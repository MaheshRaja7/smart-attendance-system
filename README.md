# Smart Attendance System

A premium Flask-based attendance system using Facial Recognition and Excel for data storage.

## Features
- **Face Recognition**: Automatically identify students and mark attendance.
- **Excel Database**: Stores all records in `data/database.xlsx` for easy access.
- **Dashboard**: 
  - Staff: View all student stats and attendance percentages.
  - Student: View personal attendance history.
- **Premium UI**: Glassmorphism design with Dark Mode aesthetics.

## Installation

1. **Install Dependencies**:
   Ensure you have Python installed.
   ```bash
   pip install -r requirements.txt
   ```
   *Note: This project uses OpenCV's LBPH recognizer, which is easier to install than dlib.*

2. **Run the Application**:
   ```bash
   python app.py
   ```

3. **Usage**:
   - Access the app at `http://127.0.0.1:5000`.
   - **First Time**: Go to Login -> Register as Staff.
   - **Register Students**: Login as Staff, then add students (Upload a clear face photo).
   - **Mark Attendance**: Click "Mark Attendance" on the home page and face the camera.

## Project Structure
- `app.py`: Main application.
- `camera.py`: Face recognition logic.
- `utils.py`: Excel database handling.
- `templates/`: HTML files.
- `static/`: CSS/JS files.
- `data/`: Stores `database.xlsx`, photos, and encodings.
