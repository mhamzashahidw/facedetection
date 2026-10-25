import os
import sys
import cv2
import numpy as np
from typing import Optional

class SFaceEmbedder:
    """
    Lightweight, fast face feature embedder using OpenCV SFace ONNX model.
    Produces 128-dimensional L2-normalized feature vectors.
    """
    def __init__(self, model_path: Optional[str] = None):
        if model_path is None:
            if hasattr(sys, '_MEIPASS'):
                base_dir = getattr(sys, '_MEIPASS')
                candidates = [
                    os.path.join(base_dir, "models", "face_recognition_sface_2021dec.onnx"),
                    os.path.join(base_dir, "desktop", "models", "face_recognition_sface_2021dec.onnx"),
                ]
                model_path = next((c for c in candidates if os.path.exists(c)), candidates[0])
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                model_path = os.path.join(base_dir, "models", "face_recognition_sface_2021dec.onnx")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"SFace ONNX model not found at {model_path}")

        self.recognizer = cv2.FaceRecognizerSF.create(
            model=model_path,
            config="",
            backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
            target_id=cv2.dnn.DNN_TARGET_CPU
        )

    def extract_feature(self, frame: np.ndarray, face_box_landmarks: np.ndarray) -> Optional[np.ndarray]:
        """
        Aligns the face crop using 5 landmarks and extracts a 128-d embedding vector.
        Safely returns None if alignment or feature extraction fails.
        """
        try:
            face_f32 = np.ascontiguousarray(face_box_landmarks, dtype=np.float32)
            aligned_face = self.recognizer.alignCrop(frame, face_f32)
            if aligned_face is None or aligned_face.size == 0:
                return None
            feature = self.recognizer.feature(aligned_face)
            if feature is None:
                return None
            return feature.flatten()
        except Exception:
            return None

    def average_embeddings(self, embeddings_list: list) -> np.ndarray:
        """
        Calculates the centroid/average of 3-5 enrollment embeddings and L2 normalizes it.
        """
        if not embeddings_list:
            raise ValueError("No embeddings provided to average")
        avg = np.mean(embeddings_list, axis=0)
        norm = np.linalg.norm(avg)
        return avg / norm if norm > 0 else avg
