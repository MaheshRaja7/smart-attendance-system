from utils import get_all_students

students = get_all_students()
print(f"Total students: {len(students)}")
for s in students:
    print(f"RegNo: '{s['RegisterNo']}', Email: '{s['Email']}', Pwd(RegNo): '{s['RegisterNo']}'")
