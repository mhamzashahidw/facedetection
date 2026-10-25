import sys
import os

# Put backend root on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal
from app.models import Base, Student, Teacher, Admin, Course, Enrollment, Session as CourseSession, Attendance
from app.auth_utils import get_password_hash
from datetime import datetime, timezone, timedelta

def seed():
    print("Ensuring tables exist...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 0. Admin
        adm = db.query(Admin).filter((Admin.username == "admin") | (Admin.email == "admin@univision.edu")).first()
        if not adm:
            adm = Admin(
                username="admin",
                email="admin@univision.edu",
                full_name="System Administrator",
                password_hash=get_password_hash("admin123")
            )
            db.add(adm)
            db.commit()
            db.refresh(adm)
            print("Admin created: admin / admin123")
        else:
            adm.password_hash = get_password_hash("admin123")
            db.commit()

        # 1. Teachers
        t1 = db.query(Teacher).filter(Teacher.email == "teacher@school.edu").first()
        if not t1:
            t1 = Teacher(
                full_name="Prof. Alan Turing",
                email="teacher@school.edu",
                password_hash=get_password_hash("teacher123")
            )
            db.add(t1)
            db.commit()
            db.refresh(t1)
            print("Teacher created: teacher@school.edu / teacher123")
        else:
            t1.password_hash = get_password_hash("teacher123")
            db.commit()

        # Ensure teacher@univision.edu also exists for seamless cloud diagnostics
        t2 = db.query(Teacher).filter(Teacher.email == "teacher@univision.edu").first()
        if not t2:
            t2 = Teacher(
                full_name="Prof. Alan Turing",
                email="teacher@univision.edu",
                password_hash=get_password_hash("teacher123")
            )
            db.add(t2)
            db.commit()
        else:
            t2.password_hash = get_password_hash("teacher123")
            db.commit()

        # 2. Courses
        c1 = db.query(Course).filter(Course.code == "CS-401").first()
        if not c1:
            c1 = Course(
                code="CS-401",
                name="Software Design & Architecture",
                teacher_id=t1.id
            )
            db.add(c1)
            db.commit()
            db.refresh(c1)
            print("Course created: CS-401")

        # 3. Students
        students_data = [
            ("2024-CS-001", "Alice Johnson", "alice@student.edu", "student123"),
            ("2024-CS-002", "Bob Smith", "bob@student.edu", "student123"),
            ("2024-CS-003", "Charlie Davis", "charlie@student.edu", "student123")
        ]

        created_students = []
        for roll, name, email, pwd in students_data:
            st = db.query(Student).filter(Student.roll_no == roll).first()
            if not st:
                st = Student(
                    roll_no=roll,
                    full_name=name,
                    email=email,
                    password_hash=get_password_hash(pwd)
                )
                db.add(st)
                db.commit()
                db.refresh(st)
                print(f"Student created: {roll} ({name}) / {pwd}")
            else:
                st.password_hash = get_password_hash(pwd)
                db.commit()
            created_students.append(st)

        # 4. Enrollments
        for st in created_students:
            enr = db.query(Enrollment).filter(
                Enrollment.student_id == st.id,
                Enrollment.course_id == c1.id
            ).first()
            if not enr:
                enr = Enrollment(student_id=st.id, course_id=c1.id)
                db.add(enr)
                db.commit()

        # 5. Sessions & Attendance History
        now = datetime.now(timezone.utc)
        s1 = db.query(CourseSession).filter(CourseSession.course_id == c1.id).first()
        if not s1:
            s1 = CourseSession(
                course_id=c1.id,
                started_at=now - timedelta(days=2),
                ended_at=now - timedelta(days=2, hours=-1)
            )
            db.add(s1)
            db.commit()
            db.refresh(s1)

            # Mark Alice and Bob present in session 1
            a1 = Attendance(session_id=s1.id, student_id=created_students[0].id, method="face", confidence=0.88)
            a2 = Attendance(session_id=s1.id, student_id=created_students[1].id, method="face", confidence=0.91)
            db.add_all([a1, a2])
            db.commit()

        print("Database seeded successfully with sample data!")

    except Exception as e:
        db.rollback()
        print(f"Seed error: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed()
