import cv2
import numpy as np
import traceback

print("Testing MediaPipe FaceMesh Initialization...")

try:
    import mediapipe as mp
    
    # Try old API first
    if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'face_mesh'):
        mp_face_mesh = mp.solutions.face_mesh
        face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        print("FaceMesh initialized successfully (old API).")
        
        # Create a dummy image
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        results = face_mesh.process(img)
        print("Processed dummy frame successfully.")
    else:
        print("MediaPipe newer version without solutions API detected.")
        print("Liveness detection features will be disabled, but recognition will work.")
    
except Exception:
    traceback.print_exc()

print("Done.")
