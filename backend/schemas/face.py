from pydantic import BaseModel
from typing import List

class FaceEnrollRequest(BaseModel):
    student_id: int
    images_base64: List[str]

class FaceRecognizeRequest(BaseModel):
    image_base64: str
    session_id: int

class FaceRecognizeResponse(BaseModel):
    status: str
    student_id: int = None
    similarity: float = None
    message: str = None
