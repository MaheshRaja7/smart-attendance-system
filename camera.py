import cv2
import numpy as np
import os
import time

# Force CPU to avoid CUDA DLL errors
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

from utils import mark_attendance, get_student_by_reg, get_all_students
from camera_config import CAMERA_SOURCE

# --- Liveness & Recognition Config ---
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
recognizer = cv2.face.LBPHFaceRecognizer_create()

# MediaPipe for Blink & Head Pose
use_liveness = False
face_mesh = None
mp = None # Global placeholder

try:
    import mediapipe as mp
    
    # Try new MediaPipe 0.10+ API first
    if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'face_mesh'):
        mp_face_mesh = mp.solutions.face_mesh
        face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=5,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        use_liveness = True
        print("Liveness Detection (MediaPipe) Initialized.")
    else:
        # Fallback for older/newer versions without solutions
        print("WARNING: MediaPipe solutions API not available, using placeholder detection.")
        use_liveness = False
        
except Exception as e:
    print(f"WARNING: Liveness Detection failed to initialize: {e}")
    print("Proceeding without Liveness Detection.")
    use_liveness = False

# Constants
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]
EAR_THRESHOLD = 0.25 # Slightly looser to ensure detection
CONSEC_FRAMES = 1

# Head Pose Thresholds
# We use nose tip (1) vs side of face or simply 3D rotation logic if available, 
# but simple geometry is usually enough for "Turn Left/Right".
# Using nose tip (1) and chin (152) and ear connections isn't always easy 
# without PnP. 
# SIMPLER APPROACH: Compare Nose x-position relative to face center.
LEFT_HEAD_TURN_THRESHOLD = -10 # Degrees (approx)
RIGHT_HEAD_TURN_THRESHOLD = 10 # Degrees (approx)

# Liveness Stages
STAGE_WAITING_BLINK = 0
STAGE_WAITING_HEAD_TURN = 1
STAGE_VERIFIED = 2

# State Machine
# Map: reg_no -> {'stage': 0, 'blink_detected': False, 'marked': False, 'last_seen': time, 'status_msg': ''}
liveness_states = {}

def calculate_ear(landmarks, indices, w, h):
    # Euclidean distance helper
    def dist(i1, i2):
        p1 = np.array([landmarks[i1].x * w, landmarks[i1].y * h])
        p2 = np.array([landmarks[i2].x * w, landmarks[i2].y * h])
        return np.linalg.norm(p1 - p2)

    A = dist(indices[1], indices[5])
    B = dist(indices[2], indices[4])
    C = dist(indices[0], indices[3])

    if C == 0: return 0
    return (A + B) / (2.0 * C)

def get_head_pose(landmarks, w, h):
    # Simple estimation using nose tip (1) and average of ears or face sides (234, 454)
    # 1: Nose tip, 234: Left ear/cheek, 454: Right ear/cheek
    
    nose = landmarks[1]
    left_side = landmarks[234]
    right_side = landmarks[454]
    
    # Calculate horizontal ratio
    # If looking straight, dist(nose, left) ~= dist(nose, right)
    # Ratio = dist(nose, left) / dist(left, right)
    
    nose_x = nose.x * w
    left_x = left_side.x * w
    right_x = right_side.x * w
    
    total_width = right_x - left_x
    if total_width == 0: return 0
    
    # 0.5 is center. < 0.4 is looking left (from camera view), > 0.6 is looking right.
    ratio = (nose_x - left_x) / total_width
    
    # Normalize to -1 to 1 roughly, where 0 is center
    # strict 0.5 -> 0
    # 0.2 -> -0.3 (-30%)
    turn_val = (ratio - 0.5) * 2 
    return turn_val # -1 (Left) to +1 (Right)

def load_known_faces():
    global is_trained, known_face_names
    print("Loading known faces...")
    faces, ids = [], []
    known_face_names = {}
    
    try:
        students = get_all_students()
        current_id = 0
        BASE_ENCODING_DIR = 'data/encodings' 
        
        for student in students:
            reg_no = str(student['RegisterNo'])
            current_id += 1 
            known_face_names[current_id] = reg_no
            
            student_dir = os.path.join(BASE_ENCODING_DIR, reg_no)
            loaded_count = 0
            
            if os.path.exists(student_dir) and os.path.isdir(student_dir):
                for file_name in os.listdir(student_dir):
                    if file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                        img_path = os.path.join(student_dir, file_name)
                        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                        if img is not None:
                            faces.append(cv2.resize(img, (200, 200)))
                            ids.append(current_id)
                            loaded_count += 1
            
            if loaded_count == 0:
                photo_path = student['EncodingPath']
                if photo_path and os.path.exists(photo_path):
                    img = cv2.imread(photo_path, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        faces.append(cv2.resize(img, (200, 200)))
                        ids.append(current_id)
                        loaded_count += 1
                        
        if len(faces) > 0:
            recognizer.train(faces, np.array(ids))
            is_trained = True
            print(f"Trained on {len(faces)} faces from {len(students)} students.")
        else:
            is_trained = False
            print("No faces found to train.")
            
    except Exception as e:
        print(f"Error loading faces: {e}")

def train_face(image_path, save_path):
    try:
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        if len(faces) == 0: return False
        
        faces = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)
        (x, y, w, h) = faces[0]
        face_img = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
        cv2.imwrite(save_path, face_img)
        return True
    except:
        return False

class VideoCamera(object):
    def __init__(self):
        self.video = cv2.VideoCapture(CAMERA_SOURCE)
    
    def __del__(self):
        self.video.release()
    
    def get_frame(self):
        success, frame = self.video.read()
        if not success: return None
        
        # Mirror for better UX
        frame = cv2.flip(frame, 1)
        
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 1. Detect Faces for Recognition
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        # 2. MediaPipe Mesh for Liveness
        keypoints = None
        if use_liveness and face_mesh:
            try:
                keypoints = face_mesh.process(rgb_frame)
            except Exception as e:
                pass 
        
        # Process Detected Faces
        for (x, y, wa, ha) in faces:
            cv2.rectangle(frame, (x, y), (x+wa, y+ha), (0, 255, 0), 2)
            
            name = "Unknown"
            status_msg = "Look at camera"
            color = (0, 255, 255) # Yellow
            
            if is_trained:
                roi = cv2.resize(gray[y:y+ha, x:x+wa], (200, 200))
                id_, conf = recognizer.predict(roi)
                
                # Confidence Check
                if conf < 65 and id_ in known_face_names:
                    reg_no = known_face_names[id_]
                    full_name = get_student_by_reg(reg_no)['Name']
                    name = full_name
                    
                    # --- LIVENESS LOGIC ---
                    if reg_no not in liveness_states:
                        liveness_states[reg_no] = {
                            'stage': STAGE_WAITING_BLINK, 
                            'marked': False,
                            'blink_time': 0
                        }
                    
                    state = liveness_states[reg_no]
                    
                    if state['marked']:
                        status_msg = "Attendance Marked"
                        color = (0, 255, 0) # Green
                    elif use_liveness:
                        if keypoints and keypoints.multi_face_landmarks:
                            # Use first detection for simplicity
                            lm = keypoints.multi_face_landmarks[0].landmark
                            
                            # 1. Blink Check
                            if state['stage'] == STAGE_WAITING_BLINK:
                                ear = (calculate_ear(lm, LEFT_EYE, w, h) + calculate_ear(lm, RIGHT_EYE, w, h)) / 2
                                if ear < EAR_THRESHOLD:
                                    # Eyes closed
                                    state['blink_time'] = time.time()
                                else:
                                    # Eyes open
                                    if state['blink_time'] > 0 and (time.time() - state['blink_time'] < 1.0):
                                        # Just opened after closing -> Valid Blink
                                        state['stage'] = STAGE_WAITING_HEAD_TURN
                                        state['blink_time'] = 0 
                                    else:
                                        state['blink_time'] = 0
                                        
                                status_msg = "Please BLINK eyes"
                                color = (0, 165, 255) # Orange
                                
                            # 2. Head Turn Check
                            elif state['stage'] == STAGE_WAITING_HEAD_TURN:
                                head_turn = get_head_pose(lm, w, h)
                                # Threshold: +/- 0.3 (approx 30% turn)
                                if abs(head_turn) > 0.3:
                                    state['stage'] = STAGE_VERIFIED
                                else:
                                    status_msg = "Turn Head Left/Right"
                                    color = (0, 200, 255) # Yellow-Orange
                                    
                            # 3. Verified
                            elif state['stage'] == STAGE_VERIFIED:
                                mark_attendance(reg_no, full_name, "Dept", "Year") 
                                state['marked'] = True
                                status_msg = "VERIFIED! Marked."
                                color = (0, 255, 0)
                        else:
                            status_msg = "Face not clear"
                    else:
                        # No Liveness -> Auto Mark (Fallback)
                        mark_attendance(reg_no, full_name, "Dept", "Year")
                        state['marked'] = True
                        status_msg = "Marked (No Liveness)"
                        color = (0, 255, 0)

                else:
                    name = "Unknown"
                    status_msg = "Face not recognized"
                    color = (0, 0, 255) 
            
            cv2.putText(frame, name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.putText(frame, status_msg, (x, y+ha+25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)


        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()

