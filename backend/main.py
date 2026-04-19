import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Set
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from camera.camera_manager import CameraManager, CameraConfig
from pipeline.processor import ProcessingPipeline

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


CAMERA_CONFIGS = [
    CameraConfig(camera_id="cam_0", name="Main Hall",  source=0,              zone="Main Hall"),
    CameraConfig(camera_id="cam_1", name="Corridor",   source="C:/Users/navee\PycharmProjects\stampede project/backend/videos/1887-151131664_medium.mp4", zone="Corridor"),
    CameraConfig(camera_id="cam_2", name="Entrance",   source="C:/Users/navee\PycharmProjects\stampede project/backend/videos/6387-191695740.mp4", zone="Entrance"),
    CameraConfig(camera_id="cam_3", name="Stairwell A",  source="C:/Users/navee\PycharmProjects\stampede project/backend/videos/57128-484330955_medium.mp4",     zone="Stairwell A"),
]

camera_manager: CameraManager = None
pipeline: ProcessingPipeline = None
ws_clients: Set[WebSocket] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global camera_manager, pipeline
    
    logger.info("Starting CrowdSafe AI system...")
    camera_manager = CameraManager(CAMERA_CONFIGS)
    camera_manager.start_all()
    
    pipeline = ProcessingPipeline(camera_manager)
    pipeline.start()
    

    asyncio.create_task(broadcast_loop())
    
    logger.info("System ready.")
    yield
    
    logger.info("Shutting down...")
    pipeline.stop()
    camera_manager.stop_all()


app = FastAPI(title="CrowdSafe AI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def broadcast_loop():
    global ws_clients
    while True:
        await asyncio.sleep(0.2)   # 5fps broadcast
        if not ws_clients or pipeline is None:
            continue

        try:
            state = pipeline.get_state()
            msg = json.dumps({"type": "state", "data": state})

            dead = set()
            for ws in list(ws_clients):
                try:
                    await ws.send_text(msg)
                except Exception:
                    dead.add(ws)

            ws_clients -= dead
        except Exception as e:
            logger.error(f"Broadcast error: {e}")



@app.websocket("/ws/live")
@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    await ws.accept()
    ws_clients.add(ws)
    logger.info(f"WS connected  (total: {len(ws_clients)})")
    try:
        while True:
            # Send ping every 20s to keep connection alive
            await asyncio.sleep(20)
            try:
                await ws.send_text('{"type":"ping"}')
            except Exception:
                break
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        ws_clients.discard(ws)
        logger.info(f"WS disconnected  (total: {len(ws_clients)})")


@app.get("/state")
async def get_state():
    if pipeline is None:
        return JSONResponse({"error": "Pipeline not ready"}, status_code=503)
    return pipeline.get_state()


@app.get("/alerts")
async def get_alerts():
    if pipeline is None:
        return JSONResponse({"error": "Pipeline not ready"}, status_code=503)
    state = pipeline.get_state()
    return {"alerts": state["alerts"]}


@app.get("/evacuation")
async def get_evacuation():
    if pipeline is None:
        return JSONResponse({"error": "Pipeline not ready"}, status_code=503)
    state = pipeline.get_state()
    return state["evacuation"]


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": time.time(),
        "ws_clients": len(ws_clients),
        "pipeline_running": pipeline is not None,
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, workers=1)
