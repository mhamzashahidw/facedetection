import os
from datetime import datetime, timedelta, timezone
from typing import Optional
try:
    from jose import JWTError, jwt
except ImportError:
    import jwt
    from jwt.exceptions import PyJWTError as JWTError
# ponytail: direct bcrypt hashing, minimal dependencies, safe sub casting
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
import hashlib
from .models import Student, Teacher, Admin

SECRET_KEY = os.getenv("SECRET_KEY", "focus-attendance-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    try:
        if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        pass
    
    # Check SHA-256 with univision_ salt (used in local storage)
    sha_hash = hashlib.sha256(f"univision_{plain_password}".encode('utf-8')).hexdigest()
    if hashed_password == sha_hash:
        return True
    
    # Check plain equality for dev/testing
    if hashed_password == plain_password:
        return True

    return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    # ponytail: RFC 7519 requires JWT sub claim to be string
    to_encode = data.copy()
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

security_bearer = HTTPBearer()

def decode_token(credentials: HTTPAuthorizationCredentials = Depends(security_bearer)) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_teacher(payload: dict = Depends(decode_token), db: Session = Depends(get_db)) -> Teacher:
    if payload.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="Teacher credentials required")
    try:
        teacher_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token subject")
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return teacher

def get_current_admin(payload: dict = Depends(decode_token), db: Session = Depends(get_db)) -> Admin:
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin credentials required")
    try:
        admin_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token subject")
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    return admin

def get_current_student(payload: dict = Depends(decode_token), db: Session = Depends(get_db)) -> Student:
    if payload.get("role") != "student":
        raise HTTPException(status_code=403, detail="Student credentials required")
    try:
        student_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token subject")
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student
