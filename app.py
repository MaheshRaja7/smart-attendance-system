from flask import Flask, render_template, request, redirect, url_for, Response, session, flash, send_from_directory, jsonify
import os
import time
from werkzeug.utils import secure_filename
from camera import VideoCamera, train_face, load_known_faces
from utils import init_db, add_student, add_staff, get_student_by_reg, get_staff_by_email, get_attendance_stats, get_all_students, get_distinct_dates, get_available_months

from datetime import datetime, date
app = Flask(__name__)
app.secret_key = 'super_secret_key_for_demo'

# Configuration
UPLOAD_FOLDER = 'data/photos'
ENCODING_FOLDER = 'data/encodings'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ENCODING_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Initialize DB and Load Faces
print("Initializing Database...")
try:
    init_db()
    print("Database Initialized.")
except Exception as e:
    print(f"CRITICAL ERROR: Failed to initialize database: {e}")

print("Loading Known Faces...")
try:
    load_known_faces()
    print("Faces Loaded.")
except Exception as e:
    print(f"CRITICAL ERROR: Failed to load faces: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_type = request.form.get('user_type')
        # email_or_id can be Email or RegisterNo
        email_or_id = request.form.get('email_or_id').strip()
        password = request.form.get('password').strip()
        
        print(f"Login Attempt: Type={user_type}, ID={email_or_id}") # Debug log

        if user_type == 'staff':
            staff = get_staff_by_email(email_or_id)
            if staff and staff['Password'] == password:
                session['user_type'] = 'staff'
                session['user_id'] = email_or_id
                session['name'] = staff['Name']
                flash("Login Successful!")
                return redirect(url_for('dashboard_staff'))
            else:
                flash("Invalid Staff Credentials")
        
        elif user_type == 'student':
            # Support Email OR RegisterNo lookup
            from utils import get_student_by_identifier
            student = get_student_by_identifier(email_or_id)
            
            # Authentication Rule: Password is ALWAYS RegisterNo for now.
            if student:
                reg_no = str(student['RegisterNo']).strip()
                if password == reg_no:
                    session['user_type'] = 'student'
                    session['user_id'] = reg_no
                    session['name'] = student['Name']
                    flash("Login Successful!")
                    return redirect(url_for('dashboard_student'))
                else:
                    print(f"Failed Password for {email_or_id}. Expected {reg_no}, Got {password}")
                    flash("Invalid Password (Use Register Number)")
            else:
                print(f"Student not found: {email_or_id}")
                flash("Student Not Found")
                
    return render_template('login.html')

@app.route('/register_student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        try:
            # File handling
            if 'photo' not in request.files:
                flash('No photo uploaded')
                return redirect(request.url)
            
            file = request.files['photo']
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)

            reg_no = request.form.get('reg_no')
            filename = secure_filename(f"{reg_no}_{file.filename}")
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # NEW: Create a directory for this student's encodings (Multi-Shot)
            student_enc_dir = os.path.join(ENCODING_FOLDER, reg_no)
            os.makedirs(student_enc_dir, exist_ok=True)
            
            # Save cropped face as initial.jpg
            encoding_path = os.path.join(student_enc_dir, "initial.jpg")
            
            file.save(photo_path)
            
            # Train face
            if train_face(photo_path, encoding_path):
                data = {
                    'RegisterNo': reg_no,
                    'Name': request.form.get('name'),
                    'Dept': request.form.get('dept'),
                    'Year': request.form.get('year'),
                    'Email': request.form.get('email'),
                    'Contact': request.form.get('contact'),
                    'PhotoPath': photo_path,
                    'EncodingPath': encoding_path # Points to the specific file, but camera.py will scan the dir
                }
                if add_student(data):
                    load_known_faces() # Reload faces
                    flash("Student Registered Successfully!")
                    return redirect(url_for('login'))
                else:
                    flash("Error adding to database")
            else:
                flash("Could not detect face in photo. Please try another.")
                os.remove(photo_path) # Cleanup
                
        except Exception as e:
            print(e)
            flash(f"Error: {e}")
            
    return render_template('register_student.html')

@app.route('/add_face_variant', methods=['POST'])
def add_face_variant():
    if 'user_id' not in session or session.get('user_type') != 'student':
        flash("Unauthorized")
        return redirect(url_for('login'))
        
    reg_no = session['user_id']
    
    if 'photo' not in request.files:
        flash('No photo uploaded')
        return redirect(url_for('dashboard_student'))
    
    file = request.files['photo']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('dashboard_student'))
        
    try:
        # Save temp original
        temp_filename = secure_filename(f"variant_{reg_no}_{int(time.time())}.jpg")
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
        file.save(temp_path)
        
        # Determine strict Student Encoding Dir
        student_enc_dir = os.path.join(ENCODING_FOLDER, reg_no)
        os.makedirs(student_enc_dir, exist_ok=True)
        
        # Save new variant with timestamp
        variant_name = f"variant_{int(time.time())}.jpg"
        variant_path = os.path.join(student_enc_dir, variant_name)
        
        if train_face(temp_path, variant_path):
            load_known_faces()
            flash("New face appearance added successfully!")
        else:
            flash("Could not detect face. Please try a clear photo.")
            
        # Cleanup temp
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
    except Exception as e:
        print(f"Error adding variant: {e}")
        flash(f"Error: {e}")
        
    return redirect(url_for('dashboard_student'))

@app.route('/register_staff', methods=['GET', 'POST'])
def register_staff():
    if request.method == 'POST':
        data = {
            'Name': request.form.get('name'),
            'Dept': request.form.get('dept'),
            'Email': request.form.get('email'),
            'Contact': request.form.get('contact'),
            'Password': request.form.get('password')
        }
        if add_staff(data):
            flash("Staff Registered Successfully!")
            return redirect(url_for('login'))
        else:
            flash("Error registering staff (Email might exist)")
            
    return render_template('register_staff.html')

@app.route('/dashboard_student')
def dashboard_student():
    if 'user_id' not in session or session.get('user_type') != 'student':
        return redirect(url_for('login'))
        
    from utils import get_student_summary
    
    # Get filters
    selected_month = request.args.get('month')
    selected_status = request.args.get('status')
    
    summary = get_student_summary(session['user_id'], selected_month, selected_status)
    available_months = get_available_months()
    
    if not summary:
        flash("Error loading student data")
        return redirect(url_for('login'))
    
    return render_template('dashboard_student.html', 
                           info=summary['info'], 
                           stats=summary['statistics'], 
                           history=summary['history'],
                           available_months=available_months,
                           selected_month=selected_month,
                           selected_status=selected_status)

@app.route('/dashboard_staff')
def dashboard_staff():
    if 'user_id' not in session or session.get('user_type') != 'staff':
        return redirect(url_for('login'))
        
    # Get all attendance records (or filter by date/dept if needed)
    # For now, let's just show all students and their summary
    students = get_all_students()
    all_dates = get_distinct_dates()
    total_working_days = len(all_dates)
    
    summary_data = []
    
    for s in students:
        s_stats = get_attendance_stats('student', s['RegisterNo'])
        # Count days present (unique dates in stats)
        present_days = {x['Date'] for x in s_stats if x['Status'] == 'Present'}
        od_days = {x['Date'] for x in s_stats if x['Status'] == 'OD'}
        present = len(present_days)
        od = len(od_days)
        
        # Calculate percentage based on TOTAL working days
        total_present = present + od
        percentage = (total_present / total_working_days * 100) if total_working_days > 0 else 0
        
        summary_data.append({
            'Name': s['Name'],
            'RegisterNo': s['RegisterNo'],
            'Dept': s['Dept'],
            'Year': s['Year'],
            'Total': total_working_days,
            'Present': present,
            'OD': od,
            'Absent': total_working_days - total_present,
            'Percentage': round(percentage, 2)
        })
        
    return render_template('dashboard_staff.html', students=summary_data)

@app.route('/student_details/<reg_no>')
def student_details(reg_no):
    if 'user_id' not in session or session.get('user_type') != 'staff':
        return redirect(url_for('login'))
        
    from utils import get_student_summary
    
    selected_month = request.args.get('month')
    selected_status = request.args.get('status')
    
    summary = get_student_summary(reg_no, selected_month, selected_status)
    available_months = get_available_months()
    
    if not summary:
        flash("Student not found")
        return redirect(url_for('dashboard_staff'))
        
    # Reuse student dashboard template or create a new one 'student_details.html'
    # reusing dashboard_student.html might be tricky if it assumes session user, 
    # but we passed 'info' explicitly. Let's send a flag 'is_staff_view'.
    return render_template('dashboard_student.html', 
                           info=summary['info'], 
                           stats=summary['statistics'], 
                           history=summary['history'],
                           is_staff_view=True,
                           available_months=available_months,
                           selected_month=selected_month,
                           selected_status=selected_status)

@app.route('/api/student_attendance/<reg_no>')
def get_student_attendance_api(reg_no):
    if 'user_id' not in session or session.get('user_type') != 'staff':
        return jsonify({'error': 'Unauthorized'}), 403
    
    stats = get_attendance_stats('student', reg_no)
    all_dates = get_distinct_dates()
    
    # Create Map of Date -> Record
    attendance_map = {s['Date']: s for s in stats}
    
    final_stats = []
    for day in all_dates:
        if day in attendance_map:
            item = attendance_map[day].copy()
        else:
            item = {
                'Date': day,
                'Morning_IN': '-',
                'Evening_OUT': '-',
                'Status': 'Absent'
            }
        
        # Serialization
        if isinstance(item.get('Date'), (date, datetime)):
            item['Date'] = item['Date'].strftime('%Y-%m-%d')
            
        for time_col in ['Morning_IN', 'Evening_OUT']:
             val = item.get(time_col)
             if val and val != '-':
                 item[time_col] = str(val)
                 
        final_stats.append(item)
        
    return jsonify(final_stats)

def gen(camera):
    try:
        while True:
            frame = camera.get_frame()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
            else:
                break
    except Exception as e:
        print(f"Camera Stream Error: {e}")
    finally:
        # Check if camera has a release method and call it
        # This ensures the hardware light turns off IMMEDIATELY when the client stops requesting frames.
        if hasattr(camera, 'video'):
             camera.video.release()
        print("Camera Released.")

@app.route('/video_feed')
def video_feed():
    return Response(gen(VideoCamera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/attendance')
def attendance():
    return render_template('attendance.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
