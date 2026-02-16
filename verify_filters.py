import sys
import os

# Ensure we can import from app directory
sys.path.append(os.getcwd())

from utils import get_student_summary, get_available_months, get_all_students

def verify():
    print("--- Verifying Attendance Filtering Logic ---")
    
    # 1. Check Available Months
    months = get_available_months()
    print(f"Available Months: {months}")
    
    students = get_all_students()
    if not students:
        print("No students found. Cannot verify filtering.")
        return

    # Pick a student
    student = students[0]
    reg_no = student['RegisterNo']
    print(f"Testing with Student: {student['Name']} ({reg_no})")
    
    # 2. Test No Filter
    summary_all = get_student_summary(reg_no)
    print(f"\n[No Filter] Total Days: {summary_all['statistics']['TotalDays']}, History Count: {len(summary_all['history'])}")
    
    # 3. Test Month Filter (if available)
    if months:
        # months is now a list of dicts: {'value': '...', 'label': '...'}
        target_month_val = months[0]['value']
        target_month_label = months[0]['label']
        
        summary_month = get_student_summary(reg_no, month_filter=target_month_val)
        print(f"\n[Month Filter: {target_month_label}] Total Days: {summary_month['statistics']['TotalDays']}, History Count: {len(summary_month['history'])}")
        
        # Verify dates in history match month
        for record in summary_month['history']:
             if not str(record['Date']).startswith(target_month_val):
                 print(f"ERROR: Found date {record['Date']} in month filter {target_month_val}")
    
    # 4. Test Status Filter
    target_status = 'Present' # Assumption
    summary_status = get_student_summary(reg_no, status_filter=target_status)
    print(f"\n[Status Filter: {target_status}] Total Days: {summary_status['statistics']['TotalDays']}, History Count: {len(summary_status['history'])}")
    
    for record in summary_status['history']:
        if record['Status'] != target_status:
             print(f"ERROR: Found status {record['Status']} in status filter {target_status}")

if __name__ == "__main__":
    verify()
