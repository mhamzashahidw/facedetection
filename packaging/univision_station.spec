# -*- mode: python ; coding: utf-8 -*-
import os
import sys

project_root = os.path.abspath(os.path.join(SPECPATH, ".."))
flutter_release_dir = os.path.join(project_root, "desktop_flutter", "build", "windows", "x64", "runner", "Release")

# Recursively collect all Flutter release files into 'flutter_app/' destination
flutter_datas = []
for root, dirs, files in os.walk(flutter_release_dir):
    for f in files:
        full_path = os.path.join(root, f)
        rel_path = os.path.relpath(full_path, flutter_release_dir)
        target_dir = os.path.dirname(os.path.join("flutter_app", rel_path))
        flutter_datas.append((full_path, target_dir))

models_datas = [
    (os.path.join(project_root, "desktop", "models", "face_detection_yunet_2023mar.onnx"), "models"),
    (os.path.join(project_root, "desktop", "models", "face_recognition_sface_2021dec.onnx"), "models"),
    (os.path.join(project_root, "desktop", "app", "storage", "desktop_attendance.db"), "desktop/app/storage"),
]

all_datas = flutter_datas + models_datas

hidden_imports = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "fastapi",
    "fastapi.middleware.cors",
    "fastapi.responses",
    "pydantic",
    "pydantic_core",
    "cv2",
    "numpy",
    "sqlite3",
    "websockets",
    "desktop",
    "desktop.app",
    "desktop.app.bridge_service",
    "desktop.app.storage.local_db",
    "desktop.app.storage.sync_client",
    "desktop.app.controllers.session_controller",
    "desktop.app.controllers.sync_controller",
    "desktop.app.recognition.detector",
    "desktop.app.recognition.embedder",
    "desktop.app.recognition.matcher",
    "desktop.app.recognition.tracker",
    "desktop.app.recognition.liveness",
    "desktop.app.events.event_bus",
]

a = Analysis(
    ['launcher.py'],
    pathex=[project_root, os.path.join(project_root, 'desktop')],
    binaries=[],
    datas=all_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'PySide6', 'torch', 'matplotlib', 'transformers'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

icon_path = os.path.join(project_root, "desktop_flutter", "windows", "runner", "resources", "app_icon.ico")
if not os.path.exists(icon_path):
    icon_path = None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='UniVision_Biometric_Station',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)
