import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .database import engine
from .models import Base
from .routers import auth, sessions, attendance, students, admin
from .events.event_bus import event_bus
# Import handlers so they register their subscriptions with event_bus
from .events import handlers
from .events.handlers.notification_handler import notification_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend.main")

# Create tables in Postgres or local dev SQLite
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start decoupled EventBus background consumer loop
    worker_task = asyncio.create_task(event_bus.start_processing())
    logger.info("FastAPI Lifespan: EventBus worker started.")
    yield
    # Shutdown: Cleanly stop background worker
    event_bus.stop_processing()
    worker_task.cancel()
    logger.info("FastAPI Lifespan: EventBus worker stopped.")

app = FastAPI(
    title="Face Recognition Attendance Cloud API",
    description="Hybrid Architecture (MVC + Event-Driven) backend for edge desktop synchronization and student mobile attendance tracking.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(attendance.router)
app.include_router(students.router)
app.include_router(admin.router)

@app.get("/")
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Face Recognition Attendance API",
        "architecture": "Hybrid (MVC + Event-Driven)",
        "documentation": "/docs"
    }

# --- Real-Time Push Notification WebSockets (EDA Link to Clients) ---
@app.websocket("/ws/student/{student_id}")
async def websocket_student_notifications(websocket: WebSocket, student_id: int):
    """
    Subscribes a student's mobile app to personal real-time attendance events.
    """
    await notification_manager.connect_student(student_id, websocket)
    try:
        while True:
            # Keep socket open and receive heartbeat/ping
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_manager.disconnect_student(student_id, websocket)

@app.websocket("/ws/broadcast")
async def websocket_broadcast(websocket: WebSocket):
    """
    Global broadcast socket for administrative telemetry and live class monitors.
    """
    await notification_manager.connect_broadcast(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_manager.disconnect_broadcast(websocket)
