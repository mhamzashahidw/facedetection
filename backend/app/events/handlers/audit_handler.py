import json
import logging
from ..event_bus import event_bus
from ...database import SessionLocal
from ...models import AuditLog

logger = logging.getLogger("backend.handlers.audit")

async def record_audit_log(action: str, entity_type: str, entity_id: int, details: dict):
    db = SessionLocal()
    try:
        log = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=json.dumps(details, default=str)
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.error(f"[AuditHandler] Failed to record audit log for {action}: {e}")
        db.rollback()
    finally:
        db.close()

async def on_attendance_marked(payload: dict):
    await record_audit_log(
        action="ATTENDANCE_MARKED",
        entity_type="Attendance",
        entity_id=payload.get("attendance_id"),
        details=payload
    )

async def on_session_started(payload: dict):
    await record_audit_log(
        action="SESSION_STARTED",
        entity_type="Session",
        entity_id=payload.get("session_id"),
        details=payload
    )

async def on_session_ended(payload: dict):
    await record_audit_log(
        action="SESSION_ENDED",
        entity_type="Session",
        entity_id=payload.get("session_id"),
        details=payload
    )

async def on_teacher_logged_in(payload: dict):
    await record_audit_log(
        action="TEACHER_LOGGED_IN",
        entity_type="Teacher",
        entity_id=payload.get("teacher_id"),
        details=payload
    )

async def on_student_logged_in(payload: dict):
    await record_audit_log(
        action="STUDENT_LOGGED_IN",
        entity_type="Student",
        entity_id=payload.get("student_id"),
        details=payload
    )

event_bus.subscribe("AttendanceMarked", on_attendance_marked)
event_bus.subscribe("SessionStarted", on_session_started)
event_bus.subscribe("SessionEnded", on_session_ended)
event_bus.subscribe("TeacherLoggedIn", on_teacher_logged_in)
event_bus.subscribe("StudentLoggedIn", on_student_logged_in)
