from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime

# --- Auth Schemas ---
class StudentLogin(BaseModel):
    roll_no: str
    password: str

class TeacherLogin(BaseModel):
    email: EmailStr
    password: str

class AdminLogin(BaseModel):
    username_or_email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    full_name: str

# --- User Management Schemas ---
class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: str
    role: str
    roll_no: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class UserCreate(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    password: str
    full_name: str
    role: str # 'student', 'teacher', or 'admin'
    roll_no: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    roll_no: Optional[str] = None
    username: Optional[str] = None

class PasswordUpdate(BaseModel):
    new_password: str

# --- Session Schemas ---
class SessionCreate(BaseModel):
    course_id: int

class SessionOut(BaseModel):
    id: int
    course_id: int
    started_at: datetime
    ended_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# --- Attendance Schemas ---
class AttendanceRecordItem(BaseModel):
    student_id: int
    marked_at: Optional[datetime] = None
    method: str = "face" # 'face' or 'manual'
    confidence: Optional[float] = None

class AttendanceBatchUpload(BaseModel):
    session_id: int
    records: List[AttendanceRecordItem]

class AttendanceUpdate(BaseModel):
    method: Optional[str] = None # 'manual'
    confidence: Optional[float] = None

class AttendanceOut(BaseModel):
    id: int
    session_id: int
    student_id: int
    marked_at: datetime
    method: str
    confidence: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

# --- Student Analytics & Mobile Schemas ---
class StudentAttendanceItem(BaseModel):
    attendance_id: int
    course_code: str
    course_name: str
    session_id: int
    marked_at: datetime
    method: str

class CourseSummary(BaseModel):
    course_id: int
    course_code: str
    course_name: str
    total_sessions: int
    attended_sessions: int
    attendance_percentage: float
    is_below_threshold: bool # True if percentage < 75%
