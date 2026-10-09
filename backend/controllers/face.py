import json
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.connection import get_db
from models.models import FaceProfile, Student, Attendance, AttendanceSession, User
from schemas.face import FaceEnrollRequest, FaceRecognizeRequest, FaceRecognizeResponse
from algorithms.face_engine import face_engine
from events.event_bus import event_bus
from utils.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/face", tags=["Face Recognition"])

@router.post("/enroll")
async def enroll_face(request: FaceEnrollRequest, db: Session = Depends(get_db), current_user: User = Depends(require_role(["ADMIN"]))):
    student = db.query(Student).filter(Student.id == request.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    await event_bus.publish("FaceEnrollmentStarted", {"student_id": request.student_id})

    all_embeddings = []
    for b64_img in request.images_base64:
        img = face_engine.decode_base64_image(b64_img)
        try:
            emb = face_engine.get_embedding(img)
            all_embeddings.append(emb)
        except ValueError as e:
            continue # Skip bad frames
            
    if not all_embeddings:
        raise HTTPException(status_code=400, detail="Could not detect a valid face in any of the provided images.")

    # Average the embeddings for a robust profile
    avg_embedding = np.mean(all_embeddings, axis=0).tolist()

    # Save to DB
    profile = db.query(FaceProfile).filter(FaceProfile.student_id == request.student_id).first()
    if profile:
        profile.embedding_json = json.dumps(avg_embedding)
    else:
        profile = FaceProfile(student_id=request.student_id, embedding_json=json.dumps(avg_embedding))
        db.add(profile)
        
    db.commit()
    
    await event_bus.publish("FaceEnrollmentCompleted", {"student_id": request.student_id})
    return {"message": "Face enrolled successfully"}

@router.post("/recognize", response_model=FaceRecognizeResponse)
async def recognize_face(request: FaceRecognizeRequest, db: Session = Depends(get_db)):
    await event_bus.publish("FaceRecognitionStarted", {"session_id": request.session_id})
    
    # 1. Process incoming image
    img = face_engine.decode_base64_image(request.image_base64)
    try:
        live_embedding = face_engine.get_embedding(img)
    except ValueError as e:
        await event_bus.publish("FaceDetectionFailed", {"reason": str(e)})
        return {"status": "FAILED", "message": str(e)}

    # 2. Retrieve all profiles (In a real scenario, this would be cached in-memory)
    # This demonstrates the DSA vector search concept
    profiles = db.query(FaceProfile).all()
    
    best_match_student_id = None
    highest_similarity = -1.0
    THRESHOLD = 0.60 # Typical threshold for Cosine Similarity
    
    for profile in profiles:
        db_embedding = json.loads(profile.embedding_json)
        similarity = face_engine.calculate_similarity(live_embedding, db_embedding)
        
        if similarity > highest_similarity:
            highest_similarity = similarity
            best_match_student_id = profile.student_id

    if highest_similarity >= THRESHOLD:
        await event_bus.publish("FaceRecognized", {
            "student_id": best_match_student_id, 
            "similarity": highest_similarity,
            "session_id": request.session_id
        })
        return {
            "status": "SUCCESS", 
            "student_id": best_match_student_id, 
            "similarity": float(highest_similarity),
            "message": "Face Recognized"
        }
    else:
        await event_bus.publish("UnknownFaceDetected", {"max_similarity": highest_similarity})
        return {"status": "UNKNOWN", "message": "Unknown Face"}

from pydantic import BaseModel
class FrameValidationRequest(BaseModel):
    image_base64: str

@router.post("/validate_frame")
async def validate_frame(request: FrameValidationRequest):
    img = face_engine.decode_base64_image(request.image_base64)
    try:
        # Just check if we can extract a face
        face_engine.get_embedding(img)
        return {"status": "SUCCESS", "message": "Face detected"}
    except ValueError as e:
        return {"status": "FAILED", "message": str(e)}
