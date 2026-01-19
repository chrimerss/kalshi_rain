import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))

from backend.src.db import init_db, get_db_connection
from backend.src.config import STATIONS

def init_climatology():
    print("Initializing Climatology Table...")
    init_db() # Ensure table exists
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if empty
    c.execute("SELECT count(*) as count FROM climatology")
    count = c.fetchone()['count']
    
    if count > 0:
        print(f"Climatology table already has {count} entries. Skipping.")
        conn.close()
        return

    # Insert placeholders
    # 3.0 inches for all months/stations
    months = range(1, 13)
    
    for station_id in STATIONS.keys(): # STATIONS keys are friendly names? No, config keys are "NYC", "CLILAX".
        # config.py STATIONS maps Key -> Station(id="KNYC"...)
        # We should probably use config key or Station ID?
        # The DB uses `location_id` which usually matches Station.id (KNYC).
        
        station_obj = STATIONS[station_id]
        loc_id = station_obj.id 
        
        print(f"Populating for {loc_id} ({station_obj.name})...")
        for m in months:
            c.execute('''
                INSERT INTO climatology (location_id, month, value)
                VALUES (?, ?, ?)
            ''', (loc_id, m, 3.0))
            
    conn.commit()
    conn.close()
    print("Climatology initialization complete.")

if __name__ == "__main__":
    init_climatology()
