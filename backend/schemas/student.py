from pydantic import BaseModel
from typing import Optional

class StudentCreate(BaseModel):
    student_id_number: str
    department: str
    program: str
    semester: int
    section: str
    user_id: Optional[int] = None

class StudentOut(BaseModel):
    id: int
    student_id_number: str
    department: str
    program: str
    semester: int
    section: str

    class Config:
        from_attributes = True
