import sqlite3
from datetime import datetime
import os
from .config import DB_PATH

def get_db_connection():
    db_folder = os.path.dirname(DB_PATH)
    if not os.path.exists(db_folder):
        os.makedirs(db_folder)
        
    conn = sqlite3.connect(DB_PATH, timeout=10) # 10s timeout
    conn.execute("PRAGMA journal_mode=WAL") # Enable WAL mode
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Table for storing forecasts and observations
    c.execute('''
        CREATE TABLE IF NOT EXISTS forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id TEXT NOT NULL,
            model_name TEXT NOT NULL,
            init_time TEXT NOT NULL,         -- ISO format timestamp of model run or observation time
            observed_mtd REAL,               -- Observed Month-To-Date value (from NWS CLI)
            forecast_remainder REAL,         -- Forecasted accumulation for rest of month
            total_proj REAL,                 -- observed_mtd + forecast_remainder
            is_partial BOOLEAN DEFAULT 0,    -- Flag if forecast doesn't cover full month remainder
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Table for climatology
    c.execute('''
        CREATE TABLE IF NOT EXISTS climatology (
            location_id TEXT,
            month INTEGER,
            value REAL,
            PRIMARY KEY (location_id, month)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS kalshi_markets (
            ticker TEXT PRIMARY KEY,
            location_id TEXT,
            title TEXT,
            yes_price INTEGER,
            no_price INTEGER,
            status TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    
    # Index for fast lookups and Uniqueness to prevent duplicates
    c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_forecasts_unique ON forecasts (location_id, model_name, init_time)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_forecasts_loc_model ON forecasts (location_id, model_name)')
    
    conn.commit()
    conn.close()

def get_latest_observation(location_id: str) -> float:
    """Retrieves the latest NWS_CLI observed MTD value for a location."""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        SELECT observed_mtd FROM forecasts 
        WHERE location_id = ? AND model_name = 'NWS_CLI'
        ORDER BY init_time DESC LIMIT 1
    ''', (location_id,))
    
    row = c.fetchone()
    conn.close()
    
    if row:
        return row['observed_mtd']
    return 0.0

def get_climatology_value(location_id: str, month: int) -> float:
    """Retrieves the climatology value for a location and month."""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        SELECT value FROM climatology 
        WHERE location_id = ? AND month = ?
    ''', (location_id, month))
    
    row = c.fetchone()
    conn.close()
    
    if row:
        return row['value']
    return 3.0 # Default fallback


def save_forecast(location_id, model_name, init_time, observed_mtd, forecast_remainder, is_partial=False):
    conn = get_db_connection()
    c = conn.cursor()
    
    total_proj = (observed_mtd or 0.0) + (forecast_remainder or 0.0)
    
    c.execute('''
        INSERT OR REPLACE INTO forecasts 
        (location_id, model_name, init_time, observed_mtd, forecast_remainder, total_proj, is_partial)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (location_id, model_name, init_time, observed_mtd, forecast_remainder, total_proj, is_partial))
    
    conn.commit()
    conn.close()

def get_latest_forecasts():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get the latest entry for each location+model combination
    query = '''
        SELECT f.* 
        FROM forecasts f
        INNER JOIN (
            SELECT location_id, model_name, MAX(init_time) as max_time
            FROM forecasts
            GROUP BY location_id, model_name
        ) latest ON f.location_id = latest.location_id 
                AND f.model_name = latest.model_name 
                AND f.init_time = latest.max_time
        ORDER BY f.location_id, f.model_name
    '''
    
    rows = c.execute(query).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def save_market_data(ticker, location_id, title, yes_price, no_price, status):
    conn = get_db_connection()
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO kalshi_markets 
            (ticker, location_id, title, yes_price, no_price, status, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (ticker, location_id, title, yes_price, no_price, status))
    conn.close()

def get_latest_markets(location_id):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("""
        SELECT * FROM kalshi_markets 
        WHERE location_id = ? AND status = 'active'
        ORDER BY ticker
    """, (location_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
