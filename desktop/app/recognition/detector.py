import os
import sys
import cv2
import numpy as np
from typing import List, Tuple, Optional

class YuNetDetector:
    """
    Lightweight, real-time face detector using OpenCV's YuNet ONNX model.
    Runs at 100+ FPS on standard CPU.
    """
    def __init__(self, model_path: Optional[str] = None, conf_threshold: float = 0.6, nms_threshold: float = 0.3):
        if model_path is None:
            if hasattr(sys, '_MEIPASS'):
                base_dir = getattr(sys, '_MEIPASS')
                candidates = [
                    os.path.join(base_dir, "models", "face_detection_yunet_2023mar.onnx"),
                    os.path.join(base_dir, "desktop", "models", "face_detection_yunet_2023mar.onnx"),
                ]
                model_path = next((c for c in candidates if os.path.exists(c)), candidates[0])
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                model_path = os.path.join(base_dir, "models", "face_detection_yunet_2023mar.onnx")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"YuNet ONNX model not found at {model_path}")

        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        self.detector = cv2.FaceDetectorYN.create(
            model=model_path,
            config="",
            input_size=(320, 320),
            score_threshold=self.conf_threshold,
            nms_threshold=self.nms_threshold,
            top_k=5000,
            backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
            target_id=cv2.dnn.DNN_TARGET_CPU
        )

    def detect(self, frame: np.ndarray) -> np.ndarray:
        """
        Detects faces in the given BGR frame.
        Returns array of detected faces with format:
        [x, y, w, h, x_re, y_re, x_le, y_le, x_nt, y_nt, x_rcm, y_rcm, x_lcm, y_lcm, score]
        """
        h, w = frame.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(frame)
        return faces if faces is not None else np.empty((0, 15))
