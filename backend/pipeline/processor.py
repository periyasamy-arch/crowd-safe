"""
processor.py  –  Main processing pipeline (OPTIMIZED)
- YOLO resized to 416px before inference (2-3x faster)
- Pipeline at 4Hz
- Crowd estimation in background thread
- Per-camera webcam detection relaxation
- All detection filters included
"""

import base64
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

import cv2
import numpy as np

from pipeline.density_classifier import DensityClassifier, MAX_DENSITY_VALUE
from pipeline.tracker            import IoUTracker
from pipeline.risk_engine        import ZoneRisk, analyze_zone, compute_global_risk
from pipeline.evacuation_router  import EvacuationRouter

logger = logging.getLogger(__name__)

# ── Detection tuning ──────────────────────────────────────────────────────────
YOLO_CONF        = 0.60
MIN_BOX_AREA = 4000  # was 3500
ASPECT_RATIO_MIN = 1.2
FRAME_W          = 426
FRAME_H          = 240
JPEG_QUALITY     = 35

# ── YOLO ─────────────────────────────────────────────────────────────────────
try:
    from ultralytics import YOLO as _YOLO
    _YOLO_AVAILABLE = True
except ImportError:
    _YOLO_AVAILABLE = False
    logger.warning("YOLOv8 not available – using fallback detector")


@dataclass
class CameraState:
    camera_id:         str
    name:              str
    zone:              str
    frame_b64:         str   = ""
    person_count:      int   = 0
    density:           float = 0.0
    speed_variance:    float = 0.0
    direction_entropy: float = 0.0
    risk_score:        float = 0.0
    risk_level:        str   = "LOW"
    density_class:     str   = "LOW"
    cnn_confidence:    float = 0.0
    fps:               float = 0.0


@dataclass
class SystemState:
    cameras:           Dict[str, CameraState] = field(default_factory=dict)
    global_risk_score: float = 0.0
    global_risk_level: str   = "LOW"
    total_people:      int   = 0
    alerts:            List  = field(default_factory=list)
    evacuation:        Dict  = field(default_factory=dict)
    timestamp:         float = 0.0


class ProcessingPipeline:
    CNN_CHECKPOINT = "density_classifier_best.pth"

    def __init__(self, camera_manager, cnn_checkpoint: str = None):
        self.camera_manager = camera_manager

        # CNN density classifier
        ckpt = cnn_checkpoint or self.CNN_CHECKPOINT
        self.cnn = DensityClassifier(checkpoint_path=ckpt, device="cpu")
        logger.info(f"[Pipeline] CNN mode: {'CNN' if self.cnn.using_cnn else 'HEURISTIC FALLBACK'}")

        # YOLO
        self.yolo = None
        self._init_yolo()

        # Per-camera trackers
        self.trackers: Dict[str, IoUTracker] = {
            cid: IoUTracker()
            for cid in camera_manager.get_camera_ids()
        }

        # Evacuation router
        self.router = EvacuationRouter()

        # Shared state
        self.state      = SystemState(timestamp=time.time())
        self._lock      = threading.RLock()
        self._risk_hist = deque(maxlen=360)
        self._running   = False

        # Processing threads
        self._thread: Optional[threading.Thread]            = None
        self._estimation_thread: Optional[threading.Thread] = None

        # Crowd count cache (for HIGH density cameras)
        self._crowd_counts    = {}
        self._estimation_lock = threading.Lock()

        # Alert debounce
        self._last_alert = 0.0
        self._alert_ttl  = 5.0

    # ── YOLO init ─────────────────────────────────────────────────────────────

    def _init_yolo(self):
        if not _YOLO_AVAILABLE:
            return
        try:
            import torch
            import ultralytics.nn.tasks
            torch.serialization.add_safe_globals([
                ultralytics.nn.tasks.DetectionModel
            ])
            self.yolo = _YOLO("yolov8n.pt")
            logger.info("[Pipeline] YOLOv8n loaded")
        except Exception:
            try:
                import torch
                original_load = torch.load
                def patched_load(*args, **kwargs):
                    kwargs['weights_only'] = False
                    return original_load(*args, **kwargs)
                torch.load = patched_load
                self.yolo = _YOLO("yolov8n.pt")
                torch.load = original_load
                logger.info("[Pipeline] YOLOv8n loaded (patched)")
            except Exception as e:
                logger.error(f"[Pipeline] YOLO load failed: {e}")

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        self._running = True

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

        self._estimation_thread = threading.Thread(
            target=self._crowd_estimation_loop, daemon=True
        )
        self._estimation_thread.start()

        logger.info("[Pipeline] Started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    # ── Public state ──────────────────────────────────────────────────────────

    def get_state(self) -> Dict:
        with self._lock:
            return {
                "cameras":           {k: asdict(v) for k, v in self.state.cameras.items()},
                "global_risk_score": self.state.global_risk_score,
                "global_risk_level": self.state.global_risk_level,
                "total_people":      self.state.total_people,
                "alerts":            self.state.alerts[-10:],
                "evacuation":        self.state.evacuation,
                "risk_history":      list(self._risk_hist),
                "timestamp":         self.state.timestamp,
            }

    # ── Processing loop ───────────────────────────────────────────────────────

    def _loop(self):
        while self._running:
            t0 = time.time()
            try:
                self._process_all()
            except Exception as e:
                logger.error(f"[Pipeline] Error: {e}", exc_info=True)
            time.sleep(max(0.25, 0.25 - (time.time() - t0)))  # 4Hz max

    def _process_all(self):
        frames     = self.camera_manager.get_all_frames()
        zone_risks = []
        cam_states = {}

        for cam_id, frame in frames.items():
            if frame is None:
                continue

            name      = self.camera_manager.get_camera_name(cam_id)
            zone      = self.camera_manager.get_camera_zone(cam_id)
            h, w      = frame.shape[:2]
            is_webcam = cam_id == "cam_0"

            # Step 1 — CNN density classification
            density_class, cnn_conf = self.cnn.classify(frame)

            # Step 2 — Hybrid person counting
            if density_class in ("LOW", "MEDIUM"):
                detections   = self._yolo_detect(frame, is_webcam=is_webcam)
                tracks       = self.trackers[cam_id].update(detections)
                person_count = len(tracks)
            else:
                # HIGH density — use background estimated count
                person_count = self._get_crowd_count(cam_id)
                self.trackers[cam_id].inject_virtual_tracks(person_count, w, h)
                tracks = list(self.trackers[cam_id].tracks.values())

            # Step 3 — Risk metrics
            zr = analyze_zone(
                cam_id, zone, tracks,
                person_count, density_class, cnn_conf, w, h
            )
            zone_risks.append(zr)

            # Step 4 — Annotate and encode
            annotated = self._annotate(frame.copy(), tracks, zr)
            frame_b64 = self._encode(annotated)

            cam_states[cam_id] = CameraState(
                camera_id=cam_id, name=name, zone=zone,
                frame_b64=frame_b64,
                person_count=person_count,
                density=round(zr.density * 100, 1),
                speed_variance=round(zr.speed_variance * 100, 1),
                direction_entropy=round(zr.direction_entropy * 100, 1),
                risk_score=zr.risk_score,
                risk_level=zr.risk_level,
                density_class=density_class,
                cnn_confidence=round(cnn_conf, 3),
            )

        # Global risk
        g_score, g_level = compute_global_risk(zone_risks)
        total            = sum(z.person_count for z in zone_risks)
        self._risk_hist.append(round(g_score, 1))

        # Evacuation
        evac = self._handle_evacuation(g_level, zone_risks)

        # Alerts
        alerts = self._make_alerts(g_level, g_score, zone_risks, total)

        # Atomic state update
        with self._lock:
            self.state.cameras           = cam_states
            self.state.global_risk_score = g_score
            self.state.global_risk_level = g_level
            self.state.total_people      = total
            self.state.evacuation        = evac
            if alerts:
                self.state.alerts = alerts
            self.state.timestamp = time.time()

    # ── YOLO detection ────────────────────────────────────────────────────────

    def _yolo_detect(self, frame: np.ndarray, is_webcam: bool = False) -> List:
        if self.yolo is None:
            return self._mock_detect(frame)
        try:
            h, w = frame.shape[:2]

            # Resize to 416px wide before YOLO — 2-3x faster inference
            scale = 416 / w
            small = cv2.resize(frame, (416, int(h * scale)),
                               interpolation=cv2.INTER_LINEAR)
            sh, sw = small.shape[:2]

            conf      = 0.45 if is_webcam else YOLO_CONF
            min_area  = 1500 if is_webcam else MIN_BOX_AREA
            min_ratio = 0.6  if is_webcam else ASPECT_RATIO_MIN

            results = self.yolo(small, classes=[0], verbose=False, conf=conf)
            detections = []

            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()

                    # Scale back to original frame coordinates
                    x1 = x1 / sw * w
                    y1 = y1 / sh * h
                    x2 = x2 / sw * w
                    y2 = y2 / sh * h

                    bw   = x2 - x1
                    bh   = y2 - y1
                    area = bw * bh

                    # filter 1 — too small
                    if area < min_area:
                        continue

                    # filter 2 — aspect ratio (persons are taller than wide)
                    if bw > 0 and (bh / bw) < min_ratio:
                        continue

                    # filter 3 — too large (walls/background)
                    if area > (w * h * 0.3):
                        continue

                    # filter 4 — too wide (not a person) — skip for webcam
                    if not is_webcam and bw > w * 0.4:
                        continue

                    # filter 5 — top of frame (ceiling signs)
                    if not is_webcam and y1 < h * 0.08:
                        continue

                    # filter 6 — center too high (wall decorations)
                    if not is_webcam and (y1 + y2) / 2 < h * 0.20:
                        continue

                    # filter 7 — far right edge (shop signs)
                    if not is_webcam and x1 > w * 0.85:
                        continue

                    detections.append((x1, y1, x2, y2))

            return detections

        except Exception as e:
            logger.error(f"[YOLO] Error: {e}")
            return []

    def _mock_detect(self, frame: np.ndarray) -> List:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, th = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY)
        cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        dets = []
        for c in cnts:
            area = cv2.contourArea(c)
            if area < MIN_BOX_AREA:
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            if bw > 0 and (bh / bw) < ASPECT_RATIO_MIN:
                continue
            dets.append((float(x), float(y), float(x+bw), float(y+bh)))
        return dets[:10]

    # ── Crowd estimation (background thread) ─────────────────────────────────

    def _crowd_estimation_loop(self):
        while self._running:
            frames = self.camera_manager.get_all_frames()
            for cam_id, frame in frames.items():
                if frame is None:
                    continue
                try:
                    count = self._run_patch_yolo(frame)
                    with self._estimation_lock:
                        self._crowd_counts[cam_id] = count
                except Exception as e:
                    logger.error(f"[Estimation] {e}")
                time.sleep(0.3)   # gap between cameras
            time.sleep(1.0)       # full cycle every 1s

    def _run_patch_yolo(self, frame: np.ndarray) -> int:
        if self.yolo is None:
            return self._pixel_based_estimate(frame)
        try:
            h, w = frame.shape[:2]
            ph, pw = h // 2, w // 2
            total = 0
            for r in range(2):
                for c in range(2):
                    patch = frame[r*ph:(r+1)*ph, c*pw:(c+1)*pw]
                    results = self.yolo(patch, classes=[0], verbose=False, conf=0.25)
                    for res in results:
                        total += len(res.boxes)
            total     = total * 2
            pixel_est = self._pixel_based_estimate(frame)
            return max(total, pixel_est, 30)
        except Exception as e:
            logger.error(f"[Crowd count] error: {e}")
            return self._pixel_based_estimate(frame)

    def _pixel_based_estimate(self, frame: np.ndarray) -> int:
        gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges   = cv2.Canny(gray, 50, 150)
        density = np.count_nonzero(edges) / edges.size
        return int(30 + density * 600)

    def _get_crowd_count(self, cam_id: str) -> int:
        with self._estimation_lock:
            return self._crowd_counts.get(cam_id, 30)

    # ── Frame annotation ──────────────────────────────────────────────────────

    def _annotate(self, frame: np.ndarray, tracks, zr: ZoneRisk) -> np.ndarray:
        COLORS = {
            "LOW":      "#00d084",
            "MEDIUM":   "#f0b429",
            "HIGH":     "#f97316",
            "CRITICAL": "#ef4444",
        }
        hex_c = COLORS.get(zr.risk_level, "#00d084").lstrip("#")
        bgr   = tuple(int(hex_c[i:i+2], 16) for i in (4, 2, 0))

        if zr.density_class == "HIGH":
            # Red tint overlay for HIGH density — no fake boxes
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]),
                          (0, 0, 180), -1)
            cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
            cv2.putText(frame, "HIGH DENSITY ZONE",
                        (10, frame.shape[0] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        else:
            # Draw real YOLO tracks only
            for t in tracks:
                x1, y1, x2, y2 = (int(v) for v in t.bbox)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"P{t.track_id}", (x1, y1 - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)

        h, w = frame.shape[:2]
        ov   = frame.copy()
        cv2.rectangle(ov, (0, 0), (w, 38), (15, 15, 15), -1)
        cv2.addWeighted(ov, 0.75, frame, 0.25, 0, frame)
        banner = (f"Risk: {zr.risk_level} {zr.risk_score:.0f}%  |  "
                  f"People: {zr.person_count}  |  CNN: {zr.density_class}")
        cv2.putText(frame, banner, (6, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, bgr, 1)
        return frame

    def _encode(self, frame: np.ndarray) -> str:
        resized = cv2.resize(frame, (FRAME_W, FRAME_H),
                             interpolation=cv2.INTER_LINEAR)
        _, buf = cv2.imencode('.jpg', resized,
                              [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        return base64.b64encode(buf).decode('utf-8')

    # ── Evacuation ────────────────────────────────────────────────────────────

    def _handle_evacuation(self, level: str, zone_risks: List[ZoneRisk]) -> Dict:
        critical_zones = [z.zone for z in zone_risks if z.risk_level == "CRITICAL"]
        all_high       = [z.zone for z in zone_risks
                          if z.risk_level in ("HIGH", "CRITICAL")]

        if level == "CRITICAL":
            worst = max(zone_risks, key=lambda z: z.risk_score)
            self.router.activate_evacuation(critical_zones, worst.zone)
        else:
            self.router.deactivate()

        return self.router.get_graph_data(critical_zones=all_high)

    # ── Alerts ────────────────────────────────────────────────────────────────

    def _make_alerts(self, level, score, zone_risks, total) -> List:
        now = time.time()
        if now - self._last_alert < self._alert_ttl:
            return self.state.alerts
        self._last_alert = now

        if level == "CRITICAL":
            msg = (f"CRITICAL RISK {score:.0f}%. Evacuation active. "
                   f"Zones: {', '.join(z.zone for z in zone_risks if z.risk_score > 60)}")
        elif level == "HIGH":
            msg = f"HIGH RISK {score:.0f}%. {total} persons detected. Monitoring closely."
        elif level == "MEDIUM":
            worst = max(zone_risks, key=lambda z: z.risk_score) if zone_risks else None
            msg = (f"WARNING: Elevated density in "
                   f"{worst.zone if worst else '?'}. Risk {score:.0f}%.")
        else:
            worst = max(zone_risks, key=lambda z: z.risk_score) if zone_risks else None
            msg = (f"System nominal. Highest activity: "
                   f"{worst.zone if worst else 'N/A'} ({total} persons).")

        return [{"level": level, "message": msg,
                 "score": score, "timestamp": now}]