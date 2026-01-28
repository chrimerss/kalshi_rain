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

    # Table for Temperature Forecasts
    c.execute('''
        CREATE TABLE IF NOT EXISTS temperature_forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id TEXT NOT NULL,
            target_date TEXT NOT NULL,       -- YYYY-MM-DD
            model_name TEXT NOT NULL,
            forecast_type TEXT DEFAULT 'high', -- 'high' or 'low'
            forecast_value REAL,             -- Forecasted Temp (F)
            observed_value REAL,             -- Observed Temp (F)
            error REAL,                      -- forecast - observed
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(location_id, target_date, model_name, forecast_type)
        )
    ''')
    
    # Migration: Add forecast_type column to existing table if missing
    try:
        c.execute("ALTER TABLE temperature_forecasts ADD COLUMN forecast_type TEXT DEFAULT 'high'")
    except:
        pass  # Column already exists
    
    # Table for Synoptic real-time observations
    c.execute('''
        CREATE TABLE IF NOT EXISTS synoptic_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT NOT NULL,
            obs_time TEXT NOT NULL,           -- ISO format timestamp
            air_temp REAL,                    -- Temperature (F)
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(station_id, obs_time)
        )
    ''')
    
    # Index for fast lookups
    c.execute('CREATE INDEX IF NOT EXISTS idx_synoptic_station_time ON synoptic_observations (station_id, obs_time)')
    
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

def save_market_data(ticker, location_id, title, yes_price, no_price, status, target_date=None):
    conn = get_db_connection()
    with conn:
        # Check if column exists (migration hack for existing dbs)
        try:
            conn.execute("ALTER TABLE kalshi_markets ADD COLUMN target_date TEXT")
        except:
            pass
            
        conn.execute("""
            INSERT OR REPLACE INTO kalshi_markets 
            (ticker, location_id, title, yes_price, no_price, status, target_date, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (ticker, location_id, title, yes_price, no_price, status, target_date))
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

def save_temperature_forecast(location_id, target_date, model_name, forecast_value, forecast_type='high'):
    """Save a temperature forecast. forecast_type is 'high' or 'low'."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Upsert: preserved observed_value if it exists
    c.execute('''
        INSERT INTO temperature_forecasts (location_id, target_date, model_name, forecast_type, forecast_value)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(location_id, target_date, model_name, forecast_type) DO UPDATE SET
        forecast_value = excluded.forecast_value,
        created_at = CURRENT_TIMESTAMP
    ''', (location_id, target_date, model_name, forecast_type, forecast_value))
    
    conn.commit()
    conn.close()

def update_temperature_observation(location_id, target_date, observed_value, forecast_type='high'):
    """Update observed temperature for a specific forecast type ('high' or 'low')."""
    conn = get_db_connection()
    c = conn.cursor()

    def round_half_up(value: float) -> int:
        return int(value + 0.5)

    rounded_observed = round_half_up(observed_value)

    # Update ALL model rows for that target_date and forecast_type with the same observed value.
    # Error is computed using rounded forecast and observed values.
    c.execute('''
        UPDATE temperature_forecasts
        SET observed_value = ?,
            error = (CAST(forecast_value + 0.5 AS INTEGER)) - ?
        WHERE location_id = ? AND target_date = ? AND forecast_type = ?
    ''', (rounded_observed, rounded_observed, location_id, target_date, forecast_type))
    
    conn.commit()
    conn.close()

def cleanup_temperature_data(today_str: str, tomorrow_str: str):
    conn = get_db_connection()
    c = conn.cursor()

    # Keep historical rows (before today) and only tomorrow's forecasts.
    c.execute('''
        DELETE FROM temperature_forecasts
        WHERE target_date >= ? AND target_date != ?
    ''', (today_str, tomorrow_str))

    # Keep only tomorrow's temperature markets.
    c.execute('''
        DELETE FROM kalshi_markets
        WHERE ticker NOT LIKE 'KXRAIN%'
          AND (target_date IS NULL OR target_date != ?)
    ''', (tomorrow_str,))

    conn.commit()
    conn.close()

def get_temperature_forecasts(location_id, limit=30):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('''
        SELECT * FROM temperature_forecasts
        WHERE location_id = ?
        ORDER BY target_date DESC
        LIMIT ?
    ''', (location_id, limit))
    
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def save_synoptic_observation(station_id: str, obs_time: str, air_temp: float):
    """Save a synoptic observation."""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        INSERT OR REPLACE INTO synoptic_observations (station_id, obs_time, air_temp)
        VALUES (?, ?, ?)
    ''', (station_id, obs_time, air_temp))
    
    conn.commit()
    conn.close()

def get_synoptic_observations(station_id: str, hours: int = 24):
    """Get recent synoptic observations for a station."""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        SELECT obs_time, air_temp FROM synoptic_observations
        WHERE station_id = ?
        ORDER BY obs_time DESC
        LIMIT ?
    ''', (station_id, hours * 60))  # Assume ~1 obs per minute
    
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def clear_old_synoptic_observations(station_id: str, keep_hours: int = 48):
    """Remove synoptic observations older than keep_hours."""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        DELETE FROM synoptic_observations
        WHERE station_id = ? 
        AND datetime(obs_time) < datetime('now', ? || ' hours')
    ''', (station_id, f'-{keep_hours}'))
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
