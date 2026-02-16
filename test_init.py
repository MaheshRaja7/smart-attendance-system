import cv2
import time
print("Step 1: Importing modules...")
from camera import load_known_faces, VideoCamera
print("Step 2: Loading known faces...")
try:
    load_known_faces()
    print("Faces loaded.")
except Exception as e:
    print(f"Error loading faces: {e}")

print("Step 3: Initializing Camera...")
try:
    cam = VideoCamera()
    print("Camera initialized.")
    frame = cam.get_frame()
    if frame is None:
        print("Warning: Camera returned empty frame")
    else:
        print("Camera frame captured.")
    del cam
except Exception as e:
    print(f"Error initializing camera: {e}")
