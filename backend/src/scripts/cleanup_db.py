import sqlite3
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))
from backend.src.config import DB_PATH

def cleanup_duplicates():
    print("Cleaning up duplicate DB entries...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Enable WAL just in case
    conn.execute("PRAGMA journal_mode=WAL")
    
    # Identify duplicates: same loc, model, time. Keep row with highest ID (latest).
    query = '''
        DELETE FROM forecasts
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM forecasts
            GROUP BY location_id, model_name, init_time
        )
    '''
    c.execute(query)
    deleted = c.rowcount
    print(f"Deleted {deleted} duplicate rows.")
    
    # Create the Unique Index if not exists (db.py does this, but good to ensure now)
    try:
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_forecasts_unique ON forecasts (location_id, model_name, init_time)')
        print("Ensured Unique Index exists.")
    except Exception as e:
        print(f"Error creating index: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    cleanup_duplicates()
