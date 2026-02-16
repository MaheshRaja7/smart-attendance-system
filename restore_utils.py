
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
