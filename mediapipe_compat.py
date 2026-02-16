"""
Compatibility wrapper for MediaPipe 0.10+ to work with code written for 0.8.x API
"""
import mediapipe as mp_new
import mediapipe.tasks.vision as vision
from mediapipe.tasks import BaseOptions

class FaceMeshCompat:
    """Adapter for MediaPipe 0.10+ FaceMesh using the old 0.8.x API"""
    
    def __init__(self, max_num_faces=1, refine_landmarks=True, 
                 min_detection_confidence=0.5, min_tracking_confidence=0.5):
        """Initialize FaceMesh with new API, compatible with old usage"""
        self.options = vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=None),
            num_faces=max_num_faces,
            min_face_detection_confidence=min_detection_confidence,
            min_face_presence_confidence=min_tracking_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.detector = vision.FaceLandmarker.create_from_options(self.options)
    
    def process(self, image):
        """Process image and return compatible results"""
        # Convert from OpenCV BGR/numpy to MediaPipe Image format
        import cv2
        from mediapipe import Image, ImageFormat
        
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Create MediaPipe Image
        mp_image = Image(image_format=ImageFormat.SRGB, data=rgb_image)
        
        # Detect face landmarks
        detection_result = self.detector.detect(mp_image)
        
        # Wrap result to match old API
        return LandmarkResultCompat(detection_result)


class LandmarkResultCompat:
    """Wrapper for detection results to match old API"""
    
    def __init__(self, detection_result):
        self.detection_result = detection_result
        self.multi_face_landmarks = []
        
        # Convert new format to old format
        if detection_result.face_landmarks:
            self.multi_face_landmarks = [
                FaceLandmarksCompat(landmarks) 
                for landmarks in detection_result.face_landmarks
            ]
    
    # Single face access for backward compatibility
    @property
    def face_landmarks(self):
        return self.multi_face_landmarks[0] if self.multi_face_landmarks else None


class FaceLandmarksCompat:
    """Wrapper for individual face landmarks"""
    
    def __init__(self, landmark_list):
        self.landmark = landmark_list


class Solutions:
    """Wrapper for the old 'solutions' API"""
    
    class FaceMesh:
        @staticmethod
        def FaceMesh(**kwargs):
            return FaceMeshCompat(**kwargs)


# Create module-level attribute for backward compatibility
original_mp = mp_new
Solutions = Solutions()


def patch_mediapipe():
    """Patch the global mediapipe module with backward compatibility"""
    import sys
    import mediapipe
    
    # Add solutions to mediapipe
    mediapipe.solutions = Solutions()
    mediapipe.solutions.face_mesh = lambda: FaceMeshCompat
    
    # Create class version for constructor style
    class FaceMeshClass:
        def __init__(self, **kwargs):
            return FaceMeshCompat(**kwargs)
        
    mediapipe.solutions.face_mesh.FaceMesh = FaceMeshClass
    
    return mediapipe


if __name__ == "__main__":
    # Test the compatibility wrapper
    patch_mediapipe()
    import mediapipe as mp
    
    print("MediaPipe compatibility wrapper loaded successfully")
    print(f"mp.solutions: {hasattr(mp, 'solutions')}")
    print(f"mp.solutions.face_mesh: {hasattr(mp.solutions, 'face_mesh')}")
