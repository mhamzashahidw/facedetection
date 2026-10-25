"""
UniVision Biometric Desktop Station - Unified Single Executable Launcher
Wraps the Flutter Desktop GUI and Python AI/Storage Bridge Service into a single lifecycle.
"""
import os
import sys
import time
import ctypes
import logging
import threading
import subprocess
import urllib.request
import urllib.error

# Ensure stdout/stderr are valid streams even in GUI/noconsole mode
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

def setup_environment():
    if getattr(sys, "frozen", False):
        bundle_dir = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
    else:
        bundle_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if bundle_dir not in sys.path:
        sys.path.insert(0, bundle_dir)

    desktop_dir = os.path.join(bundle_dir, "desktop")
    if os.path.exists(desktop_dir) and desktop_dir not in sys.path:
        sys.path.insert(0, desktop_dir)

    # Prepare AppData storage directory
    app_data = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
    univision_data = os.path.join(app_data, "UniVision")
    os.makedirs(univision_data, exist_ok=True)

    # Setup file logger
    log_file = os.path.join(univision_data, "station.log")
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logging.info("UniVision unified station launcher initialized.")
    return bundle_dir, univision_data

def acquire_single_instance_lock():
    """Ensure only one instance runs at a time to prevent port/camera collisions."""
    mutex_name = "UniVision_Biometric_Station_Mutex_Global"
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, True, mutex_name)
    last_error = kernel32.GetLastError()
    # 183 = ERROR_ALREADY_EXISTS
    if last_error == 183:
        logging.warning("Another instance of UniVision is already running.")
        try:
            ctypes.windll.user32.MessageBoxW(
                0,
                "UniVision Biometric Station is already running in another window.",
                "UniVision Station",
                0x00000040 | 0x00010000  # MB_OK | MB_ICONINFORMATION | MB_SETFOREGROUND
            )
        except Exception:
            pass
        sys.exit(0)
    return mutex

def start_backend_bridge():
    """Starts Uvicorn in a daemon thread serving the FastAPI app on 127.0.0.1:8001."""
    import uvicorn
    from desktop.app.bridge_service import app as fastapi_app

    config = uvicorn.Config(
        app=fastapi_app,
        host="127.0.0.1",
        port=8001,
        log_level="warning",
        access_log=False,
        loop="asyncio"
    )
    server = uvicorn.Server(config)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    return server, server_thread

def wait_for_bridge_ready(timeout_seconds: float = 15.0) -> bool:
    """Polls http://127.0.0.1:8001/api/ping until responsive or timeout."""
    start_time = time.time()
    ping_url = "http://127.0.0.1:8001/api/ping"
    while time.time() - start_time < timeout_seconds:
        try:
            with urllib.request.urlopen(ping_url, timeout=1.0) as resp:
                if resp.status == 200:
                    logging.info("Python AI Bridge responded healthy on port 8001.")
                    return True
        except Exception:
            time.sleep(0.2)
    return False

def find_flutter_executable(bundle_dir: str) -> str:
    """Finds the compiled Flutter desktop executable in bundle or build directory."""
    candidates = [
        os.path.join(bundle_dir, "flutter_app", "desktop_flutter.exe"),
        os.path.join(bundle_dir, "desktop_flutter", "build", "windows", "x64", "runner", "Release", "desktop_flutter.exe"),
        os.path.join(bundle_dir, "build", "windows", "x64", "runner", "Release", "desktop_flutter.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    raise FileNotFoundError(f"Could not find desktop_flutter.exe in: {candidates}")

def main():
    bundle_dir, data_dir = setup_environment()
    mutex = acquire_single_instance_lock()

    try:
        logging.info("Starting Python AI & Storage Bridge service...")
        server, server_thread = start_backend_bridge()
    except Exception as e:
        logging.exception(f"Fatal error starting backend bridge: {e}")
        try:
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Failed to start Python AI Bridge:\n{e}\n\nCheck logs at: %LOCALAPPDATA%\\UniVision\\station.log",
                "UniVision Startup Error",
                0x00000010
            )
        except Exception:
            pass
        sys.exit(1)

    # Wait for the backend to be fully alive before presenting GUI
    is_ready = wait_for_bridge_ready(timeout_seconds=15.0)
    if not is_ready:
        logging.error("AI Bridge service failed to start within timeout.")
        ctypes.windll.user32.MessageBoxW(
            0,
            "UniVision AI Bridge Service failed to initialize on port 8001.\nPlease check logs at %LOCALAPPDATA%\\UniVision\\station.log",
            "UniVision Error",
            0x00000010 | 0x00010000  # MB_ICONERROR
        )
        sys.exit(1)

    flutter_exe = find_flutter_executable(bundle_dir)
    logging.info(f"Launching Flutter Desktop GUI: {flutter_exe}")

    try:
        # Launch Flutter GUI in its directory so it finds flutter_windows.dll and data/
        flutter_dir = os.path.dirname(flutter_exe)
        proc = subprocess.Popen([flutter_exe], cwd=flutter_dir)

        # Wait until user closes the Flutter app window
        proc.wait()
        exit_code = proc.returncode
    except Exception as e:
        logging.exception(f"Error launching or running Flutter GUI: {e}")
        ctypes.windll.user32.MessageBoxW(
            0,
            f"Failed to launch Flutter GUI:\n{e}",
            "UniVision Error",
            0x00000010
        )
        exit_code = 1
    finally:
        logging.info("Flutter GUI closed. Stopping backend bridge...")
        server.should_exit = True
        server_thread.join(timeout=2.0)
        logging.info("Clean shutdown complete.")

    sys.exit(exit_code)

if __name__ == "__main__":
    main()
