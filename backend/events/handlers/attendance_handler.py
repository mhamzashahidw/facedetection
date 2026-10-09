import datetime
from sqlalchemy.exc import IntegrityError
from events.event_bus import event_bus
from database.connection import SessionLocal
from models.models import Attendance, Student

async def handle_face_recognized(payload: dict):
    student_id = payload.get("student_id")
    session_id = payload.get("session_id")
    
    if not student_id or not session_id:
        return

    await event_bus.publish("AttendanceCheckStarted", {"student_id": student_id, "session_id": session_id})
    
    db = SessionLocal()
    try:
        # Check if already marked
        existing = db.query(Attendance).filter(
            Attendance.student_id == student_id,
            Attendance.session_id == session_id
        ).first()
        
        if existing:
            await event_bus.publish("AttendanceAlreadyMarked", {"student_id": student_id, "session_id": session_id})
            return
            
        new_attendance = Attendance(
            student_id=student_id,
            session_id=session_id,
            status="PRESENT",
            timestamp=datetime.datetime.utcnow()
        )
        db.add(new_attendance)
        db.commit()
        
        # Get student details for notification
        student = db.query(Student).filter(Student.id == student_id).first()
        
        await event_bus.publish("AttendanceMarked", {
            "student_id": student_id,
            "student_id_number": student.student_id_number if student else "Unknown",
            "session_id": session_id,
            "time": new_attendance.timestamp.isoformat(),
            "status": "PRESENT"
        })
        
    except IntegrityError:
        db.rollback()
        await event_bus.publish("AttendanceAlreadyMarked", {"student_id": student_id, "session_id": session_id})
    except Exception as e:
        db.rollback()
        print(f"Error marking attendance: {e}")
    finally:
        db.close()

# Register the handler
event_bus.subscribe("FaceRecognized", handle_face_recognized)
