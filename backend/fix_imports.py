import os

backend_dir = r"C:\Users\User\.gemini\antigravity-ide\scratch\FaceAttend-AI\backend"

fixes = {
    "main.py": [
        ("from .database.connection", "from database.connection"),
        ("from .events.event_bus", "from events.event_bus"),
        ("from .controllers import", "from controllers import"),
        ("from .events.handlers", "from events.handlers"),
    ],
    "models\\models.py": [
        ("from ..database.connection", "from database.connection"),
    ],
    "utils\\dependencies.py": [
        ("from ..database.connection", "from database.connection"),
        ("from ..models.models", "from models.models"),
        ("from .security", "from utils.security"),
    ],
    "controllers\\auth.py": [
        ("from ..database.connection", "from database.connection"),
        ("from ..models.models", "from models.models"),
        ("from ..schemas.user", "from schemas.user"),
        ("from ..utils.security", "from utils.security"),
        ("from ..events.event_bus", "from events.event_bus"),
        ("from ..utils.dependencies", "from utils.dependencies"),
    ],
    "controllers\\students.py": [
        ("from ..database.connection", "from database.connection"),
        ("from ..models.models", "from models.models"),
        ("from ..schemas.student", "from schemas.student"),
        ("from ..utils.dependencies", "from utils.dependencies"),
        ("from ..events.event_bus", "from events.event_bus"),
    ],
    "controllers\\face.py": [
        ("from ..database.connection", "from database.connection"),
        ("from ..models.models", "from models.models"),
        ("from ..schemas.face", "from schemas.face"),
        ("from ..algorithms.face_engine", "from algorithms.face_engine"),
        ("from ..events.event_bus", "from events.event_bus"),
        ("from ..utils.dependencies", "from utils.dependencies"),
    ],
    "controllers\\attendance.py": [
        ("from ..database.connection", "from database.connection"),
        ("from ..models.models", "from models.models"),
        ("from ..schemas.attendance", "from schemas.attendance"),
        ("from ..events.event_bus", "from events.event_bus"),
        ("from ..utils.dependencies", "from utils.dependencies"),
    ],
    "events\\handlers\\attendance_handler.py": [
        ("from ..event_bus", "from events.event_bus"),
        ("from ...database.connection", "from database.connection"),
        ("from ...models.models", "from models.models"),
    ],
    "events\\handlers\\audit_handler.py": [
        ("from ..event_bus", "from events.event_bus"),
        ("from ...database.connection", "from database.connection"),
        ("from ...models.models", "from models.models"),
    ],
}

for rel_path, replacements in fixes.items():
    full_path = os.path.join(backend_dir, rel_path)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        for old, new in replacements:
            content = content.replace(old, new)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {rel_path}")
    else:
        print(f"Not found: {full_path}")
