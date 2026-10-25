import requests
from typing import Optional, List, Dict
from .local_db import LocalStorage

class CloudSyncClient:
    """
    HTTP client responsible for synchronizing local desktop attendance records
    with the central FastAPI backend. Handles token refresh and batch uploads.
    """
    def __init__(self, base_url: str = "http://localhost:8000", local_storage: Optional[LocalStorage] = None):
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = None
        self.local_storage = local_storage or LocalStorage()

    def login_teacher(self, email: str, password: str) -> bool:
        try:
            resp = requests.post(
                f"{self.base_url}/auth/teacher/login",
                json={"email": email, "password": password},
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("access_token")
                return True
            return False
        except Exception:
            return False

    def create_cloud_session(self, course_id: int) -> Optional[int]:
        if not self.token:
            return None
        try:
            resp = requests.post(
                f"{self.base_url}/sessions",
                json={"course_id": course_id},
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=5
            )
            if resp.status_code == 201:
                return resp.json().get("id")
            return None
        except Exception:
            return None

    def end_cloud_session(self, cloud_session_id: int) -> bool:
        if not self.token:
            return False
        try:
            resp = requests.patch(
                f"{self.base_url}/sessions/{cloud_session_id}/end",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=5
            )
            return resp.status_code == 200
        except Exception:
            return False

    def sync_pending_records(self) -> Dict[str, int]:
        """
        Uploads all pending unsynced records to the backend in an idempotent batch.
        Marks uploaded records as synced in local SQLite upon confirmation.
        """
        pending = self.local_storage.get_pending_sync_records()
        if not pending:
            return {"synced": 0, "failed": 0, "pending": 0}

        if not self.token:
            return {"synced": 0, "failed": len(pending), "pending": len(pending), "error": "Not authenticated"}

        # Group by cloud_session_id and resolve offline sessions
        session_groups: Dict[int, List[dict]] = {}
        no_session_ids = []
        resolved_sessions: Dict[int, int] = {}

        for r in pending:
            csid = r.get("cloud_session_id")
            lsid = r.get("local_session_id")
            if not csid and lsid:
                if lsid in resolved_sessions:
                    csid = resolved_sessions[lsid]
                    r["cloud_session_id"] = csid
                else:
                    lsess = self.local_storage.get_local_session(lsid)
                    course_id = lsess.get("course_id", 1) if lsess else 1
                    new_csid = self.create_cloud_session(course_id)
                    if new_csid:
                        self.local_storage.update_local_session_cloud_id(lsid, new_csid)
                        resolved_sessions[lsid] = new_csid
                        csid = new_csid
                        r["cloud_session_id"] = csid

            if csid:
                session_groups.setdefault(csid, []).append(r)
            else:
                no_session_ids.append(r["id"])

        synced_count = 0
        failed_count = len(no_session_ids)

        for cloud_session_id, records in session_groups.items():
            payload = {
                "session_id": cloud_session_id,
                "records": [
                    {
                        "student_id": r["student_id"],
                        "marked_at": r["marked_at"],
                        "method": r["method"],
                        "confidence": r["confidence"]
                    }
                    for r in records
                ]
            }

            try:
                resp = requests.post(
                    f"{self.base_url}/attendance/batch",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=8
                )
                if resp.status_code == 200:
                    q_ids = [r["id"] for r in records]
                    self.local_storage.mark_records_synced(q_ids)
                    synced_count += len(records)
                else:
                    failed_count += len(records)
            except Exception:
                failed_count += len(records)

        return {
            "synced": synced_count,
            "failed": failed_count,
            "pending": len(pending) - synced_count
        }
