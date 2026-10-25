import sqlite3
import os
import sys
import shutil
import json
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

class LocalStorage:
    """
    Offline-first local SQLite storage for the Windows Desktop App.
    Stores biometric embeddings LOCALLY on the machine (they never leave).
    Queues attendance records for offline-first synchronization with the cloud backend.
    """
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            if getattr(sys, 'frozen', False):
                app_data = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
                db_dir = os.path.join(app_data, "UniVision")
                os.makedirs(db_dir, exist_ok=True)
                db_path = os.path.join(db_dir, "desktop_attendance.db")
                if not os.path.exists(db_path):
                    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
                    candidates = [
                        os.path.join(base_dir, "desktop", "app", "storage", "desktop_attendance.db"),
                        os.path.join(base_dir, "app", "storage", "desktop_attendance.db"),
                        os.path.join(base_dir, "desktop_attendance.db"),
                    ]
                    for c in candidates:
                        if os.path.exists(c):
                            try:
                                shutil.copy2(c, db_path)
                                break
                            except Exception:
                                pass
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                db_path = os.path.join(base_dir, "desktop_attendance.db")
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # 1. Enrolled students and their biometric embeddings (Local only!)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS enrolled_students (
                student_id INTEGER PRIMARY KEY,
                roll_no TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                embedding BLOB NOT NULL,
                enrolled_at TEXT NOT NULL
            )
            """)

            # 2. Local sessions
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS local_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                course_code TEXT NOT NULL,
                course_name TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                cloud_session_id INTEGER
            )
            """)

            # 3. Attendance sync queue (Offline-first buffer)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                local_session_id INTEGER NOT NULL,
                cloud_session_id INTEGER,
                student_id INTEGER NOT NULL,
                roll_no TEXT NOT NULL,
                full_name TEXT NOT NULL,
                marked_at TEXT NOT NULL,
                method TEXT DEFAULT 'face',
                confidence REAL,
                synced INTEGER DEFAULT 0,
                synced_at TEXT,
                UNIQUE(local_session_id, student_id)
            )
            """)

            # 4. Desktop Station Users (Admin, Teacher, Student)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                full_name TEXT NOT NULL,
                roll_no TEXT,
                created_at TEXT NOT NULL
            )
            """)
            conn.commit()

            # Seed default admin and teacher if empty
            cursor.execute("SELECT COUNT(*) FROM app_users")
            if cursor.fetchone()[0] == 0:
                now_str = datetime.now(timezone.utc).isoformat()
                admin_hash = self.hash_password("admin123")
                teacher_hash = self.hash_password("teacher123")
                student_hash = self.hash_password("student123")
                cursor.execute("""
                INSERT INTO app_users (username, email, password_hash, role, full_name, roll_no, created_at)
                VALUES 
                ('admin', 'admin@univision.edu', ?, 'admin', 'System Administrator', NULL, ?),
                ('teacher', 'teacher@school.edu', ?, 'teacher', 'Prof. Alan Turing', NULL, ?),
                ('2024-CS-001', 'alice@student.edu', ?, 'student', 'Alice Johnson', '2024-CS-001', ?)
                """, (admin_hash, now_str, teacher_hash, now_str, student_hash, now_str))
                conn.commit()

            # Sync any enrolled students into app_users for instant student login
            cursor.execute("SELECT student_id, roll_no, full_name FROM enrolled_students")
            for sid, rno, fname in cursor.fetchall():
                cursor.execute("SELECT id FROM app_users WHERE LOWER(username) = LOWER(?) OR (roll_no IS NOT NULL AND LOWER(roll_no) = LOWER(?))", (rno, rno))
                if not cursor.fetchone():
                    now_str = datetime.now(timezone.utc).isoformat()
                    st_hash = self.hash_password("student123")
                    clean_roll = rno.lower().replace(" ", "").replace("(", "").replace(")", "").replace("-", "")
                    cursor.execute("""
                    INSERT OR IGNORE INTO app_users (username, email, password_hash, role, full_name, roll_no, created_at)
                    VALUES (?, ?, ?, 'student', ?, ?, ?)
                    """, (rno, f"{clean_roll}@student.edu", st_hash, fname, rno, now_str))
            conn.commit()

    @staticmethod
    def hash_password(password: str) -> str:
        import hashlib
        return hashlib.sha256(f"univision_{password}".encode('utf-8')).hexdigest()

    def verify_user_password(self, plain_password: str, stored_hash: str) -> bool:
        if not stored_hash or not plain_password:
            return False
        if stored_hash == self.hash_password(plain_password):
            return True
        if stored_hash == plain_password:
            return True
        if stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"):
            try:
                import bcrypt
                return bcrypt.checkpw(plain_password.encode('utf-8'), stored_hash.encode('utf-8'))
            except Exception:
                pass
        return False

    def authenticate_user(self, identifier: str, password: str, role: Optional[str] = None) -> Optional[dict]:
        clean_id = (identifier or "").strip()
        clean_pwd = (password or "").strip()
        if not clean_id or not clean_pwd:
            return None

        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Query app_users by username, email, or roll_no
            cursor.execute("""
            SELECT * FROM app_users 
            WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?) OR (roll_no IS NOT NULL AND LOWER(roll_no) = LOWER(?))
            """, (clean_id, clean_id, clean_id))
            user_row = cursor.fetchone()

            # Fallback: Check if student exists in enrolled_students but not yet in app_users
            if not user_row:
                cursor.execute("SELECT * FROM enrolled_students WHERE LOWER(roll_no) = LOWER(?)", (clean_id,))
                enrolled_row = cursor.fetchone()
                if enrolled_row:
                    now_str = datetime.now(timezone.utc).isoformat()
                    st_hash = self.hash_password("student123")
                    rno = enrolled_row["roll_no"]
                    fname = enrolled_row["full_name"]
                    clean_roll = rno.lower().replace(" ", "").replace("(", "").replace(")", "").replace("-", "")
                    cursor.execute("""
                    INSERT OR IGNORE INTO app_users (username, email, password_hash, role, full_name, roll_no, created_at)
                    VALUES (?, ?, ?, 'student', ?, ?, ?)
                    """, (rno, f"{clean_roll}@student.edu", st_hash, fname, rno, now_str))
                    conn.commit()

                    cursor.execute("SELECT * FROM app_users WHERE LOWER(roll_no) = LOWER(?)", (clean_id,))
                    user_row = cursor.fetchone()

            if not user_row:
                return None

            user_dict = dict(user_row)

            # Check password
            pw_ok = self.verify_user_password(clean_pwd, user_dict["password_hash"])
            if not pw_ok and user_dict["role"] == "student" and user_dict["password_hash"] == self.hash_password("student123"):
                if clean_pwd == "student123" or (user_dict.get("roll_no") and clean_pwd.lower() == user_dict["roll_no"].lower()):
                    pw_ok = True

            if not pw_ok:
                return None

            # Check role if required
            if role and user_dict["role"].lower() != role.lower():
                return None

            return {
                "id": user_dict["id"],
                "username": user_dict["username"],
                "email": user_dict["email"],
                "role": user_dict["role"],
                "full_name": user_dict["full_name"],
                "roll_no": user_dict.get("roll_no")
            }

    def list_users(self) -> List[dict]:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, email, role, full_name, roll_no, created_at FROM app_users ORDER BY id ASC")
            return [dict(row) for row in cursor.fetchall()]

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, email, role, full_name, roll_no, created_at FROM app_users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_user(self, username: str, email: str, password: str, role: str, full_name: str, roll_no: Optional[str] = None) -> dict:
        clean_user = username.strip()
        clean_email = email.strip()
        clean_pwd = password.strip()
        clean_role = role.strip().lower()
        clean_name = full_name.strip()
        clean_roll = roll_no.strip() if roll_no else (clean_user if clean_role == 'student' else None)
        
        now_str = datetime.now(timezone.utc).isoformat()
        pwd_hash = self.hash_password(clean_pwd)

        with self._get_conn() as conn:
            cursor = conn.cursor()
            # Check existing username or email
            cursor.execute("SELECT id FROM app_users WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)", (clean_user, clean_email))
            if cursor.fetchone():
                raise ValueError("A user with this username or email already exists")

            cursor.execute("""
            INSERT INTO app_users (username, email, password_hash, role, full_name, roll_no, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (clean_user, clean_email, pwd_hash, clean_role, clean_name, clean_roll, now_str))
            new_id = cursor.lastrowid
            conn.commit()

            return {
                "id": new_id,
                "username": clean_user,
                "email": clean_email,
                "role": clean_role,
                "full_name": clean_name,
                "roll_no": clean_roll,
                "created_at": now_str
            }

    def update_user_password(self, user_id: int, new_password: str) -> bool:
        clean_pwd = new_password.strip()
        if len(clean_pwd) < 4:
            raise ValueError("Password must be at least 4 characters long")

        pwd_hash = self.hash_password(clean_pwd)
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE app_users SET password_hash = ? WHERE id = ?", (pwd_hash, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_user(self, user_id: int, full_name: Optional[str] = None, email: Optional[str] = None, roll_no: Optional[str] = None, username: Optional[str] = None) -> bool:
        updates = []
        params = []
        if full_name is not None and full_name.strip():
            updates.append("full_name = ?")
            params.append(full_name.strip())
        if email is not None and email.strip():
            updates.append("email = ?")
            params.append(email.strip())
        if roll_no is not None and roll_no.strip():
            updates.append("roll_no = ?")
            params.append(roll_no.strip())
        if username is not None and username.strip():
            updates.append("username = ?")
            params.append(username.strip())

        if not updates:
            return False

        params.append(user_id)
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE app_users SET {', '.join(updates)} WHERE id = ?", params)
            if cursor.rowcount > 0:
                conn.commit()
                # If roll_no or full_name changed, cascade to enrolled_students if student
                cursor.execute("SELECT role, roll_no, full_name FROM app_users WHERE id = ?", (user_id,))
                user_info = cursor.fetchone()
                if user_info and user_info[0] == 'student':
                    rno = user_info[1]
                    fname = user_info[2]
                    conn.execute("UPDATE enrolled_students SET full_name = ? WHERE LOWER(roll_no) = LOWER(?)", (fname, rno))
                    conn.execute("UPDATE attendance_queue SET full_name = ? WHERE LOWER(roll_no) = LOWER(?)", (fname, rno))
                    conn.commit()
                return True
            return False

    def delete_user(self, user_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM app_users WHERE id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    # --- Student Biometrics Enrollment ---
    def save_enrolled_student(self, student_id: int, roll_no: str, full_name: str, embedding: np.ndarray):
        raw_bytes = embedding.astype(np.float32).tobytes()
        now_str = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO enrolled_students (student_id, roll_no, full_name, embedding, enrolled_at)
            VALUES (?, ?, ?, ?, ?)
            """, (student_id, roll_no, full_name, raw_bytes, now_str))

            # Automatically provision student login credentials in app_users
            st_hash = self.hash_password("student123")
            clean_roll = roll_no.lower().replace(" ", "").replace("(", "").replace(")", "").replace("-", "")
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM app_users WHERE LOWER(username) = LOWER(?) OR (roll_no IS NOT NULL AND LOWER(roll_no) = LOWER(?))", (roll_no, roll_no))
            existing = cursor.fetchone()
            if existing:
                cursor.execute("""
                UPDATE app_users SET full_name = ?, roll_no = ? WHERE id = ?
                """, (full_name, roll_no, existing[0]))
            else:
                cursor.execute("""
                INSERT OR IGNORE INTO app_users (username, email, password_hash, role, full_name, roll_no, created_at)
                VALUES (?, ?, ?, 'student', ?, ?, ?)
                """, (roll_no, f"{clean_roll}@student.edu", st_hash, full_name, roll_no, now_str))
            conn.commit()

    def get_all_enrolled_embeddings(self) -> Dict[int, np.ndarray]:
        """
        Returns {student_id: numpy_embedding} for in-memory matching.
        """
        result = {}
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT student_id, embedding FROM enrolled_students")
            for sid, raw_bytes in cursor.fetchall():
                arr = np.frombuffer(raw_bytes, dtype=np.float32)
                result[sid] = arr
        return result

    def get_student_details(self, student_id: int) -> Optional[Tuple[str, str]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT roll_no, full_name FROM enrolled_students WHERE student_id = ?", (student_id,))
            row = cursor.fetchone()
            return (row[0], row[1]) if row else None

    def list_enrolled_students(self) -> List[dict]:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT student_id, roll_no, full_name, enrolled_at FROM enrolled_students ORDER BY roll_no")
            return [dict(row) for row in cursor.fetchall()]

    def delete_enrolled_student(self, student_id: int) -> bool:
        """
        Deletes an enrolled student and their biometrics from local database.
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM enrolled_students WHERE student_id = ?", (student_id,))
            conn.commit()
            return cursor.rowcount > 0

    def update_enrolled_student(self, student_id: int, roll_no: Optional[str] = None, full_name: Optional[str] = None) -> bool:
        """
        Updates an enrolled student's roll number and/or full name in local SQLite storage,
        and cascades changes to attendance records.
        """
        updates = []
        params = []
        if roll_no is not None and str(roll_no).strip():
            updates.append("roll_no = ?")
            params.append(str(roll_no).strip())
        if full_name is not None and str(full_name).strip():
            updates.append("full_name = ?")
            params.append(str(full_name).strip())
        if not updates:
            return False
        params.append(student_id)
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE enrolled_students SET {', '.join(updates)} WHERE student_id = ?", params)
            if cursor.rowcount > 0:
                # Also cascade roll_no and full_name updates to attendance_queue
                att_updates = []
                att_params = []
                if roll_no is not None and str(roll_no).strip():
                    att_updates.append("roll_no = ?")
                    att_params.append(str(roll_no).strip())
                if full_name is not None and str(full_name).strip():
                    att_updates.append("full_name = ?")
                    att_params.append(str(full_name).strip())
                att_params.append(student_id)
                conn.execute(f"UPDATE attendance_queue SET {', '.join(att_updates)} WHERE student_id = ?", att_params)

                # Cascade to app_users if student account exists
                cursor.execute("SELECT roll_no FROM enrolled_students WHERE student_id = ?", (student_id,))
                current_rno = cursor.fetchone()
                if current_rno:
                    rno_val = current_rno[0]
                    usr_updates = []
                    usr_params = []
                    if full_name is not None and str(full_name).strip():
                        usr_updates.append("full_name = ?")
                        usr_params.append(str(full_name).strip())
                    if roll_no is not None and str(roll_no).strip():
                        usr_updates.append("roll_no = ?")
                        usr_params.append(str(roll_no).strip())
                        usr_updates.append("username = ?")
                        usr_params.append(str(roll_no).strip())
                    if usr_updates:
                        usr_params.append(rno_val)
                        conn.execute(f"UPDATE app_users SET {', '.join(usr_updates)} WHERE LOWER(roll_no) = LOWER(?) OR LOWER(username) = LOWER(?)", usr_params + [rno_val])

                conn.commit()
                return True
            return False

    # --- Session Management ---
    def create_local_session(self, course_id: int, course_code: str, course_name: str, cloud_session_id: Optional[int] = None) -> int:
        now_str = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO local_sessions (course_id, course_code, course_name, started_at, cloud_session_id)
            VALUES (?, ?, ?, ?, ?)
            """, (course_id, course_code, course_name, now_str, cloud_session_id))
            conn.commit()
            return cursor.lastrowid

    def end_local_session(self, local_session_id: int):
        now_str = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute("UPDATE local_sessions SET ended_at = ? WHERE id = ?", (now_str, local_session_id))
            conn.commit()

    def get_local_session(self, local_session_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM local_sessions WHERE id = ?", (local_session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_local_session_cloud_id(self, local_session_id: int, cloud_session_id: int):
        with self._get_conn() as conn:
            conn.execute("UPDATE local_sessions SET cloud_session_id = ? WHERE id = ?", (cloud_session_id, local_session_id))
            conn.execute("UPDATE attendance_queue SET cloud_session_id = ? WHERE local_session_id = ?", (cloud_session_id, local_session_id))
            conn.commit()

    # --- Attendance Queue (Offline-First) ---
    def queue_attendance(
        self,
        local_session_id: int,
        student_id: int,
        roll_no: str,
        full_name: str,
        method: str = "face",
        confidence: float = 0.9,
        cloud_session_id: Optional[int] = None
    ) -> bool:
        """
        Saves attendance record locally. Returns True if newly added, False if duplicate.
        """
        now_str = datetime.now(timezone.utc).isoformat()
        try:
            with self._get_conn() as conn:
                conn.execute("""
                INSERT INTO attendance_queue 
                (local_session_id, cloud_session_id, student_id, roll_no, full_name, marked_at, method, confidence, synced)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (local_session_id, cloud_session_id, student_id, roll_no, full_name, now_str, method, confidence))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def get_pending_sync_records(self) -> List[dict]:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM attendance_queue WHERE synced = 0")
            return [dict(row) for row in cursor.fetchall()]

    def mark_records_synced(self, queue_ids: List[int]):
        now_str = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.executemany("UPDATE attendance_queue SET synced = 1, synced_at = ? WHERE id = ?",
                               [(now_str, qid) for qid in queue_ids])
            conn.commit()

    def get_session_attendance(self, local_session_id: int) -> List[dict]:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM attendance_queue 
            WHERE local_session_id = ? 
            ORDER BY marked_at DESC
            """, (local_session_id,))
            return [dict(row) for row in cursor.fetchall()]

    def export_session_to_csv(self, local_session_id: int, target_file_path: str):
        import csv
        records = self.get_session_attendance(local_session_id)
        if not records:
            return False
        with open(target_file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["id", "roll_no", "full_name", "marked_at", "method", "confidence", "synced"])
            writer.writeheader()
            for r in records:
                writer.writerow({
                    "id": r["id"],
                    "roll_no": r["roll_no"],
                    "full_name": r["full_name"],
                    "marked_at": r["marked_at"],
                    "method": r["method"],
                    "confidence": f"{r['confidence']:.2f}" if r['confidence'] else "N/A",
                    "synced": "YES" if r["synced"] == 1 else "PENDING"
                })
        return True

    # ponytail: lightweight queries for desktop views and Flutter bridge
    def list_local_sessions(self) -> List[dict]:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM local_sessions ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_all_attendance(self) -> List[dict]:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM attendance_queue ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]

    def update_attendance(self, queue_id: int, method: Optional[str] = None, confidence: Optional[float] = None) -> bool:
        updates = []
        params = []
        if method is not None:
            updates.append("method = ?")
            params.append(method)
        if confidence is not None:
            updates.append("confidence = ?")
            params.append(confidence)
        if not updates:
            return False
        params.append(queue_id)
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE attendance_queue SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
            return cursor.rowcount > 0

    def delete_attendance(self, queue_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM attendance_queue WHERE id = ?", (queue_id,))
            conn.commit()
            return cursor.rowcount > 0

    def export_all_attendance_to_csv(self, target_file_path: str) -> bool:
        import csv
        records = self.get_all_attendance()
        if not records:
            return False
        with open(target_file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["id", "local_session_id", "roll_no", "full_name", "marked_at", "method", "confidence", "synced"])
            writer.writeheader()
            for r in records:
                writer.writerow({
                    "id": r["id"],
                    "local_session_id": r["local_session_id"],
                    "roll_no": r["roll_no"],
                    "full_name": r["full_name"],
                    "marked_at": r["marked_at"],
                    "method": r["method"],
                    "confidence": f"{r['confidence']:.2f}" if r['confidence'] is not None else "N/A",
                    "synced": "YES" if r["synced"] == 1 else "PENDING"
                })
        return True

    def get_attendance_for_student(self, roll_no: Optional[str] = None, student_id: Optional[int] = None) -> List[dict]:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = """
            SELECT q.*, s.course_code, s.course_name, s.started_at as session_started_at
            FROM attendance_queue q
            LEFT JOIN local_sessions s ON q.local_session_id = s.id
            WHERE 1=1
            """
            params = []
            if roll_no:
                query += " AND (q.roll_no = ? OR LOWER(q.roll_no) = LOWER(?))"
                params.extend([roll_no, roll_no])
            elif student_id is not None:
                query += " AND q.student_id = ?"
                params.append(student_id)
            query += " ORDER BY q.marked_at DESC, q.id DESC"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_all_attendance_with_sessions(self) -> List[dict]:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
            SELECT q.*, s.course_code, s.course_name, s.started_at as session_started_at
            FROM attendance_queue q
            LEFT JOIN local_sessions s ON q.local_session_id = s.id
            ORDER BY q.marked_at DESC, q.id DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def export_student_attendance_to_csv(self, roll_no: str, target_file_path: str) -> bool:
        import csv
        records = self.get_attendance_for_student(roll_no=roll_no)
        if not records:
            return False
        with open(target_file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["id", "local_session_id", "course_code", "course_name", "roll_no", "full_name", "marked_at", "method", "confidence", "synced"])
            writer.writeheader()
            for r in records:
                writer.writerow({
                    "id": r["id"],
                    "local_session_id": r["local_session_id"],
                    "course_code": r.get("course_code") or "N/A",
                    "course_name": r.get("course_name") or "N/A",
                    "roll_no": r["roll_no"],
                    "full_name": r["full_name"],
                    "marked_at": r["marked_at"],
                    "method": r["method"],
                    "confidence": f"{r['confidence']:.2f}" if r['confidence'] is not None else "N/A",
                    "synced": "YES" if r["synced"] == 1 else "PENDING"
                })
        return True
