# ponytail: rigorous backend integration tests with zero external test plugins
import os
import sys
from fastapi.testclient import TestClient

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from backend.app.main import app
    from backend.app.database import SessionLocal, engine
    from backend.app.models import Base, Teacher, Student, Course, Session as CourseSession, Attendance, Enrollment
    from backend.app.auth_utils import get_password_hash
    from backend.seed_data import seed
except ImportError:
    from app.main import app
    from app.database import SessionLocal, engine
    from app.models import Base, Teacher, Student, Course, Session as CourseSession, Attendance, Enrollment
    from app.auth_utils import get_password_hash
    from seed_data import seed

client = TestClient(app)

def setup_module():
    seed()

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "documentation" in data

def test_auth_teacher_success_and_failure():
    # Success
    res = client.post("/auth/teacher/login", json={
        "email": "teacher@school.edu",
        "password": "teacher123"
    })
    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body
    assert body["role"] == "teacher"
    assert body["full_name"] == "Prof. Alan Turing"

    # Bad password
    bad_res = client.post("/auth/teacher/login", json={
        "email": "teacher@school.edu",
        "password": "wrongpassword"
    })
    assert bad_res.status_code == 401

    # Non-existent user
    not_found = client.post("/auth/teacher/login", json={
        "email": "ghost@school.edu",
        "password": "teacher123"
    })
    assert not_found.status_code == 401

def test_auth_student_success_and_failure():
    # Success
    res = client.post("/auth/student/login", json={
        "roll_no": "2024-CS-001",
        "password": "student123"
    })
    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body
    assert body["role"] == "student"
    assert body["full_name"] == "Alice Johnson"

    # Bad password
    bad_res = client.post("/auth/student/login", json={
        "roll_no": "2024-CS-001",
        "password": "badpassword"
    })
    assert bad_res.status_code == 401

def test_session_lifecycle_and_authorization():
    # 1. Login teacher to get token
    login_res = client.post("/auth/teacher/login", json={
        "email": "teacher@school.edu",
        "password": "teacher123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    course = db.query(Course).first()
    db.close()
    assert course is not None

    # 2. Start session
    start_res = client.post("/sessions", json={"course_id": course.id}, headers=headers)
    assert start_res.status_code == 201
    session_data = start_res.json()
    assert session_data["course_id"] == course.id
    session_id = session_data["id"]

    # 3. Unauthorized access (student token attempting teacher session start)
    student_login = client.post("/auth/student/login", json={
        "roll_no": "2024-CS-001",
        "password": "student123"
    })
    st_token = student_login.json()["access_token"]
    st_headers = {"Authorization": f"Bearer {st_token}"}

    forbidden_res = client.post("/sessions", json={"course_id": course.id}, headers=st_headers)
    assert forbidden_res.status_code == 403

    # 4. End session
    end_res = client.patch(f"/sessions/{session_id}/end", headers=headers)
    assert end_res.status_code == 200
    assert end_res.json()["ended_at"] is not None

def test_batch_attendance_upload_and_idempotency():
    # Teacher login
    login_res = client.post("/auth/teacher/login", json={
        "email": "teacher@school.edu",
        "password": "teacher123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    session = db.query(CourseSession).first()
    students = db.query(Student).all()
    db.close()

    assert session is not None
    assert len(students) >= 2

    # Batch upload for students
    batch_payload = {
        "session_id": session.id,
        "records": [
            {
                "student_id": students[0].id,
                "method": "face",
                "confidence": 0.95
            },
            {
                "student_id": students[1].id,
                "method": "face",
                "confidence": 0.91
            }
        ]
    }

    res = client.post("/attendance/batch", json=batch_payload, headers=headers)
    assert res.status_code == 200
    records = res.json()
    assert len(records) >= 2

    # Test idempotency: re-upload same batch without error or duplicates
    res_idempotent = client.post("/attendance/batch", json=batch_payload, headers=headers)
    assert res_idempotent.status_code == 200
    re_records = res_idempotent.json()
    assert len(re_records) >= 2

    # Manual correction
    att_id = records[0]["id"]
    patch_res = client.patch(f"/attendance/{att_id}", json={"method": "manual", "confidence": 1.0}, headers=headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["method"] == "manual"
    assert patch_res.json()["confidence"] == 1.0

def test_student_self_service_attendance_and_summary():
    student_login = client.post("/auth/student/login", json={
        "roll_no": "2024-CS-001",
        "password": "student123"
    })
    token = student_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. My Attendance list
    att_res = client.get("/me/attendance", headers=headers)
    assert att_res.status_code == 200
    records = att_res.json()
    assert isinstance(records, list)

    # 2. My Summary percentages
    sum_res = client.get("/me/summary", headers=headers)
    assert sum_res.status_code == 200
    summaries = sum_res.json()
    assert isinstance(summaries, list)
    if summaries:
        assert "attendance_percentage" in summaries[0]
        assert "is_below_threshold" in summaries[0]

def test_admin_user_and_password_management():
    # 1. Admin Login
    admin_res = client.post("/auth/admin/login", json={
        "username_or_email": "admin",
        "password": "admin123"
    })
    assert admin_res.status_code == 200
    admin_token = admin_res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. List all users
    users_res = client.get("/admin/users", headers=admin_headers)
    assert users_res.status_code == 200
    users = users_res.json()
    assert len(users) >= 4 # admin + teacher + 3 students
    roles = {u["role"] for u in users}
    assert "admin" in roles and "teacher" in roles and "student" in roles

    # 3. Admin creates a new student with password
    create_st_res = client.post("/admin/users", json={
        "username": "2026-CS-999",
        "roll_no": "2026-CS-999",
        "full_name": "Test Managed Student",
        "email": "managed_student@school.edu",
        "role": "student",
        "password": "initial_password_123"
    }, headers=admin_headers)
    assert create_st_res.status_code == 201
    new_st = create_st_res.json()
    st_id = new_st["id"]

    # Verify student can login with initial password
    st_login = client.post("/auth/student/login", json={
        "roll_no": "2026-CS-999",
        "password": "initial_password_123"
    })
    assert st_login.status_code == 200

    # 4. Admin edits/updates password for this student
    pwd_update_res = client.put(f"/admin/users/student/{st_id}/password", json={
        "new_password": "super_secret_updated_pwd"
    }, headers=admin_headers)
    assert pwd_update_res.status_code == 200
    assert pwd_update_res.json()["status"] == "SUCCESS"

    # Verify old password fails
    old_fail = client.post("/auth/student/login", json={
        "roll_no": "2026-CS-999",
        "password": "initial_password_123"
    })
    assert old_fail.status_code == 401

    # Verify new password succeeds immediately
    new_ok = client.post("/auth/student/login", json={
        "roll_no": "2026-CS-999",
        "password": "super_secret_updated_pwd"
    })
    assert new_ok.status_code == 200

    # 5. Admin edits/updates password for teacher
    db = SessionLocal()
    teacher = db.query(Teacher).filter(Teacher.email == "teacher@school.edu").first()
    t_id = teacher.id
    db.close()

    t_pwd_res = client.put(f"/admin/users/teacher/{t_id}/password", json={
        "new_password": "teacher_new_secure_pwd"
    }, headers=admin_headers)
    assert t_pwd_res.status_code == 200

    # Verify teacher can login with new password
    t_login = client.post("/auth/teacher/login", json={
        "email": "teacher@school.edu",
        "password": "teacher_new_secure_pwd"
    })
    assert t_login.status_code == 200

    # Reset teacher password back to default for other tests
    client.put(f"/admin/users/teacher/{t_id}/password", json={
        "new_password": "teacher123"
    }, headers=admin_headers)

    # 6. Cleanup created test student
    del_res = client.delete(f"/admin/users/student/{st_id}", headers=admin_headers)
    assert del_res.status_code == 200

