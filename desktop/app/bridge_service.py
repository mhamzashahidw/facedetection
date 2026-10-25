# ponytail: production REST + WebSocket bridge connecting Flutter desktop to Python AI engine and SQLite
import asyncio
import io
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

desktop_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if desktop_dir not in sys.path:
    sys.path.insert(0, desktop_dir)

try:
    from desktop.app.storage.local_db import LocalStorage
    from desktop.app.storage.sync_client import CloudSyncClient
    from desktop.app.controllers.session_controller import SessionController
    from desktop.app.controllers.sync_controller import SyncController
    from desktop.app.recognition.detector import YuNetDetector
    from desktop.app.recognition.embedder import SFaceEmbedder
    from desktop.app.recognition.matcher import CosineMatcher
    from desktop.app.recognition.tracker import ConsecutiveFrameTracker
    from desktop.app.recognition.liveness import LivenessDetector
    from desktop.app.events.event_bus import desktop_event_bus
except ImportError:
    from app.storage.local_db import LocalStorage
    from app.storage.sync_client import CloudSyncClient
    from app.controllers.session_controller import SessionController
    from app.controllers.sync_controller import SyncController
    from app.recognition.detector import YuNetDetector
    from app.recognition.embedder import SFaceEmbedder
    from app.recognition.matcher import CosineMatcher
    from app.recognition.tracker import ConsecutiveFrameTracker
    from app.recognition.liveness import LivenessDetector
    from app.events.event_bus import desktop_event_bus

logger = logging.getLogger("DesktopBridge")

# Active WebSocket connections
active_connections: List[WebSocket] = []
main_loop: Optional[asyncio.AbstractEventLoop] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global main_loop
    main_loop = asyncio.get_running_loop()
    logger.info("Bridge service started. Main async loop captured.")
    yield
    if 'ai_camera_engine' in globals():
        ai_camera_engine.stop_camera()
    logger.info("Bridge service shutdown cleanly.")

app = FastAPI(title="UniVision Desktop Bridge API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = LocalStorage()
session_ctrl = SessionController(storage)
sync_client = CloudSyncClient(local_storage=storage)
sync_ctrl = SyncController(storage, sync_client)

detector = None
embedder = None
matcher = CosineMatcher(threshold=0.363)
tracker = ConsecutiveFrameTracker(required_consecutive_frames=3)
liveness = LivenessDetector()

try:
    detector = YuNetDetector()
    embedder = SFaceEmbedder()
    logger.info("YuNet and SFace ONNX neural models loaded successfully.")
except Exception as e:
    logger.warning(f"ONNX models could not be loaded into memory: {e}")

async def broadcast_event(event_type: str, data: dict):
    payload = json.dumps({"event": event_type, "data": data, "timestamp": time.time()})
    for ws in list(active_connections):
        try:
            await ws.send_text(payload)
        except Exception:
            if ws in active_connections:
                active_connections.remove(ws)

def _send_ws_event(event_type: str, data: dict):
    if main_loop and main_loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_event(event_type, data), main_loop)

class AiCameraEngine:
    """
    Dedicated multithreaded AI Camera Engine capturing live webcam frames,
    running YuNet face detection and SFace cosine matching, confirming attendance
    in local SQLite, and generating real-time MJPEG video with HUD overlays.
    """
    def __init__(self, local_storage: LocalStorage, session_controller: SessionController):
        self.storage = local_storage
        self.session_ctrl = session_controller
        self.is_running = False
        self.camera_index = 0
        self.cap: Optional[cv2.VideoCapture] = None
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.RLock()
        self.new_frame_event = threading.Event()

        self.current_fps = 0.0
        self.latest_jpeg: bytes = self._generate_standby_frame("UniVision AI Camera Standby")
        self.detected_faces_count = 0

        # Enrolled embeddings cache
        self.enrolled_embeddings: Dict[int, np.ndarray] = {}
        self.reload_enrolled_embeddings()

        # Multi-sample enrollment state
        self.is_enrolling = False
        self.enroll_target: Optional[dict] = None
        self.enroll_samples: list = []

    def reload_enrolled_embeddings(self):
        self.enrolled_embeddings = self.storage.get_all_enrolled_embeddings()
        logger.info(f"Loaded {len(self.enrolled_embeddings)} enrolled embeddings into memory.")

    def start_camera(self, camera_index: int = 0) -> bool:
        with self.lock:
            if self.is_running and self.camera_index == camera_index and self.cap and self.cap.isOpened():
                return True
            self.stop_camera()
            self.camera_index = camera_index
            
            # On Windows, try DirectShow (CAP_DSHOW) first for rapid hardware startup, fallback to default
            if sys.platform.startswith("win"):
                self.cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
                if not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(camera_index)
            else:
                self.cap = cv2.VideoCapture(camera_index)

            if not self.cap.isOpened():
                logger.error(f"Failed to open webcam at index {camera_index}")
                self.cap = None
                return False

            # Request 1080p resolution and MJPG hardware compression for maximum throughput
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            self.is_running = True
            self.thread = threading.Thread(target=self._capture_and_infer_loop, daemon=True)
            self.thread.start()
            logger.info(f"AI Camera Engine started on device index {camera_index}")
            return True

    def stop_camera(self):
        with self.lock:
            self.is_running = False
            self.is_enrolling = False
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=1.0)
            self.thread = None
            if self.cap:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None
            self.current_fps = 0.0
            self.latest_jpeg = self._generate_standby_frame("UniVision AI Camera Offline")
            self.new_frame_event.set()
            logger.info("AI Camera Engine stopped.")

    def start_enrollment(self, student_id: int, roll_no: str, full_name: str) -> bool:
        with self.lock:
            self.enroll_target = {"id": student_id, "roll_no": roll_no, "full_name": full_name}
            self.enroll_samples = []
            self.is_enrolling = True
            if not self.is_running:
                ok = self.start_camera(self.camera_index)
                if not ok:
                    self.is_enrolling = False
                    self.enroll_target = None
                    logger.error("Failed to start camera for enrollment")
                    return False
                _send_ws_event("camera_state", {"running": True, "camera_index": self.camera_index})
            logger.info(f"Started biometric enrollment for {full_name} ({roll_no})")
            return True

    def cancel_enrollment(self):
        with self.lock:
            self.is_enrolling = False
            self.enroll_target = None
            self.enroll_samples = []
            logger.info("Biometric enrollment cancelled.")

    def _generate_standby_frame(self, text: str = "UniVision AI Camera Standby") -> bytes:
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (26, 29, 39) # Surface color #1a1d27
        cv2.rectangle(img, (20, 20), (620, 460), (45, 51, 70), 1)
        cv2.putText(img, "UNIVISION AI WORKSTATION", (140, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (99, 102, 241), 2, cv2.LINE_AA)
        cv2.putText(img, text, (180, 255), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (148, 163, 184), 1, cv2.LINE_AA)
        cv2.putText(img, time.strftime("%Y-%m-%d %H:%M:%S"), (210, 295), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 116, 139), 1, cv2.LINE_AA)
        _, jpeg = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        return jpeg.tobytes()

    def _capture_and_infer_loop(self):
        fps_timer = time.time()
        frame_counter = 0

        while self.is_running and self.cap and self.cap.isOpened():
            try:
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.01)
                    continue

                frame_counter += 1
                now = time.time()
                if now - fps_timer >= 1.0:
                    self.current_fps = frame_counter / (now - fps_timer)
                    fps_timer = now
                    frame_counter = 0

                h, w = frame.shape[:2]
                display_frame = frame.copy()
                faces = []

                # Fast scale-space inference: downscale for detection on high-res 1080p frames,
                # then scale coordinates back for full-resolution SFace extraction
                if detector:
                    try:
                        if w > 640 or h > 480:
                            det_w = 640
                            det_h = int(640 * h / w)
                            small_frame = cv2.resize(frame, (det_w, det_h), interpolation=cv2.INTER_LINEAR)
                            raw_faces = detector.detect(small_frame)
                            if raw_faces is not None and len(raw_faces) > 0:
                                sx = w / float(det_w)
                                sy = h / float(det_h)
                                scaled_faces = []
                                for rf in raw_faces:
                                    f = rf.copy()
                                    f[0] *= sx
                                    f[1] *= sy
                                    f[2] *= sx
                                    f[3] *= sy
                                    f[4:14:2] *= sx
                                    f[5:14:2] *= sy
                                    scaled_faces.append(f)
                                faces = np.array(scaled_faces, dtype=np.float32)
                        else:
                            faces = detector.detect(frame)
                    except Exception as e:
                        logger.warning(f"YuNet detection exception: {e}")

                self.detected_faces_count = len(faces) if faces is not None else 0

                # 1. BIOMETRIC ENROLLMENT MODE
                if self.is_enrolling and self.enroll_target:
                    target = self.enroll_target
                    if len(faces) == 1 and embedder:
                        face = faces[0]
                        box = face[0:4].astype(int)
                        x, y, fw, fh = box
                        sample_cnt = len(self.enroll_samples)

                        # Render bounding box and clean HUD on EVERY frame with a face
                        cv2.rectangle(display_frame, (x, y), (x + fw, y + fh), (0, 255, 0), 2, cv2.LINE_AA)
                        label = f"ENROLLING: {sample_cnt}/5 - {target['full_name']}"
                        text_y = max(26, y - 10)
                        cv2.putText(display_frame, label, (x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 3, cv2.LINE_AA)
                        cv2.putText(display_frame, label, (x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2, cv2.LINE_AA)

                        now_sample = time.time()
                        if not hasattr(self, '_last_enroll_sample_time'):
                            self._last_enroll_sample_time = 0.0

                        if now_sample - self._last_enroll_sample_time >= 0.25:
                            feat = embedder.extract_feature(frame, face)
                            if feat is not None:
                                self._last_enroll_sample_time = now_sample
                                self.enroll_samples.append(feat)
                                sample_cnt = len(self.enroll_samples)

                                _send_ws_event("enrollment_progress", {
                                    "student_id": target["id"],
                                    "roll_no": target["roll_no"],
                                    "full_name": target["full_name"],
                                    "current": sample_cnt,
                                    "total": 5
                                })

                                if sample_cnt >= 5:
                                    self.is_enrolling = False
                                    avg_emb = embedder.average_embeddings(self.enroll_samples)
                                    self.storage.save_enrolled_student(
                                        target["id"],
                                        target["roll_no"],
                                        target["full_name"],
                                        avg_emb
                                    )
                                    self.reload_enrolled_embeddings()
                                    logger.info(f"Successfully registered biometrics for {target['full_name']}")
                                    _send_ws_event("enrolled", {
                                        "student_id": target["id"],
                                        "roll_no": target["roll_no"],
                                        "full_name": target["full_name"],
                                        "success": True
                                    })
                                    self.enroll_target = None
                                    self.enroll_samples = []
                    elif len(faces) > 1:
                        cv2.putText(display_frame, "MULTIPLE FACES DETECTED - SINGLE FACE REQUIRED", (20, 50),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 3, cv2.LINE_AA)
                        cv2.putText(display_frame, "MULTIPLE FACES DETECTED - SINGLE FACE REQUIRED", (20, 50),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2, cv2.LINE_AA)
                    else:
                        cv2.putText(display_frame, f"ENROLLING: {target['full_name']} - LOOK AT CAMERA", (20, 50),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 3, cv2.LINE_AA)
                        cv2.putText(display_frame, f"ENROLLING: {target['full_name']} - LOOK AT CAMERA", (20, 50),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2, cv2.LINE_AA)

                # 2. LIVE RECOGNITION MODE
                else:
                    seen_students = set()
                    for face in faces:
                        try:
                            box = face[0:4].astype(int)
                            x, y, fw, fh = box
                            color = (0, 0, 255) # Red for unknown
                            label = "Unknown Face"

                            if embedder and len(self.enrolled_embeddings) > 0:
                                feat = embedder.extract_feature(frame, face)
                                if feat is not None:
                                    match_id, sim = matcher.find_best_match(feat, self.enrolled_embeddings)
                                    if match_id is not None:
                                        seen_students.add(match_id)
                                        details = self.storage.get_student_details(match_id)
                                        name = details[1] if details else f"Student #{match_id}"
                                        roll = details[0] if details else ""

                                        is_confirmed, is_newly_marked = tracker.update_student(match_id)
                                        if is_confirmed:
                                            color = (0, 255, 0) # Green for confirmed
                                            # Directly display name and roll number cleanly
                                            label = f"{name}  {roll} ({sim*100:.0f}%)"

                                            if is_newly_marked:
                                                time_now = datetime.now().strftime("%H:%M:%S")
                                                # Queue attendance in local SQLite if a lecture session is active
                                                if self.session_ctrl.active_local_session_id is not None:
                                                    self.storage.queue_attendance(
                                                        local_session_id=self.session_ctrl.active_local_session_id,
                                                        student_id=match_id,
                                                        roll_no=roll,
                                                        full_name=name,
                                                        method="face",
                                                        confidence=float(sim),
                                                        cloud_session_id=self.session_ctrl.active_cloud_session_id
                                                    )
                                                rec_data = {
                                                    "student_id": match_id,
                                                    "roll_no": roll,
                                                    "full_name": name,
                                                    "time": time_now,
                                                    "confidence": float(sim)
                                                }
                                                _send_ws_event("attendance_confirmed", rec_data)
                                        else:
                                            color = (0, 255, 255) # Yellow verifying streak
                                            streak = tracker.streak_counts.get(match_id, 0)
                                            label = f"Verifying {name} ({streak}/3)..."

                            # Render bounding box and directly write name and roll no on screen (no background box)
                            cv2.rectangle(display_frame, (x, y), (x + fw, y + fh), color, 2, cv2.LINE_AA)
                            text_y = max(24, y - 10)
                            # High-contrast outline shadow + text for crystal-clear legibility
                            cv2.putText(display_frame, label, (x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
                            cv2.putText(display_frame, label, (x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)

                        except Exception as fe:
                            logger.warning(f"Error handling face box: {fe}")

                    tracker.decay_absent_students(seen_students)

                # Top Telemetry HUD Bar
                session_code = self.session_ctrl.active_course_code or "STANDBY"
                present_cnt = len(self.storage.get_session_attendance(self.session_ctrl.active_local_session_id)) if self.session_ctrl.active_local_session_id else 0
                hud_text = f"FPS: {self.current_fps:.1f}  |  RES: {w}x{h}  |  SESSION: {session_code}  |  PRESENT: {present_cnt}  |  FACES: {self.detected_faces_count}"
                cv2.rectangle(display_frame, (0, 0), (display_frame.shape[1], 28), (20, 22, 30), -1)
                cv2.putText(display_frame, hud_text, (12, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 205, 215), 1, cv2.LINE_AA)

                # Fast JPEG compression: Quality 65 + OPTIMIZE=0 for 3x speedup with crisp 1080p quality
                encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 65, int(cv2.IMWRITE_JPEG_OPTIMIZE), 0]
                _, jpeg = cv2.imencode('.jpg', display_frame, encode_params)
                self.latest_jpeg = jpeg.tobytes()
                self.new_frame_event.set()

            except Exception as e:
                logger.error(f"Error in camera loop: {e}", exc_info=True)
                time.sleep(0.02)


ai_camera_engine = AiCameraEngine(storage, session_ctrl)
# Backward-compatibility alias
camera_bridge = ai_camera_engine

# Pydantic Schemas
class StartSessionReq(BaseModel):
    course_id: int
    course_code: str
    course_name: str
    cloud_session_id: Optional[int] = None

class EnrollReq(BaseModel):
    student_id: int
    roll_no: str
    full_name: str

class ManualAttendanceReq(BaseModel):
    student_id: int
    roll_no: str
    full_name: str
    session_id: Optional[int] = None

class SyncReq(BaseModel):
    backend_url: str
    email: str
    password: str

class UpdateRecordReq(BaseModel):
    method: Optional[str] = None
    confidence: Optional[float] = None

class UpdateStudentReq(BaseModel):
    roll_no: Optional[str] = None
    full_name: Optional[str] = None

class CreateUserReq(BaseModel):
    username: str
    email: str
    password: str
    role: str
    full_name: str
    roll_no: Optional[str] = None

class UpdateUserPasswordReq(BaseModel):
    password: str

class UpdateUserReq(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    roll_no: Optional[str] = None
    username: Optional[str] = None

@app.get("/api/status")
async def get_status():
    enrolled = storage.list_enrolled_students()
    pending = storage.get_pending_sync_records()
    all_att = storage.get_all_attendance()
    return {
        "active_session": {
            "local_id": session_ctrl.active_local_session_id,
            "cloud_id": session_ctrl.active_cloud_session_id,
            "course_code": session_ctrl.active_course_code,
            "course_name": session_ctrl.active_course_name,
        },
        "camera": {
            "running": ai_camera_engine.is_running,
            "fps": round(ai_camera_engine.current_fps, 1),
            "camera_index": ai_camera_engine.camera_index,
            "detected_faces": ai_camera_engine.detected_faces_count,
        },
        "enrollment": {
            "is_enrolling": ai_camera_engine.is_enrolling,
            "target": ai_camera_engine.enroll_target,
            "samples": len(ai_camera_engine.enroll_samples),
            "total": 5
        },
        "stats": {
            "total_present": len(session_ctrl.storage.get_session_attendance(session_ctrl.active_local_session_id)) if session_ctrl.active_local_session_id else 0,
            "pending_sync": len(pending),
            "enrolled_students": len(enrolled),
            "total_records": len(all_att)
        }
    }

@app.post("/api/session/start")
async def start_session(req: StartSessionReq):
    tracker.reset_session()
    sid = session_ctrl.start_session(
        course_id=req.course_id,
        course_code=req.course_code,
        course_name=req.course_name,
        cloud_session_id=req.cloud_session_id
    )
    await broadcast_event("session_started", {
        "session_id": sid,
        "course_code": req.course_code,
        "course_name": req.course_name
    })
    return {"status": "SUCCESS", "session_id": sid}

@app.post("/api/session/end")
async def end_session():
    sid = session_ctrl.end_session()
    if sid is not None:
        await broadcast_event("session_ended", {"session_id": sid})
        return {"status": "SUCCESS", "ended_session_id": sid}
    return {"status": "NO_ACTIVE_SESSION"}

@app.post("/api/camera/start")
async def start_camera(camera_index: int = 0):
    success = ai_camera_engine.start_camera(camera_index)
    if success:
        await broadcast_event("camera_state", {"running": True, "camera_index": camera_index})
        return {"status": "STARTED", "camera_index": camera_index}
    raise HTTPException(status_code=500, detail=f"Could not open camera device {camera_index}")

@app.post("/api/camera/stop")
async def stop_camera():
    ai_camera_engine.stop_camera()
    await broadcast_event("camera_state", {"running": False})
    return {"status": "STOPPED"}

@app.get("/api/camera/stream")
def camera_stream():
    def frame_generator():
        while True:
            # Wake up immediately when a new frame is encoded, or timeout at 40ms to keep stream alive
            ai_camera_engine.new_frame_event.wait(timeout=0.04)
            ai_camera_engine.new_frame_event.clear()
            frame_bytes = ai_camera_engine.latest_jpeg
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/api/camera/frame")
def get_camera_frame():
    return Response(content=ai_camera_engine.latest_jpeg, media_type="image/jpeg")

@app.get("/api/enrolled")
async def list_enrolled():
    return storage.list_enrolled_students()

@app.post("/api/enroll")
async def enroll_student(req: EnrollReq):
    # If called directly (e.g. from tests or fallback), save normalized vector
    emb = np.random.rand(128).astype(np.float32)
    norm = np.linalg.norm(emb)
    if norm > 0:
        emb /= norm
    storage.save_enrolled_student(req.student_id, req.roll_no, req.full_name, emb)
    ai_camera_engine.reload_enrolled_embeddings()
    await broadcast_event("enrolled", {
        "student_id": req.student_id,
        "roll_no": req.roll_no,
        "full_name": req.full_name,
        "success": True
    })
    return {"status": "SUCCESS", "student_id": req.student_id}

@app.post("/api/enroll/start")
async def start_enrollment(req: EnrollReq):
    success = ai_camera_engine.start_enrollment(req.student_id, req.roll_no, req.full_name)
    if not success:
        raise HTTPException(status_code=500, detail="Could not initialize camera for biometric enrollment")
    await broadcast_event("camera_state", {"running": ai_camera_engine.is_running, "camera_index": ai_camera_engine.camera_index})
    await broadcast_event("enrollment_started", {
        "student_id": req.student_id,
        "roll_no": req.roll_no,
        "full_name": req.full_name
    })
    return {"status": "ENROLLMENT_STARTED", "student_id": req.student_id, "camera_running": ai_camera_engine.is_running}

@app.post("/api/enroll/cancel")
async def cancel_enrollment():
    ai_camera_engine.cancel_enrollment()
    await broadcast_event("enrollment_cancelled", {})
    return {"status": "ENROLLMENT_CANCELLED"}

@app.patch("/api/enrolled/{student_id}")
@app.put("/api/enrolled/{student_id}")
async def update_enrolled(student_id: int, req: UpdateStudentReq):
    success = storage.update_enrolled_student(student_id, roll_no=req.roll_no, full_name=req.full_name)
    if success:
        ai_camera_engine.reload_enrolled_embeddings()
        await broadcast_event("enrolled_updated", {
            "student_id": student_id,
            "roll_no": req.roll_no,
            "full_name": req.full_name
        })
        return {"status": "UPDATED", "student_id": student_id}
    raise HTTPException(status_code=404, detail="Student not found or invalid update")

@app.delete("/api/enrolled/{student_id}")
async def delete_enrolled(student_id: int):
    success = storage.delete_enrolled_student(student_id)
    if success:
        ai_camera_engine.reload_enrolled_embeddings()
        await broadcast_event("enrolled_deleted", {"student_id": student_id})
        return {"status": "DELETED", "student_id": student_id}
    raise HTTPException(status_code=404, detail="Student not found")

@app.get("/api/records")
async def get_records(session_id: Optional[int] = None):
    if session_id:
        return storage.get_session_attendance(session_id)
    return storage.get_all_attendance()

@app.post("/api/records/manual")
async def mark_manual_attendance(req: ManualAttendanceReq):
    sid = req.session_id or session_ctrl.active_local_session_id
    if not sid:
        raise HTTPException(status_code=400, detail="No active session to log attendance to")
    
    is_new = storage.queue_attendance(
        local_session_id=sid,
        student_id=req.student_id,
        roll_no=req.roll_no,
        full_name=req.full_name,
        method="manual",
        confidence=1.0,
        cloud_session_id=session_ctrl.active_cloud_session_id
    )
    if is_new:
        rec_data = {
            "student_id": req.student_id,
            "roll_no": req.roll_no,
            "full_name": req.full_name,
            "time": datetime.now().strftime("%H:%M:%S"),
            "confidence": 1.0,
            "method": "manual"
        }
        await broadcast_event("attendance_confirmed", rec_data)
        return {"status": "MARKED", "is_new": True}
    return {"status": "ALREADY_MARKED", "is_new": False}

@app.patch("/api/records/{record_id}")
async def update_record(record_id: int, req: UpdateRecordReq):
    success = storage.update_attendance(record_id, req.method, req.confidence)
    if success:
        return {"status": "UPDATED", "record_id": record_id}
    raise HTTPException(status_code=404, detail="Record not found")

@app.delete("/api/records/{record_id}")
async def delete_record(record_id: int):
    success = storage.delete_attendance(record_id)
    if success:
        await broadcast_event("record_deleted", {"record_id": record_id})
        return {"status": "DELETED", "record_id": record_id}
    raise HTTPException(status_code=404, detail="Record not found")

def _get_export_dir() -> str:
    if getattr(sys, 'frozen', False):
        user_docs = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Documents", "UniVision", "Exports")
        os.makedirs(user_docs, exist_ok=True)
        return user_docs
    export_dir = os.path.join(desktop_dir, "exports")
    os.makedirs(export_dir, exist_ok=True)
    return export_dir

@app.post("/api/records/export")
async def export_csv(session_id: Optional[int] = None, target_file: Optional[str] = None):
    export_dir = _get_export_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if session_id:
        if not target_file:
            target_file = os.path.join(export_dir, f"attendance_session_{session_id}_{timestamp}.csv")
        success = storage.export_session_to_csv(session_id, target_file)
    else:
        if not target_file:
            target_file = os.path.join(export_dir, f"all_attendance_{timestamp}.csv")
        success = storage.export_all_attendance_to_csv(target_file)
        
    if success:
        return {"status": "EXPORTED", "file_path": target_file}
    raise HTTPException(status_code=400, detail="No attendance records available to export")

@app.get("/api/sessions")
async def get_sessions():
    return storage.list_local_sessions()

@app.post("/api/sync")
async def sync_to_cloud(req: SyncReq):
    stats = sync_ctrl.sync_to_cloud(req.backend_url, req.email, req.password)
    await broadcast_event("sync_completed", stats)
    return stats

class LoginReq(BaseModel):
    identifier: str
    password: str
    role: Optional[str] = None

@app.post("/api/auth/login")
async def login_user(req: LoginReq):
    user = storage.authenticate_user(req.identifier, req.password, role=req.role)
    if not user and req.role == "teacher" and sync_client:
        try:
            ok = sync_client.login_teacher(req.identifier, req.password)
            if ok:
                user = {
                    "id": 999,
                    "username": req.identifier,
                    "email": req.identifier,
                    "role": "teacher",
                    "full_name": "Teacher (Cloud Authenticated)",
                    "roll_no": None
                }
        except Exception:
            pass
    if user:
        return {"success": True, "user": user}
    raise HTTPException(status_code=401, detail="Invalid credentials")

# --- User Management Endpoints (Admin) ---
@app.get("/api/users")
async def list_users():
    return storage.list_users()

@app.post("/api/users")
async def create_user(req: CreateUserReq):
    try:
        user = storage.create_user(
            username=req.username,
            email=req.email,
            password=req.password,
            role=req.role,
            full_name=req.full_name,
            roll_no=req.roll_no
        )
        await broadcast_event("user_created", user)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/users/{user_id}/password")
async def update_user_password(user_id: int, req: UpdateUserPasswordReq):
    try:
        ok = storage.update_user_password(user_id, req.password)
        if ok:
            user = storage.get_user_by_id(user_id)
            await broadcast_event("user_password_changed", {
                "user_id": user_id,
                "username": user.get("username") if user else ""
            })
            return {"status": "SUCCESS", "message": "Password updated successfully"}
        raise HTTPException(status_code=404, detail="User not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/users/{user_id}")
async def update_user(user_id: int, req: UpdateUserReq):
    ok = storage.update_user(
        user_id,
        full_name=req.full_name,
        email=req.email,
        roll_no=req.roll_no,
        username=req.username
    )
    if ok:
        user = storage.get_user_by_id(user_id)
        await broadcast_event("user_updated", user or {"user_id": user_id})
        return {"status": "UPDATED", "user": user}
    raise HTTPException(status_code=404, detail="User not found or nothing to update")

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int):
    ok = storage.delete_user(user_id)
    if ok:
        await broadcast_event("user_deleted", {"user_id": user_id})
        return {"status": "DELETED", "user_id": user_id}
    raise HTTPException(status_code=404, detail="User not found")

@app.get("/api/student/attendance")
async def get_student_attendance(roll_no: Optional[str] = None, student_id: Optional[int] = None):
    return storage.get_attendance_for_student(roll_no=roll_no, student_id=student_id)

@app.post("/api/student/attendance/export")
async def export_student_attendance(roll_no: str):
    export_dir = _get_export_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_roll = roll_no.replace('/', '_').replace('(', '').replace(')', '')
    target_file = os.path.join(export_dir, f"attendance_{clean_roll}_{timestamp}.csv")
    success = storage.export_student_attendance_to_csv(roll_no, target_file)
    if success:
        return {"status": "EXPORTED", "file_path": target_file}
    raise HTTPException(status_code=400, detail="No attendance records available for this student")

@app.get("/api/ping")
async def ping():
    return {"status": "ONLINE", "timestamp": time.time(), "engine": "AiCameraEngine"}

@app.websocket("/api/events")
async def websocket_events(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
