import sqlite3
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))
from backend.src.config import DB_PATH

def cleanup_locations():
    print("Cleaning up old location IDs (KCQT, KLAX)...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Enable WAL
    conn.execute("PRAGMA journal_mode=WAL")
    
    # Delete forecasts for KCQT and KLAX
    c.execute("DELETE FROM forecasts WHERE location_id IN ('KCQT', 'KLAX')")
    deleted_forecasts = c.rowcount
    print(f"Deleted {deleted_forecasts} entries from forecasts.")
    
    # Delete climatology for KCQT and KLAX
    c.execute("DELETE FROM climatology WHERE location_id IN ('KCQT', 'KLAX')")
    deleted_climatology = c.rowcount
    print(f"Deleted {deleted_climatology} entries from climatology.")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    cleanup_locations()
