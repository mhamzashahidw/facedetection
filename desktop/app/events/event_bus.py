try:
    from PySide6.QtCore import QObject, Signal
except ImportError:
    class Signal:
        """Pure-Python Signal implementation matching Qt Signal semantics."""
        def __init__(self, *arg_types):
            self._slots = []

        def connect(self, slot):
            if slot not in self._slots:
                self._slots.append(slot)

        def disconnect(self, slot=None):
            if slot is None:
                self._slots.clear()
            elif slot in self._slots:
                self._slots.remove(slot)

        def emit(self, *args, **kwargs):
            for slot in list(self._slots):
                try:
                    slot(*args, **kwargs)
                except Exception as e:
                    import logging
                    logging.getLogger("EventBus").exception(f"Error in signal slot: {e}")

    class QObject:
        pass


class DesktopEventBus(QObject):
    """
    Decoupled Event Bus for the Edge Windows Desktop Application.
    Uses Qt Signals to provide thread-safe asynchronous messaging between
    background workers (CameraWorker), domain controllers, and UI views.
    """
    # Camera & AI Telemetry Events
    frame_processed = Signal(object, list, float) # (display_frame, faces, fps)
    student_recognized = Signal(int, float) # (student_id, similarity)
    
    # Domain Biometric Confirmation
    attendance_confirmed = Signal(int, str, str, float) # (student_id, roll_no, name, confidence)
    record_queued = Signal(dict) # (record_dict with roll, name, time)
    
    # Session Lifecycle Events
    session_started = Signal(int, str, str) # (local_session_id, course_code, course_name)
    session_ended = Signal(int) # (local_session_id)
    
    # Cloud Synchronization Events
    sync_status_changed = Signal(str, dict) # (status_message, stats_dict)

# Global singleton event bus instance
desktop_event_bus = DesktopEventBus()
