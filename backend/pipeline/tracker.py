import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional


@dataclass
class Track:
    track_id: int
    bbox: Tuple[float, float, float, float]
    centroid: Tuple[float, float]
    velocity: Tuple[float, float] = (0.0, 0.0)
    age: int = 0
    missed: int = 0
    history: List[Tuple[float, float]] = field(default_factory=list)

    def update_centroid(self):
        x1, y1, x2, y2 = self.bbox
        self.centroid = ((x1 + x2) / 2, (y1 + y2) / 2)


def _iou(a, b) -> float:
    xA = max(a[0], b[0]); yA = max(a[1], b[1])
    xB = min(a[2], b[2]); yB = min(a[3], b[3])
    inter = max(0, xB - xA) * max(0, yB - yA)
    areaA = (a[2]-a[0]) * (a[3]-a[1])
    areaB = (b[2]-b[0]) * (b[3]-b[1])
    union = areaA + areaB - inter
    return inter / union if union > 0 else 0.0


class IoUTracker:
    def __init__(self, iou_threshold=0.3, max_missed=5, max_history=30):
        self.tracks: Dict[int, Track] = {}
        self.next_id       = 1
        self.iou_threshold = iou_threshold
        self.max_missed    = max_missed
        self.max_history   = max_history

    def update(self, detections: List[Tuple]) -> List[Track]:
        if not self.tracks:
            for det in detections:
                self._create(det)
            return list(self.tracks.values())

        track_ids   = list(self.tracks.keys())
        track_boxes = [self.tracks[tid].bbox for tid in track_ids]
        matched_t, matched_d = set(), set()

        if track_boxes and detections:
            mat = np.zeros((len(track_ids), len(detections)))
            for i, tb in enumerate(track_boxes):
                for j, det in enumerate(detections):
                    mat[i, j] = _iou(tb, det)

            while mat.max() >= self.iou_threshold:
                i, j  = np.unravel_index(mat.argmax(), mat.shape)
                tid   = track_ids[i]
                t     = self.tracks[tid]
                old_c = t.centroid
                t.bbox = detections[j]
                t.update_centroid()
                t.velocity = (t.centroid[0]-old_c[0], t.centroid[1]-old_c[1])
                t.history.append(t.centroid)
                if len(t.history) > self.max_history:
                    t.history.pop(0)
                t.age += 1
                t.missed = 0
                matched_t.add(tid)
                matched_d.add(j)
                mat[i, :] = -1
                mat[:, j] = -1

        for i, tid in enumerate(track_ids):
            if tid not in matched_t:
                self.tracks[tid].missed += 1

        for j, det in enumerate(detections):
            if j not in matched_d:
                self._create(det)

        dead = [tid for tid, t in self.tracks.items() if t.missed > self.max_missed]
        for tid in dead:
            del self.tracks[tid]

        return list(self.tracks.values())

    def _create(self, bbox):
        t = Track(
            track_id=self.next_id,
            bbox=bbox,
            centroid=((bbox[0]+bbox[2])/2, (bbox[1]+bbox[3])/2)
        )
        t.history.append(t.centroid)
        self.tracks[self.next_id] = t
        self.next_id += 1

    def inject_virtual_tracks(self, count: int, frame_w: int, frame_h: int):
        self.reset()
        cols = max(1, int(np.sqrt(count * frame_w / frame_h)))
        rows = max(1, (count + cols - 1) // cols)
        cw, ch = frame_w / cols, frame_h / rows
        placed = 0
        for r in range(rows):
            for c in range(cols):
                if placed >= count:
                    break
                cx = cw * (c + 0.5)
                cy = ch * (r + 0.5)
                bw, bh = cw * 0.6, ch * 0.8
                bbox = (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
                self._create(bbox)
                self.tracks[self.next_id - 1].velocity = (
                    float(np.random.uniform(-5, 5)),
                    float(np.random.uniform(-5, 5)),
                )
                placed += 1

    def reset(self):
        self.tracks.clear()
        self.next_id = 1