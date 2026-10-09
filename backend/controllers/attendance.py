from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.connection import get_db
from models.models import Attendance, AttendanceSession, Course, Student, User
from schemas.attendance import AttendanceSessionCreate, AttendanceSessionOut, AttendanceOut
from events.event_bus import event_bus
from utils.dependencies import require_role

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])

@router.post("/session", response_model=AttendanceSessionOut)
async def start_session(session_data: AttendanceSessionCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role(["ADMIN", "TEACHER"]))):
    course = db.query(Course).filter(Course.id == session_data.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    new_session = AttendanceSession(course_id=session_data.course_id)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    await event_bus.publish("SessionStarted", {"session_id": new_session.id, "course_id": course.id})
    return new_session

@router.get("/history", response_model=list[AttendanceOut])
def get_attendance_history(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(require_role(["ADMIN", "TEACHER"]))):
    records = db.query(Attendance).offset(skip).limit(limit).all()
    return records
