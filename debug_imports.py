print("Testing Imports...")
try:
    import cv2
    print("cv2 imported successfully")
except Exception as e:
    print(f"Error importing cv2: {e}")

try:
    import mediapipe as mp
    print("mediapipe imported successfully")
except Exception as e:
    print(f"Error importing mediapipe: {e}")

try:
    import tensorflow as tf
    print("tensorflow imported (unexpected if not installed explicitly)")
except Exception as e:
    print(f"tensorflow import result: {e}")
