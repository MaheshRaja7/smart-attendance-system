import mysql.connector
from datetime import datetime, date
import os

# --- Database Configuration ---
# CHANGE THESE IF YOUR MYSQL CONFIGURATION IS DIFFERENT
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 's1a2m7s4@M', # Default XAMPP password is often empty. Change if yours is different.
    'database': 'smart_attendance_db'
}

def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        # First connect without database to ensure it exists
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        conn.close()

        # Now connect to the specific database
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

def init_db():
    """Initialize the MySQL database and create tables if they don't exist."""
    conn = get_db_connection()
    if conn is None:
        print("Failed to initialize database. Check your connection settings.")
        return

    cursor = conn.cursor()

    # Create Students Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        RegisterNo VARCHAR(50) PRIMARY KEY,
        Name VARCHAR(100),
        Dept VARCHAR(50),
        Year VARCHAR(20),
        Email VARCHAR(100),
        Contact VARCHAR(20),
        PhotoPath VARCHAR(255),
        EncodingPath VARCHAR(255)
    )
    """)

    # Create Staff Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS staff (
        Email VARCHAR(100) PRIMARY KEY,
        Name VARCHAR(100),
        Dept VARCHAR(50),
        Contact VARCHAR(20),
        Password VARCHAR(255)
    )
    """)

    # Create Attendance Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INT AUTO_INCREMENT PRIMARY KEY,
        RegisterNo VARCHAR(50),
        Name VARCHAR(100),
        Date DATE,
        Morning_IN TIME,
        Evening_OUT TIME,
        Dept VARCHAR(50),
        Year VARCHAR(20),
        Status VARCHAR(20),
        FOREIGN KEY (RegisterNo) REFERENCES students(RegisterNo)
    )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("Database initialized and tables checked.")

def get_all_students():
    init_db()
    conn = get_db_connection()
    if not conn: return []
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM students")
        return cursor.fetchall()
    except Exception as e:
        print(f"Error reading students: {e}")
        return []
    finally:
        conn.close()

def get_student_by_reg(reg_no):
    conn = get_db_connection()
    if not conn: return None
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM students WHERE RegisterNo = %s", (reg_no,))
        return cursor.fetchone()
    except Exception as e:
        print(f"Error fetching student: {e}")
        return None
    finally:
        conn.close()

def get_staff_by_email(email):
    init_db()
    conn = get_db_connection()
    if not conn: return None
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM staff WHERE Email = %s", (email,))
        return cursor.fetchone()
    except Exception as e:
        print(f"Error fetching staff: {e}")
        return None
    finally:
        conn.close()

def add_student(data):
    init_db()
    conn = get_db_connection()
    if not conn: return False
    
    cursor = conn.cursor()
    try:
        sql = """INSERT INTO students (RegisterNo, Name, Dept, Year, Email, Contact, PhotoPath, EncodingPath)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        val = (data['RegisterNo'], data['Name'], data['Dept'], data['Year'], data['Email'], 
               data['Contact'], data['PhotoPath'], data['EncodingPath'])
        cursor.execute(sql, val)
        conn.commit()
        return True
    except mysql.connector.Error as err:
        print(f"Error adding student: {err}")
        return False
    finally:
        conn.close()

def add_staff(data):
    init_db()
    conn = get_db_connection()
    if not conn: return False
    
    cursor = conn.cursor()
    try:
        # Check if email exists
        cursor.execute("SELECT Email FROM staff WHERE Email = %s", (data['Email'],))
        if cursor.fetchone():
            return False # Email exists
            
        sql = """INSERT INTO staff (Name, Dept, Email, Contact, Password)
                 VALUES (%s, %s, %s, %s, %s)"""
        val = (data['Name'], data['Dept'], data['Email'], data['Contact'], data['Password'])
        cursor.execute(sql, val)
        conn.commit()
        return True
    except mysql.connector.Error as err:
        print(f"Error adding staff: {err}")
        return False
    finally:
        conn.close()

def mark_attendance(reg_no, name, dept, year):
    init_db()
    conn = get_db_connection()
    if not conn: return "Database Error"
    
    today = date.today().strftime('%Y-%m-%d')
    now = datetime.now().strftime('%H:%M:%S')
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Check if record exists for today
        cursor.execute("SELECT * FROM attendance WHERE RegisterNo = %s AND Date = %s", (reg_no, today))
        record = cursor.fetchone()
        
        msg = ""
        if not record:
            # New entry for today (Morning IN)
            sql = """INSERT INTO attendance (RegisterNo, Name, Date, Morning_IN, Dept, Year, Status)
                     VALUES (%s, %s, %s, %s, %s, %s, 'Present')"""
            val = (reg_no, name, today, now, dept, year)
            cursor.execute(sql, val)
            conn.commit()
            msg = f"Morning Attendance Marked for {name} at {now}"
        else:
            # Update Evening OUT
            if record['Evening_OUT']:
                 msg = f"Attendance already complete for {name} today."
            else:
                # Update Evening OUT
                sql = "UPDATE attendance SET Evening_OUT = %s WHERE id = %s"
                cursor.execute(sql, (now, record['id']))
                conn.commit()
                msg = f"Evening Attendance Marked for {name} at {now}"
                
        return msg
    except mysql.connector.Error as err:
        print(f"Error marking attendance: {err}")
        return f"Error: {err}"
    finally:
        conn.close()

def get_attendance_stats(user_type, identifier=None):
    init_db()
    conn = get_db_connection()
    if not conn: return []
    
    cursor = conn.cursor(dictionary=True)
    try:
        if user_type == 'student':
            sql = "SELECT * FROM attendance WHERE RegisterNo = %s ORDER BY Date DESC"
            cursor.execute(sql, (identifier,))
        else:
            # For staff or general view
            sql = "SELECT * FROM attendance ORDER BY Date DESC"
            cursor.execute(sql)
            
        return cursor.fetchall()
    except Exception as e:
        print(f"Error getting stats: {e}")
        return []
    finally:
        conn.close()


def get_student_by_identifier(identifier):
    """
    Search student by RegisterNo OR Email.
    Returns the student dict or None.
    """
    conn = get_db_connection()
    if not conn: return None
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Check RegisterNo first
        cursor.execute("SELECT * FROM students WHERE RegisterNo = %s", (identifier,))
        student = cursor.fetchone()
        if student: return student
        
        # Check Email
        cursor.execute("SELECT * FROM students WHERE Email = %s", (identifier,))
        student = cursor.fetchone()
        return student
    except Exception as e:
        print(f"Error fetching student by identifier: {e}")
        return None
    finally:
        conn.close()

def get_student_summary(reg_no, month_filter=None, status_filter=None):
    """
    Returns a detailed summary for a student:
    - Profile info
    - Attendance stats (Present, OD, Absent counts) - Affected by month_filter
    - Detailed history map - Affected by month_filter AND status_filter
    """
    student = get_student_by_reg(reg_no)
    if not student: return None
    
    # Add PhotoFilename for template
    if student.get('PhotoPath'):
        student['PhotoFilename'] = os.path.basename(student['PhotoPath'])
    
    # Get all working days (distinct dates from attendance table)
    working_days = get_distinct_dates() 
    
    # --- Filter Working Days by Month ---
    if month_filter:
        # month_filter expected as 'YYYY-MM'
        filtered_days = []
        for d in working_days:
            d_str = d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)
            if d_str.startswith(month_filter):
                filtered_days.append(d)
        working_days = filtered_days
        
    total_working_days = len(working_days)
    
    # Get student's attendance records
    conn = get_db_connection()
    stats = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        # We fetch ALL records first, then filter in Python to match working_days logic easier,
        # or we could filter in SQL. Python is fine for now.
        cursor.execute("SELECT * FROM attendance WHERE RegisterNo = %s ORDER BY Date DESC", (reg_no,))
        all_stats = cursor.fetchall()
        conn.close()
        
        # Filter stats by month if needed
        if month_filter:
            stats = []
            for rec in all_stats:
                d_str = rec['Date'].strftime('%Y-%m-%d') if hasattr(rec['Date'], 'strftime') else str(rec['Date'])
                if d_str.startswith(month_filter):
                    stats.append(rec)
        else:
            stats = all_stats
        
    # Process Stats
    present_dates = set()
    od_dates = set()
    
    # Map for easy lookup by date string
    attendance_map = {}
    
    for record in stats:
        d_str = record['Date'].strftime('%Y-%m-%d') if hasattr(record['Date'], 'strftime') else str(record['Date'])
        attendance_map[d_str] = record
        
        if record['Status'] == 'Present':
            present_dates.add(d_str)
        elif record['Status'] == 'OD':
            od_dates.add(d_str)
            
    present_count = len(present_dates)
    od_count = len(od_dates)
    
    # Calculate Absent
    # Absent = Total Working Days - (Present + OD)
    # Note: This assumes the student was expected to be present on all 'working_days'. 
    # If a student joined late, this might count prior days as absent, which is standard simple logic.
    
    # We only count absences for days that are in 'working_days' but NOT in present/od
    # working_days contains date objects usually, let's normalize to strings
    working_days_str = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in working_days]
    
    absent_count = 0
    detailed_history = []
    
    for day in working_days_str:
        status = 'Absent'
        in_time = '-'
        out_time = '-'
        
        if day in attendance_map:
            rec = attendance_map[day]
            status = rec['Status']
            in_time = str(rec['Morning_IN']) if rec['Morning_IN'] else '-'
            out_time = str(rec['Evening_OUT']) if rec['Evening_OUT'] else '-'
        else:
            absent_count += 1
            
        # --- Apply Status Filter to HISTORY List Only ---
        # (We still want the summary stats to reflect the whole month/period, 
        # but the list can be filtered to show only Absent days, for example)
        
        include_record = True
        if status_filter and status_filter != 'All':
            if status_filter == 'Present' and status != 'Present':
                include_record = False
            elif status_filter == 'Absent' and status != 'Absent':
                include_record = False
            elif status_filter == 'OD' and status != 'OD':
                include_record = False
        
        if include_record:
            detailed_history.append({
                'Date': day,
                'Morning_IN': in_time,
                'Evening_OUT': out_time,
                'Status': status
            })
        
    # Sort history by date desc
    detailed_history.sort(key=lambda x: x['Date'], reverse=True)

    return {
        'info': student,
        'statistics': {
            'TotalDays': total_working_days,
            'Present': present_count,
            'OD': od_count,
            'Absent': absent_count,
            'Percentage': round(((present_count + od_count) / total_working_days * 100), 2) if total_working_days > 0 else 0
        },
        'history': detailed_history
    }

def get_available_months():
    """
    Returns a list of month objects for the filter dropdown.
    Format: [{'value': 'YYYY-MM', 'label': 'MonthName YYYY'}, ...]
    Includes distinct months from DB + All months of current year.
    """
    init_db()
    conn = get_db_connection()
    if not conn: return []
    
    cursor = conn.cursor()
    try:
        # Extract YYYY-MM from Date
        # MySQL specific syntax
        cursor.execute("SELECT DISTINCT DATE_FORMAT(Date, '%Y-%m') FROM attendance ORDER BY Date DESC")
        db_months = {row[0] for row in cursor.fetchall() if row[0]}
        
        all_months = set(db_months)
        
        # Add all months of the current year
        current_year = date.today().year
        for m in range(1, 13):
            all_months.add(f"{current_year}-{m:02d}")
            
        # Sort descending
        sorted_months = sorted(list(all_months), reverse=True)
        
        formatted_months = []
        for m in sorted_months:
            try:
                dt = datetime.strptime(m, '%Y-%m')
                formatted_months.append({
                    'value': m,
                    'label': dt.strftime('%B %Y') # e.g. "January 2024"
                })
            except Exception:
                continue
                
        return formatted_months
    except Exception as e:
        print(f"Error fetching months: {e}")
        return []
    finally:
        conn.close()

def get_distinct_dates():
    """Returns a list of all unique dates where attendance was taken."""
    init_db()
    conn = get_db_connection()
    if not conn: return []
    
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT Date FROM attendance ORDER BY Date DESC")
        dates = [row[0] for row in cursor.fetchall()] # row is tuple (date,)
        return dates
    except Exception as e:
        print(f"Error fetching dates: {e}")
        return []
    finally:
        conn.close()


