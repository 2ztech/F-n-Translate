import sqlite3
import os
import sys

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def inspect_db():
    db_path = 'app_database.db'
    if not os.path.exists(db_path):
        print("DB not found")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- translation_cache (First 20) ---")
    try:
        cursor.execute("SELECT * FROM translation_cache LIMIT 20")
        rows = cursor.fetchall()
        for row in rows:
            print(row)
    except Exception as e:
        print(f"Error reading translation_cache: {e}")
        
    conn.close()

if __name__ == "__main__":
    inspect_db()
