import csv
import sys
import os
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))

from backend.src.db import get_db_connection
from backend.src.config import DB_PATH

CSV_PATH = Path("/Users/allen/Documents/Python/rain_forecast/climatology_rain.csv")

def parse_month(month_str):
    try:
        return datetime.strptime(month_str.strip().upper(), "%B").month
    except ValueError:
        return None

def ingest_climatology_csv():
    print(f"Reading from {CSV_PATH}...")
    
    if not CSV_PATH.exists():
        print("CSV file not found.")
        return

    conn = get_db_connection()
    c = conn.cursor()
    
    # Ensure WAL mode
    conn.execute("PRAGMA journal_mode=WAL")

    rows_processed = 0
    with open(CSV_PATH, 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            station_id = row['Station'].strip()
            month_str = row['Month'].strip()
            value_str = row['Normal_Precipitation_Inches'].strip()
            
            month_int = parse_month(month_str)
            if not month_int:
                print(f"Skipping invalid month: {month_str}")
                continue
                
            try:
                value = float(value_str)
            except ValueError:
                print(f"Skipping invalid value for {station_id}-{month_str}: {value_str}")
                continue
            
            # Upsert into DB
            c.execute('''
                INSERT OR REPLACE INTO climatology (location_id, month, value)
                VALUES (?, ?, ?)
            ''', (station_id, month_int, value))
            
            rows_processed += 1
            
    conn.commit()
    conn.close()
    print(f"Successfully processed {rows_processed} rows.")

if __name__ == "__main__":
    ingest_climatology_csv()
