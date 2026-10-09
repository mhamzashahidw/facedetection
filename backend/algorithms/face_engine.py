import numpy as np
import cv2
import base64
from deepface import DeepFace

class FaceRecognitionEngine:
    def __init__(self, model_name="Facenet", detector_backend="opencv"):
        self.model_name = model_name
        self.detector_backend = detector_backend

    def decode_base64_image(self, base64_str: str) -> np.ndarray:
        # Assumes format "data:image/jpeg;base64,....."
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
        
        img_data = base64.b64decode(base64_str)
        np_arr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return img

    def get_embedding(self, img_path_or_array) -> list:
        try:
            # Generate embeddings
            embedding_objs = DeepFace.represent(
                img_path=img_path_or_array, 
                model_name=self.model_name, 
                detector_backend=self.detector_backend,
                enforce_detection=True
            )
            if len(embedding_objs) == 0:
                raise ValueError("No face detected")
            if len(embedding_objs) > 1:
                raise ValueError("Multiple faces detected")
                
            return embedding_objs[0]["embedding"]
        except Exception as e:
            raise ValueError(f"Face processing error: {str(e)}")

    def calculate_similarity(self, embedding1, embedding2):
        # Cosine similarity
        a = np.array(embedding1)
        b = np.array(embedding2)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

face_engine = FaceRecognitionEngine()
