from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AttendanceSessionCreate(BaseModel):
    course_id: int

class AttendanceSessionOut(BaseModel):
    id: int
    course_id: int
    start_time: datetime
    end_time: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True

class AttendanceOut(BaseModel):
    id: int
    student_id: int
    session_id: int
    timestamp: datetime
    status: str

    class Config:
        from_attributes = True
