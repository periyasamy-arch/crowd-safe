# 🎯 CrowdSafe AI Command Center

Real-Time Multi-Camera Crowd Risk Monitoring & Smart Evacuation Decision System

## Architecture

```
Python AI Backend (FastAPI)
    ↓ WebSocket + REST API  
React Frontend (Vite + React 18)
```

- **Backend** performs ALL computation (YOLOv8, tracking, risk, evacuation)
- **Frontend** is visualization ONLY (zero AI processing)
- **WebSocket** streams at ~16 FPS for smooth UI

---

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run backend
python main.py
```

Backend starts on: `http://localhost:8000`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend starts on: `http://localhost:3000`

---

## Camera Configuration

Edit `backend/main.py` → `CAMERA_CONFIGS`:

```python
CAMERA_CONFIGS = [
    CameraConfig(camera_id="cam_0", name="Main Hall",  source=0,              zone="Main Hall"),   # Webcam
    CameraConfig(camera_id="cam_1", name="Corridor",   source="corridor.mp4", zone="Corridor"),    # MP4 file
    CameraConfig(camera_id="cam_2", name="Entrance",   source="entrance.mp4", zone="Entrance"),    # MP4 file
    CameraConfig(camera_id="cam_3", name="Exit Area",  source="exit.mp4",     zone="Exit Area"),   # MP4 file
]
```

- `source=0` → webcam index 0
- `source="path/to/video.mp4"` → video file (loops automatically)
- If source unavailable → **synthetic animated frames** are used automatically

---

## System Components

### Backend Modules

| File | Purpose |
|------|---------|
| `main.py` | FastAPI server, WebSocket, REST endpoints |
| `camera/camera_manager.py` | Multi-camera thread management, frame queues |
| `pipeline/tracker.py` | IoU-based multi-object tracker |
| `pipeline/risk_engine.py` | Deterministic risk calculation |
| `pipeline/evacuation_router.py` | NetworkX + Dijkstra evacuation routing |
| `pipeline/processor.py` | Main processing loop (YOLOv8 → track → risk → alert) |

### Risk Model (Locked)

```
Risk = 0.4 × Density + 0.3 × SpeedVariance + 0.3 × DirectionEntropy
```

| Risk Level | Score Range | Behavior |
|-----------|------------|---------|
| LOW       | 0–35%      | Monitoring only |
| MEDIUM    | 35–60%     | Warning |
| HIGH      | 60–80%     | Alert |
| CRITICAL  | 80–100%    | Evacuation route shown |

### REST API

| Endpoint | Description |
|---------|------------|
| `GET /health` | System health check |
| `GET /state` | Full system state snapshot |
| `GET /alerts` | Latest alerts |
| `GET /evacuation` | Evacuation graph + active route |
| `WS /ws/live` | Live WebSocket stream (primary) |

---

## Dashboard Panels

1. **Live Camera Feeds** - Annotated frames with risk/people overlay
2. **Global Risk Gauge** - SVG arc gauge showing global risk score
3. **Alert Panel** - Single latest alert (replaces, no stacking)
4. **Evacuation Panel** - Only shown during CRITICAL risk
5. **Risk Timeline** - Last 60 seconds of global risk history
6. **Zone Risk Comparison** - Bar chart per camera zone
7. **Evacuation Network** - Building topology with active route
8. **Zone Sub-Score Breakdown** - Grouped bars: Density, Speed Var., Direction Entropy

---

## Requirements

### Backend
- Python 3.10+
- CUDA optional (CPU inference works fine with yolov8n)

### Frontend
- Node.js 18+
- npm 9+

---

## Notes

- YOLOv8n model (`yolov8n.pt`) downloads automatically on first run
- If no camera/file available, synthetic animated frames are generated
- MP4 files loop automatically
- WebSocket reconnects automatically on disconnect
- Evacuation route appears ONLY during CRITICAL risk (score ≥ 80%)
