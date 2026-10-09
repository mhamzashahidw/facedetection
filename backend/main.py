import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from database.connection import engine, Base
from events.event_bus import event_bus

# Create DB tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start Event Bus background task
    task = asyncio.create_task(event_bus.start_processing())
    yield
    # Shutdown logic
    task.cancel()

from controllers import auth, students, face, attendance
from events.handlers import attendance_handler, audit_handler

app = FastAPI(
    title="FaceAttend AI API",
    description="Advanced AI Face Recognition Attendance Management System",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(auth.router)
app.include_router(students.router)
app.include_router(face.router)
app.include_router(attendance.router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "FaceAttend AI API is running"}

# Example WebSocket route for real-time dashboard updates
@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Basic handler to send events to the connected dashboard
    async def dashboard_event_handler(payload):
        await websocket.send_json(payload)
        
    # Subscribe this websocket to relevant events
    event_bus.subscribe("AttendanceMarked", dashboard_event_handler)
    
    try:
        while True:
            # Keep connection open
            data = await websocket.receive_text()
    except Exception as e:
        print("WebSocket connection closed")
        # In a complete implementation, you'd unsubscribe the handler here
