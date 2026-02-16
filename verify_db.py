import mysql.connector
from utils import DB_CONFIG

def verify_setup():
    print("--- Verifying MySQL Setup ---")
    print(f"Configuration: Host={DB_CONFIG['host']}, User={DB_CONFIG['user']}, DB={DB_CONFIG['database']}")
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print("[SUCCESS] Connected to database.")
        
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [x[0] for x in cursor.fetchall()]
        print(f"Tables found: {tables}")
        
        required_tables = ['students', 'staff', 'attendance']
        missing = [t for t in required_tables if t not in tables]
        
        if missing:
            print(f"[WARNING] Missing tables: {missing}. Run the app or utils.init_db() to create them.")
        else:
            print("[SUCCESS] All required tables exist.")
            
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as err:
        print(f"[ERROR] Connection failed: {err}")
        print("Please ensure MySQL is running and credentials in utils.py are correct.")

if __name__ == "__main__":
    verify_setup()
