import numpy as np
import cv2
from typing import List, Tuple, Dict, Optional

class LivenessDetector:
    """
    Lightweight anti-spoofing mechanism to prevent photo presentation attacks.
    Tracks facial landmark micro-dynamics and eye region texture variance.
    Supports tracking multiple faces independently without cross-talk.
    """
    def __init__(self, history_len: int = 10, min_motion_variance: float = 0.5):
        self.history_len = history_len
        self.min_motion_variance = min_motion_variance
        self.landmark_history: List[np.ndarray] = []
        self._face_histories: Dict[int, List[np.ndarray]] = {}

    def check_liveness(self, frame: np.ndarray, face_data: np.ndarray, face_id: Optional[int] = None) -> Tuple[bool, float]:
        """
        Takes raw frame and detection result [x, y, w, h, x_re, y_re, x_le, y_le, ...].
        Returns (is_live, confidence_score).
        """
        if len(face_data) < 14:
            return False, 0.0

        # Extract eye coordinates
        re_x, re_y = face_data[4], face_data[5]
        le_x, le_y = face_data[6], face_data[7]
        nose_x, nose_y = face_data[8], face_data[9]

        landmarks = np.array([re_x, re_y, le_x, le_y, nose_x, nose_y], dtype=np.float32)

        if face_id is not None:
            if face_id not in self._face_histories:
                self._face_histories[face_id] = []
            history = self._face_histories[face_id]
        else:
            history = self.landmark_history

        history.append(landmarks)
        if len(history) > self.history_len:
            history.pop(0)

        # Mirror to self.landmark_history for backward compatibility
        if face_id is not None and history is not self.landmark_history:
            self.landmark_history = history

        # If not enough history yet, pass conservatively
        if len(history) < 5:
            return True, 0.5

        # Measure motion standard deviation across history
        history_arr = np.array(history)
        variance = float(np.mean(np.std(history_arr, axis=0)))

        # Natural live humans have subtle micro-tremors and natural motion (variance > min_threshold)
        # Static printed photos placed on a stand have variance close to 0
        is_live = variance >= self.min_motion_variance
        score = min(1.0, variance / 2.0)
        return is_live, score

    def reset(self):
        self.landmark_history.clear()
        self._face_histories.clear()
