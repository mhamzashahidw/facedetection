from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from ..database import get_db
from ..models import Admin, Teacher, Student
from ..schemas import UserOut, UserCreate, UserUpdate, PasswordUpdate
from ..auth_utils import get_current_admin, get_password_hash
from ..events.event_bus import event_bus

router = APIRouter(prefix="/admin", tags=["Admin Management"])

@router.get("/users", response_model=List[UserOut])
def list_all_users(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Returns unified list of all user accounts across roles (Admins, Teachers, Students).
    """
    users = []

    # 1. Admins
    admins = db.query(Admin).all()
    for a in admins:
        users.append(UserOut(
            id=a.id,
            username=a.username,
            email=a.email,
            full_name=a.full_name,
            role="admin",
            roll_no=None,
            created_at=a.created_at
        ))

    # 2. Teachers
    teachers = db.query(Teacher).all()
    for t in teachers:
        users.append(UserOut(
            id=t.id,
            username=t.email,
            email=t.email,
            full_name=t.full_name,
            role="teacher",
            roll_no=None,
            created_at=None
        ))

    # 3. Students
    students = db.query(Student).all()
    for s in students:
        users.append(UserOut(
            id=s.id,
            username=s.roll_no,
            email=s.email,
            full_name=s.full_name,
            role="student",
            roll_no=s.roll_no,
            created_at=s.created_at
        ))

    return users

@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Admin endpoint to provision a new user (Student, Teacher, or Admin) with password.
    """
    role = payload.role.strip().lower()
    hashed_pwd = get_password_hash(payload.password)

    if role == "student":
        roll_no = (payload.roll_no or payload.username).strip()
        existing = db.query(Student).filter(
            (Student.roll_no == roll_no) | 
            (payload.email is not None and Student.email == str(payload.email))
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Student with this roll number or email already exists")

        new_st = Student(
            roll_no=roll_no,
            full_name=payload.full_name.strip(),
            email=str(payload.email) if payload.email else None,
            password_hash=hashed_pwd,
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_st)
        db.commit()
        db.refresh(new_st)

        await event_bus.publish("UserCreated", {
            "role": "student",
            "user_id": new_st.id,
            "roll_no": new_st.roll_no,
            "full_name": new_st.full_name,
            "created_by": current_admin.username
        })

        return UserOut(
            id=new_st.id,
            username=new_st.roll_no,
            email=new_st.email,
            full_name=new_st.full_name,
            role="student",
            roll_no=new_st.roll_no,
            created_at=new_st.created_at
        )

    elif role == "teacher":
        email = str(payload.email or payload.username).strip()
        existing = db.query(Teacher).filter(Teacher.email == email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Teacher with this email already exists")

        new_t = Teacher(
            full_name=payload.full_name.strip(),
            email=email,
            password_hash=hashed_pwd
        )
        db.add(new_t)
        db.commit()
        db.refresh(new_t)

        await event_bus.publish("UserCreated", {
            "role": "teacher",
            "user_id": new_t.id,
            "email": new_t.email,
            "full_name": new_t.full_name,
            "created_by": current_admin.username
        })

        return UserOut(
            id=new_t.id,
            username=new_t.email,
            email=new_t.email,
            full_name=new_t.full_name,
            role="teacher",
            roll_no=None,
            created_at=None
        )

    elif role == "admin":
        username = payload.username.strip()
        email = str(payload.email or f"{username}@univision.edu").strip()
        existing = db.query(Admin).filter((Admin.username == username) | (Admin.email == email)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Admin with this username or email already exists")

        new_a = Admin(
            username=username,
            email=email,
            full_name=payload.full_name.strip(),
            password_hash=hashed_pwd,
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_a)
        db.commit()
        db.refresh(new_a)

        return UserOut(
            id=new_a.id,
            username=new_a.username,
            email=new_a.email,
            full_name=new_a.full_name,
            role="admin",
            roll_no=None,
            created_at=new_a.created_at
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported role: '{payload.role}'. Use 'student', 'teacher', or 'admin'.")

@router.put("/users/{role}/{user_id}/password")
async def update_user_password(
    role: str,
    user_id: int,
    payload: PasswordUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Admin endpoint to change or edit password for students, teachers, or administrators.
    """
    clean_role = role.strip().lower()
    clean_pwd = payload.new_password.strip()

    if len(clean_pwd) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters long")

    hashed_pwd = get_password_hash(clean_pwd)

    if clean_role == "student":
        student = db.query(Student).filter(Student.id == user_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        student.password_hash = hashed_pwd
        db.commit()

        await event_bus.publish("PasswordChanged", {
            "role": "student",
            "user_id": user_id,
            "roll_no": student.roll_no,
            "changed_by": current_admin.username
        })
        return {"status": "SUCCESS", "message": f"Password updated for student {student.roll_no} ({student.full_name})"}

    elif clean_role == "teacher":
        teacher = db.query(Teacher).filter(Teacher.id == user_id).first()
        if not teacher:
            raise HTTPException(status_code=404, detail="Teacher not found")
        teacher.password_hash = hashed_pwd
        db.commit()

        await event_bus.publish("PasswordChanged", {
            "role": "teacher",
            "user_id": user_id,
            "email": teacher.email,
            "changed_by": current_admin.username
        })
        return {"status": "SUCCESS", "message": f"Password updated for teacher {teacher.email} ({teacher.full_name})"}

    elif clean_role == "admin":
        admin = db.query(Admin).filter(Admin.id == user_id).first()
        if not admin:
            raise HTTPException(status_code=404, detail="Admin not found")
        admin.password_hash = hashed_pwd
        db.commit()
        return {"status": "SUCCESS", "message": f"Password updated for admin {admin.username}"}

    raise HTTPException(status_code=400, detail="Invalid role specified")

@router.put("/users/{role}/{user_id}", response_model=UserOut)
def update_user_details(
    role: str,
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Admin endpoint to update user details (name, email, roll number).
    """
    clean_role = role.strip().lower()

    if clean_role == "student":
        student = db.query(Student).filter(Student.id == user_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        if payload.full_name:
            student.full_name = payload.full_name.strip()
        if payload.email:
            student.email = str(payload.email).strip()
        if payload.roll_no:
            student.roll_no = payload.roll_no.strip()
        db.commit()
        db.refresh(student)
        return UserOut(
            id=student.id,
            username=student.roll_no,
            email=student.email,
            full_name=student.full_name,
            role="student",
            roll_no=student.roll_no,
            created_at=student.created_at
        )

    elif clean_role == "teacher":
        teacher = db.query(Teacher).filter(Teacher.id == user_id).first()
        if not teacher:
            raise HTTPException(status_code=404, detail="Teacher not found")
        if payload.full_name:
            teacher.full_name = payload.full_name.strip()
        if payload.email:
            teacher.email = str(payload.email).strip()
        db.commit()
        db.refresh(teacher)
        return UserOut(
            id=teacher.id,
            username=teacher.email,
            email=teacher.email,
            full_name=teacher.full_name,
            role="teacher",
            roll_no=None,
            created_at=None
        )

    elif clean_role == "admin":
        admin = db.query(Admin).filter(Admin.id == user_id).first()
        if not admin:
            raise HTTPException(status_code=404, detail="Admin not found")
        if payload.full_name:
            admin.full_name = payload.full_name.strip()
        if payload.email:
            admin.email = str(payload.email).strip()
        if payload.username:
            admin.username = payload.username.strip()
        db.commit()
        db.refresh(admin)
        return UserOut(
            id=admin.id,
            username=admin.username,
            email=admin.email,
            full_name=admin.full_name,
            role="admin",
            roll_no=None,
            created_at=admin.created_at
        )

    raise HTTPException(status_code=400, detail="Invalid role specified")

@router.delete("/users/{role}/{user_id}")
def delete_user(
    role: str,
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Admin endpoint to delete a user account.
    """
    clean_role = role.strip().lower()

    if clean_role == "student":
        student = db.query(Student).filter(Student.id == user_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        db.delete(student)
        db.commit()
        return {"status": "DELETED", "user_id": user_id, "role": "student"}

    elif clean_role == "teacher":
        teacher = db.query(Teacher).filter(Teacher.id == user_id).first()
        if not teacher:
            raise HTTPException(status_code=404, detail="Teacher not found")
        db.delete(teacher)
        db.commit()
        return {"status": "DELETED", "user_id": user_id, "role": "teacher"}

    elif clean_role == "admin":
        if user_id == current_admin.id:
            raise HTTPException(status_code=400, detail="Cannot delete your own active admin account")
        admin = db.query(Admin).filter(Admin.id == user_id).first()
        if not admin:
            raise HTTPException(status_code=404, detail="Admin not found")
        db.delete(admin)
        db.commit()
        return {"status": "DELETED", "user_id": user_id, "role": "admin"}

    raise HTTPException(status_code=400, detail="Invalid role specified")
