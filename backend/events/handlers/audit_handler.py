import json
from events.event_bus import event_bus
from database.connection import SessionLocal
from models.models import AuditLog

async def handle_audit_logging(payload: dict, action_name: str):
    db = SessionLocal()
    try:
        log = AuditLog(
            action=action_name,
            details=json.dumps(payload)
        )
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"Failed to write audit log: {e}")
    finally:
        db.close()

# Wrapping for specific events
async def log_user_registered(payload: dict):
    await handle_audit_logging(payload, "USER_REGISTERED")
    
async def log_face_enrolled(payload: dict):
    await handle_audit_logging(payload, "FACE_ENROLLED")

async def log_attendance_marked(payload: dict):
    await handle_audit_logging(payload, "ATTENDANCE_MARKED")
    
async def log_login_failed(payload: dict):
    await handle_audit_logging(payload, "LOGIN_FAILED")

# Subscribe to events
event_bus.subscribe("UserRegistered", log_user_registered)
event_bus.subscribe("FaceEnrollmentCompleted", log_face_enrolled)
event_bus.subscribe("AttendanceMarked", log_attendance_marked)
event_bus.subscribe("LoginFailed", log_login_failed)
