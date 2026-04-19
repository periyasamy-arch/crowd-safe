import cv2
import threading
import time
import numpy as np
from queue import Queue, Empty
from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class CameraConfig:
    camera_id: str
    name: str
    source: any  # int for webcam, str for file path
    zone: str = "unknown"


class CameraStream:
    """Single camera stream running in a background thread."""
    
    def __init__(self, config: CameraConfig):
        self.config = config
        self.frame_queue = Queue(maxsize=2)  # Drop old frames
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.cap: Optional[cv2.VideoCapture] = None
        self.last_frame: Optional[np.ndarray] = None
        self.fps = 0.0
        self.frame_count = 0
        self._synthetic = False

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Non-blocking: get latest frame."""
        frame = None
        try:
            while True:
                frame = self.frame_queue.get_nowait()
        except Empty:
            pass
        if frame is not None:
            self.last_frame = frame
        return self.last_frame

    def _open_source(self):
        source = self.config.source
        if isinstance(source, int):
            cap = cv2.VideoCapture(source)
        else:
            cap = cv2.VideoCapture(source)
        
        if not cap.isOpened():
            return None
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def _generate_synthetic_frame(self) -> np.ndarray:
        """Generate synthetic frames when no camera available."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        t = time.time()
        # Animated background
        for i in range(3):
            x = int(320 + 200 * np.cos(t * 0.5 + i * 2.1))
            y = int(240 + 150 * np.sin(t * 0.7 + i * 1.5))
            color = [
                int(50 + 30 * np.sin(t + i)),
                int(80 + 40 * np.cos(t * 1.3 + i)),
                int(120 + 60 * np.sin(t * 0.8 + i))
            ]
            cv2.ellipse(frame, (x, y), (60, 40), int(t * 30) % 360, 0, 360, color, -1)
        
        cv2.putText(frame, f"SYNTHETIC - {self.config.name}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 200, 100), 1)
        cv2.putText(frame, f"No source: {self.config.source}", (10, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
        return frame

    def _capture_loop(self):
        self.cap = self._open_source()
        self._synthetic = self.cap is None
        
        t0 = time.time()
        fc = 0
        
        while self.running:
            if self._synthetic:
                frame = self._generate_synthetic_frame()
                time.sleep(0.033)  # ~30 FPS synthetic
            else:
                ret, frame = self.cap.read()
                if not ret:
                    # Loop video file
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self.cap.read()
                    if not ret:
                        self._synthetic = True
                        continue

            # Drop old frame, put new one
            if not self.frame_queue.full():
                self.frame_queue.put(frame)
            else:
                try:
                    self.frame_queue.get_nowait()
                except Empty:
                    pass
                self.frame_queue.put(frame)

            fc += 1
            elapsed = time.time() - t0
            if elapsed >= 1.0:
                self.fps = fc / elapsed
                fc = 0
                t0 = time.time()
            self.frame_count += 1


class CameraManager:
    """Manages multiple camera streams."""
    
    def __init__(self, configs: List[CameraConfig]):
        self.streams: Dict[str, CameraStream] = {}
        for cfg in configs:
            self.streams[cfg.camera_id] = CameraStream(cfg)

    def start_all(self):
        for stream in self.streams.values():
            stream.start()

    def stop_all(self):
        for stream in self.streams.values():
            stream.stop()

    def get_frame(self, camera_id: str) -> Optional[np.ndarray]:
        stream = self.streams.get(camera_id)
        if stream:
            return stream.get_latest_frame()
        return None

    def get_all_frames(self) -> Dict[str, Optional[np.ndarray]]:
        return {cid: s.get_latest_frame() for cid, s in self.streams.items()}

    def get_camera_ids(self) -> List[str]:
        return list(self.streams.keys())

    def get_camera_name(self, camera_id: str) -> str:
        stream = self.streams.get(camera_id)
        if stream:
            return stream.config.name
        return camera_id

    def get_camera_zone(self, camera_id: str) -> str:
        stream = self.streams.get(camera_id)
        if stream:
            return stream.config.zone
        return "unknown"
