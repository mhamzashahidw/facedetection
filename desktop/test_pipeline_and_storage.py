# ponytail: rigorous test suite for desktop biometric AI pipeline, offline SQLite queue, and bridge API
import os
import sys
import numpy as np
from fastapi.testclient import TestClient

desktop_dir = os.path.dirname(os.path.abspath(__file__))
if desktop_dir not in sys.path:
    sys.path.insert(0, desktop_dir)

try:
    from desktop.app.recognition.matcher import CosineMatcher
    from desktop.app.recognition.tracker import ConsecutiveFrameTracker
    from desktop.app.recognition.liveness import LivenessDetector
    from desktop.app.recognition.embedder import SFaceEmbedder
    from desktop.app.storage.local_db import LocalStorage
    from desktop.app.bridge_service import app as bridge_app
except ImportError:
    from app.recognition.matcher import CosineMatcher
    from app.recognition.tracker import ConsecutiveFrameTracker
    from app.recognition.liveness import LivenessDetector
    from app.recognition.embedder import SFaceEmbedder
    from app.storage.local_db import LocalStorage
    from app.bridge_service import app as bridge_app

def test_cosine_matcher_math():
    matcher = CosineMatcher(threshold=0.363)
    
    # Identical vectors -> similarity 1.0
    v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    assert abs(matcher.cosine_similarity(v1, v1) - 1.0) < 1e-5

    # Orthogonal vectors -> similarity 0.0
    v2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    assert abs(matcher.cosine_similarity(v1, v2) - 0.0) < 1e-5

    # Enrolled database match test
    enrolled = {
        1: np.array([1.0, 0.0, 0.0], dtype=np.float32),
        2: np.array([0.0, 1.0, 0.0], dtype=np.float32)
    }
    
    # Query matching student 1
    match_id, sim = matcher.find_best_match(v1, enrolled)
    assert match_id == 1
    assert abs(sim - 1.0) < 1e-5

    # Query matching nobody above threshold
    unmatched_query = np.array([-1.0, -1.0, 0.0], dtype=np.float32)
    match_id, sim = matcher.find_best_match(unmatched_query, enrolled)
    assert match_id is None

def test_liveness_detector():
    liveness = LivenessDetector(history_len=10, min_motion_variance=0.5)

    # Static photo fake: identical landmarks across 10 frames
    static_face = np.array([100, 100, 50, 50, 110, 110, 140, 110, 125, 125, 115, 140, 135, 140, 0.99])
    is_live = False
    for _ in range(12):
        is_live, _ = liveness.check_liveness(np.zeros((100, 100, 3)), static_face)
    assert not is_live, "Static photo should be flagged as spoof/non-live"

    # Natural motion: fluctuating landmarks
    liveness.reset()
    for i in range(12):
        jittered = static_face.copy()
        jittered[4:10] += (i % 3) * 2.5
        is_live, score = liveness.check_liveness(np.zeros((100, 100, 3)), jittered)
    assert is_live, "Natural facial micro-motion should be recognized as live human"

def test_local_storage_lifecycle(tmp_path):
    test_db = str(tmp_path / "test_lifecycle.db")
    storage = LocalStorage(db_path=test_db)

    # 1. Enrolled student biometrics
    emb = np.random.rand(128).astype(np.float32)
    storage.save_enrolled_student(1, "2024-CS-001", "Alice Johnson", emb)

    embeddings = storage.get_all_enrolled_embeddings()
    assert 1 in embeddings
    assert embeddings[1].shape == (128,)

    details = storage.get_student_details(1)
    assert details == ("2024-CS-001", "Alice Johnson")

    # Update student details
    updated = storage.update_enrolled_student(1, roll_no="2024-CS-001-MOD", full_name="Alice Smith")
    assert updated is True
    assert storage.get_student_details(1) == ("2024-CS-001-MOD", "Alice Smith")

    # 2. Local sessions
    sid = storage.create_local_session(course_id=101, course_code="CS-401", course_name="SDA")
    assert sid == 1
    storage.end_local_session(sid)

    # 3. Queue attendance (offline-first)
    is_new = storage.queue_attendance(
        local_session_id=sid,
        student_id=1,
        roll_no="2024-CS-001",
        full_name="Alice Johnson",
        confidence=0.95
    )
    assert is_new is True

    # Duplicate should return False
    duplicate = storage.queue_attendance(
        local_session_id=sid,
        student_id=1,
        roll_no="2024-CS-001",
        full_name="Alice Johnson",
        confidence=0.95
    )
    assert duplicate is False

    # Check pending records
    pending = storage.get_pending_sync_records()
    assert len(pending) == 1
    assert pending[0]["synced"] == 0

    # Mark synced
    storage.mark_records_synced([pending[0]["id"]])
    assert len(storage.get_pending_sync_records()) == 0

    # CSV Export
    csv_file = str(tmp_path / "attendance_out.csv")
    exported = storage.export_session_to_csv(sid, csv_file)
    assert exported is True
    assert os.path.exists(csv_file)

def test_bridge_service_api():
    bridge_client = TestClient(bridge_app)

    # 1. Status
    res = bridge_client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert "active_session" in data
    assert "camera" in data
    assert "stats" in data

    # 2. Start session
    start_res = bridge_client.post("/api/session/start", json={
        "course_id": 101,
        "course_code": "CS-401",
        "course_name": "Software Architecture"
    })
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "SUCCESS"

    # 3. Camera controls
    cam_start = bridge_client.post("/api/camera/start?camera_index=0")
    assert cam_start.status_code == 200
    cam_stop = bridge_client.post("/api/camera/stop")
    assert cam_stop.status_code == 200

    # 4. Enroll & list students
    enroll_res = bridge_client.post("/api/enroll", json={
        "student_id": 999,
        "roll_no": "2024-TEST-999",
        "full_name": "Test Student"
    })
    assert enroll_res.status_code == 200

    enrolled_list = bridge_client.get("/api/enrolled")
    assert enrolled_list.status_code == 200
    assert any(s["student_id"] == 999 for s in enrolled_list.json())

    # Update enrolled student details
    patch_res = bridge_client.patch("/api/enrolled/999", json={
        "roll_no": "2024-TEST-999-EDITED",
        "full_name": "Test Student Edited"
    })
    assert patch_res.status_code == 200
    updated_list = bridge_client.get("/api/enrolled").json()
    matched = next(s for s in updated_list if s["student_id"] == 999)
    assert matched["roll_no"] == "2024-TEST-999-EDITED"
    assert matched["full_name"] == "Test Student Edited"

    # Delete enrolled
    del_res = bridge_client.delete("/api/enrolled/999")
    assert del_res.status_code == 200

    # 5. End session
    end_res = bridge_client.post("/api/session/end")
    assert end_res.status_code == 200

    # 6. Manual attendance, export, and record deletion
    s2 = bridge_client.post("/api/session/start", json={
        "course_id": 102,
        "course_code": "CS-402",
        "course_name": "Design Patterns"
    })
    assert s2.status_code == 200

    man_res = bridge_client.post("/api/records/manual", json={
        "student_id": 888,
        "roll_no": "2024-TEST-888",
        "full_name": "Manual Student"
    })
    assert man_res.status_code == 200
    recs = bridge_client.get("/api/records").json()
    assert any(r["student_id"] == 888 for r in recs)

    exp_res = bridge_client.post("/api/records/export")
    assert exp_res.status_code == 200
    assert "file_path" in exp_res.json()

    rec_id = next(r["id"] for r in recs if r["student_id"] == 888)
    del_rec = bridge_client.delete(f"/api/records/{rec_id}")
    assert del_rec.status_code == 200

    bridge_client.post("/api/session/end")

def test_bridge_user_management_endpoints(tmp_path):
    bridge_client = TestClient(bridge_app)

    # 1. List users
    users_res = bridge_client.get("/api/users")
    assert users_res.status_code == 200
    users = users_res.json()
    assert len(users) >= 3

    # 2. Create user (student)
    create_res = bridge_client.post("/api/users", json={
        "username": "2026-SE-500",
        "email": "student500@univision.edu",
        "password": "initial_password_123",
        "role": "student",
        "full_name": "Ada Lovelace",
        "roll_no": "2026-SE-500"
    })
    assert create_res.status_code == 200
    created_user = create_res.json()
    u_id = created_user["id"]

    # Verify login with initial password
    login_ok = bridge_client.post("/api/auth/login", json={
        "identifier": "2026-SE-500",
        "password": "initial_password_123",
        "role": "student"
    })
    assert login_ok.status_code == 200

    # 3. Edit/Change password
    pwd_res = bridge_client.put(f"/api/users/{u_id}/password", json={
        "password": "new_updated_password_456"
    })
    assert pwd_res.status_code == 200

    # Verify old password fails
    login_old_fail = bridge_client.post("/api/auth/login", json={
        "identifier": "2026-SE-500",
        "password": "initial_password_123",
        "role": "student"
    })
    assert login_old_fail.status_code == 401

    # Verify new password succeeds
    login_new_ok = bridge_client.post("/api/auth/login", json={
        "identifier": "2026-SE-500",
        "password": "new_updated_password_456",
        "role": "student"
    })
    assert login_new_ok.status_code == 200

    # 4. Update user details
    update_res = bridge_client.put(f"/api/users/{u_id}", json={
        "full_name": "Ada Lovelace Countess of Lovelace"
    })
    assert update_res.status_code == 200
    assert update_res.json()["user"]["full_name"] == "Ada Lovelace Countess of Lovelace"

    # 5. Delete user
    del_res = bridge_client.delete(f"/api/users/{u_id}")
    assert del_res.status_code == 200


