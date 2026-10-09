from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.connection import get_db
from models.models import Student, User
from schemas.student import StudentCreate, StudentOut
from utils.dependencies import require_role
from events.event_bus import event_bus

router = APIRouter(prefix="/api/students", tags=["Students"])

@router.post("", response_model=StudentOut)
async def create_student(student: StudentCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role(["ADMIN"]))):
    # Ensure the user exists if user_id is provided, or create a student independently (based on requirement)
    if student.user_id:
        db_user = db.query(User).filter(User.id == student.user_id).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
            
    db_student = db.query(Student).filter(Student.student_id_number == student.student_id_number).first()
    if db_student:
        raise HTTPException(status_code=400, detail="Student ID already registered")
        
    new_student = Student(**student.model_dump())
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    
    await event_bus.publish("StudentCreated", {"student_id": new_student.id, "student_id_number": new_student.student_id_number})
    return new_student

@router.get("", response_model=list[StudentOut])
def get_students(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(require_role(["ADMIN", "TEACHER"]))):
    students = db.query(Student).offset(skip).limit(limit).all()
    return students

@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role(["ADMIN", "TEACHER", "STUDENT"]))):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    # If student role, can only fetch themselves
    if current_user.role == "STUDENT" and student.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this student")
        
    return student
