import sys
import os
import numpy as np
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

desktop_dir = os.path.dirname(os.path.abspath(__file__))
if desktop_dir not in sys.path:
    sys.path.insert(0, desktop_dir)

try:
    from desktop.app.storage.local_db import LocalStorage
    from desktop.app.ui.main_window import MainWindow
    from desktop.app.controllers.session_controller import SessionController
except ImportError:
    from app.storage.local_db import LocalStorage
    from app.ui.main_window import MainWindow
    from app.controllers.session_controller import SessionController

def test_local_storage_auth_and_roles(tmp_path):
    test_db = str(tmp_path / "test_auth_roles.db")
    storage = LocalStorage(db_path=test_db)

    # 1. Admin login verification
    admin_user = storage.authenticate_user("admin", "admin123", role="admin")
    assert admin_user is not None
    assert admin_user["role"] == "admin"
    assert admin_user["username"] == "admin"

    # Mismatched role rejection
    assert storage.authenticate_user("admin", "admin123", role="teacher") is None
    # Wrong password rejection
    assert storage.authenticate_user("admin", "wrong_pass", role="admin") is None

    # 2. Teacher login verification
    teacher_user = storage.authenticate_user("teacher", "teacher123", role="teacher")
    assert teacher_user is not None
    assert teacher_user["role"] == "teacher"

    # 3. Student login verification
    student_user = storage.authenticate_user("2024-CS-001", "student123", role="student")
    assert student_user is not None
    assert student_user["role"] == "student"
    assert student_user["roll_no"] == "2024-CS-001"

def test_admin_enrollment_and_biometric_student_login(tmp_path):
    test_db = str(tmp_path / "test_bio_login.db")
    storage = LocalStorage(db_path=test_db)

    # Admin enrolls a new student with face embedding
    dummy_emb = np.random.rand(128).astype(np.float32)
    new_roll = "2026-SE-100"
    storage.save_enrolled_student(
        student_id=100,
        roll_no=new_roll,
        full_name="Grace Hopper",
        embedding=dummy_emb
    )

    # Verify student is in enrolled directory
    enrolled = storage.list_enrolled_students()
    assert any(s["roll_no"] == new_roll for s in enrolled)

    # Verify newly enrolled student can immediately log in with default student password or roll
    auth_user = storage.authenticate_user(new_roll, "student123", role="student")
    assert auth_user is not None
    assert auth_user["full_name"] == "Grace Hopper"
    assert auth_user["role"] == "student"

def test_student_attendance_isolation(tmp_path):
    test_db = str(tmp_path / "test_student_isolation.db")
    storage = LocalStorage(db_path=test_db)

    # Create local lecture session
    sid = storage.create_local_session(course_id=101, course_code="CS-401", course_name="Software Architecture")

    # Queue attendance for Student A and Student B
    storage.queue_attendance(
        local_session_id=sid,
        student_id=1,
        roll_no="2024-CS-001",
        full_name="Alice Johnson",
        method="face",
        confidence=0.92
    )
    storage.queue_attendance(
        local_session_id=sid,
        student_id=2,
        roll_no="2024-CS-002",
        full_name="Bob Smith",
        method="face",
        confidence=0.88
    )

    # Student A queries attendance
    alice_records = storage.get_attendance_for_student(roll_no="2024-CS-001")
    assert len(alice_records) == 1
    assert alice_records[0]["roll_no"] == "2024-CS-001"
    assert alice_records[0]["course_code"] == "CS-401"
    assert alice_records[0]["course_name"] == "Software Architecture"

    # Student B queries attendance
    bob_records = storage.get_attendance_for_student(roll_no="2024-CS-002")
    assert len(bob_records) == 1
    assert bob_records[0]["roll_no"] == "2024-CS-002"

    # Admin/Teacher queries all attendance
    all_records = storage.get_all_attendance_with_sessions()
    assert len(all_records) == 2

def test_main_window_role_views_and_navigation(tmp_path):
    app = QApplication.instance() or QApplication(sys.argv)
    test_db = str(tmp_path / "test_ui_roles.db")
    storage = LocalStorage(db_path=test_db)

    win = MainWindow()
    win.storage = storage

    # 1. Starts at Login screen (main_stack index 0)
    assert win.main_stack.currentIndex() == 0

    # 2. Login as Admin
    win.login_view.quick_demo_login("admin", "admin", "admin123")
    assert win.main_stack.currentIndex() == 1
    assert win.current_user["role"] == "admin"
    admin_nav = [btn.text().strip() for btn, _, _ in win.nav_buttons]
    assert "Attendance Logs" in admin_nav
    assert "Biometrics Enroll" in admin_nav
    assert "Live Monitoring" in admin_nav
    assert "Cloud & Diagnostics" in admin_nav

    # 3. Logout and login as Teacher
    win.on_logout_clicked = lambda: (setattr(win, 'current_user', None), win.main_stack.setCurrentIndex(0))
    win.on_logout_clicked()
    assert win.main_stack.currentIndex() == 0

    win.login_view.quick_demo_login("teacher", "teacher", "teacher123")
    assert win.main_stack.currentIndex() == 1
    assert win.current_user["role"] == "teacher"
    teacher_nav = [btn.text().strip() for btn, _, _ in win.nav_buttons]
    assert "Live Class Session" in teacher_nav
    assert "Student Attendance" in teacher_nav
    # Teacher must NOT have biometric enroll permissions
    assert "Biometrics Enroll" not in teacher_nav

    # 4. Logout and login as Student
    win.on_logout_clicked()
    assert win.main_stack.currentIndex() == 0

    win.login_view.quick_demo_login("student", "2024-CS-001", "student123")
    assert win.main_stack.currentIndex() == 1
    assert win.current_user["role"] == "student"
    student_nav = [btn.text().strip() for btn, _, _ in win.nav_buttons]
    assert "My Attendance" in student_nav
    # Student must NOT have teacher session or admin enroll permissions
    assert "Live Class Session" not in student_nav
    assert "Live Monitoring" not in student_nav
    assert "Biometrics Enroll" not in student_nav

    win.close()

def test_admin_can_make_and_edit_user_passwords(tmp_path):
    test_db = str(tmp_path / "test_pwd_mgmt.db")
    storage = LocalStorage(db_path=test_db)

    # 1. Admin creates teacher user
    t_user = storage.create_user(
        username="newteacher",
        email="newteacher@school.edu",
        password="initial_teacher_pwd",
        role="teacher",
        full_name="Dr. Claude Shannon"
    )
    assert t_user["id"] is not None
    assert t_user["username"] == "newteacher"

    # Login with initial password succeeds
    assert storage.authenticate_user("newteacher", "initial_teacher_pwd", role="teacher") is not None

    # 2. Admin edits password for the teacher
    ok = storage.update_user_password(t_user["id"], "updated_teacher_secret_999")
    assert ok is True

    # Old password fails
    assert storage.authenticate_user("newteacher", "initial_teacher_pwd", role="teacher") is None
    # New password succeeds
    assert storage.authenticate_user("newteacher", "updated_teacher_secret_999", role="teacher") is not None

    # 3. Admin creates student user
    s_user = storage.create_user(
        username="2026-CS-777",
        email="student777@school.edu",
        password="custom_student_initial_pwd",
        role="student",
        full_name="John von Neumann",
        roll_no="2026-CS-777"
    )
    assert s_user["id"] is not None

    # Login with custom initial password
    assert storage.authenticate_user("2026-CS-777", "custom_student_initial_pwd", role="student") is not None

    # 4. Admin edits student's password
    ok_st = storage.update_user_password(s_user["id"], "john_new_password_888")
    assert ok_st is True

    # Old password fails
    assert storage.authenticate_user("2026-CS-777", "custom_student_initial_pwd", role="student") is None
    # Default student123 fails because a custom password was explicitly set
    assert storage.authenticate_user("2026-CS-777", "student123", role="student") is None
    # New password succeeds
    assert storage.authenticate_user("2026-CS-777", "john_new_password_888", role="student") is not None

