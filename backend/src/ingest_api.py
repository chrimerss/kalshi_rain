import requests
import logging
from datetime import datetime, timezone, timedelta
import pandas as pd
from typing import List, Dict

import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.src.config import STATIONS, MODELS, Station
from backend.src.db import save_forecast, get_latest_observation

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

def fetch_open_meteo_forecasts():
    """
    Fetches forecasts for all stations and models from Open-Meteo.
    """
    
    # helper to get end of month
    now = datetime.now(timezone.utc)
    current_month = now.month
    current_year = now.year
    if current_month == 12:
        next_month = datetime(current_year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(current_year, current_month + 1, 1, tzinfo=timezone.utc)
    month_end = next_month - timedelta(seconds=1)
    
    # 1. Prepare Request Parameters
    lats = [s.lat for s in STATIONS.values()]
    lons = [s.lon for s in STATIONS.values()]
    station_ids = list(STATIONS.keys())
    
    # We want daily sums to easily calculate the remainder of the month
    # We also ask for 'precipitation_sum' or 'rain_sum'. 'rain_sum' excludes snow, 'precipitation_sum' includes it.
    # Given the app is "RainForecast", but usually "Precipitation" is desired for water/hydro.
    # The previous GRIB logic extracted Total Precip. Let's use 'precipitation_sum'.
    
    # Models to query - Grouped by Forecast Horizon to avoid API errors
    # HRRR: ~2 days (48h)
    # NAM: ~2.5 days (60h)
    # Global (GFS, ECMWF, GEM, ICON): ~10-16 days
    
    # Models to query - Grouped by Forecast Horizon
    # User confirmed NAM/HRRR are not needed/available via this API.
    # Global (GFS, ECMWF, GEM, ICON): ~10-16 days
    
    model_groups = [
        {"days": 16, "models": ["gfs_seamless", "ecmwf_ifs", "ecmwf_ifs025", "ecmwf_aifs025_single", "icon_seamless", "gem_global"]},
    ]
    
    for group in model_groups:
        days = group['days']
        models = group['models']
        
        params = {
            "latitude": lats,
            "longitude": lons,
            "hourly": "precipitation", 
            "timezone": "UTC",
            "precipitation_unit": "inch",
            "models": models,
            "forecast_days": days
        }
        
        logger.info(f"Fetching {models} (Days: {days}) from Open-Meteo (Hourly)...")
        
        try:
            response = requests.get(OPEN_METEO_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data, list):
                data = [data]
                
            for i, station_data in enumerate(data):
                station_id = station_ids[i]
                station = STATIONS[station_id]
                
                hourly_data = station_data.get("hourly", {})
                # parsing with utc=True ensures timezone-aware UTC
                times = pd.to_datetime(hourly_data.get("time", []), utc=True)
                
                # No need for manual localization now
                
                
                for model_api_name in models:
                    model_friendly_name = next((k for k, v in MODELS.items() if v == model_api_name), None)
                    if not model_friendly_name:
                        continue

                    # Key usually "precipitation_modelname"
                    target_key = f"precipitation_{model_api_name}"
                    if target_key not in hourly_data:
                         # Fallback for when only 1 model is requested?
                         # API usually appends suffix if 'models' param is used.
                         if f"precipitation" in hourly_data and len(models) == 1:
                             target_key = "precipitation"
                         else:
                             continue
                    
                    values = hourly_data[target_key]
                    df = pd.DataFrame({'time': times, 'val': values})
                    
                    # Sum from NOW until End of Month
                    relevant_df = df[(df['time'] >= now) & (df['time'] <= month_end)]
                    
                    forecast_remainder = relevant_df['val'].sum()
                    
                    # Partiality Check
                    if not df.empty:
                        latest_forecast_time = df['time'].max()
                        is_partial = latest_forecast_time < month_end
                    else:
                        is_partial = True
                        forecast_remainder = 0.0
                    
                    if pd.isna(forecast_remainder):
                        forecast_remainder = 0.0
                    
                    save_forecast(
                        location_id=station.id,
                        model_name=model_friendly_name,
                        init_time=now.isoformat(),
                        observed_mtd=get_latest_observation(station.id),
                        forecast_remainder=float(forecast_remainder),
                        is_partial=is_partial
                    )
                    
            logger.info(f"Processed group {models}.")
                
        except Exception as e:
            logger.error(f"Failed to fetch {models}: {e}")

def parse_duration(pt_string):
    """
    Custom simple parser for ISO8601 Duration (PTnH).
    """
    if not pt_string.startswith("PT"):
        return timedelta(0)
    
    try:
        if "H" in pt_string:
            hours = int(pt_string.replace("PT", "").replace("H", ""))
            return timedelta(hours=hours)
        elif "M" in pt_string:
            # Note: T1M meant 1 minute usually, but P1M is 1 month. PT1M is 1 minute.
            minutes = int(pt_string.replace("PT", "").replace("M", ""))
            return timedelta(minutes=minutes)
    except:
        return timedelta(0)
    return timedelta(0)

def fetch_nws_forecasts():
    """
    Fetches Gridpoints Forecast for all stations from NWS API.
    Replaces HRRR/NAM for short-term high-res data.
    """
    logger.info("Fetching data from NWS API...")
    
    now = datetime.now(timezone.utc)
    current_month = now.month
    current_year = now.year
    if current_month == 12:
        next_month = datetime(current_year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(current_year, current_month + 1, 1, tzinfo=timezone.utc)
    month_end = next_month - timedelta(seconds=1)
    
    headers = {"User-Agent": "(raincheck-app, contact@example.com)"}
    
    # 1. Iterate Stations (10 stations, sequential is fine)
    for station_id, station in STATIONS.items():
        try:
            logger.info(f"Processing NWS for {station.name}...")
            
            # A. Get Grid Points
            # Ensure we don't spam the API. In production, cache this.
            points_url = f"https://api.weather.gov/points/{station.lat},{station.lon}"
            r = requests.get(points_url, headers=headers, timeout=10)
            if r.status_code != 200:
                logger.error(f"Failed to get points for {station.id}: {r.status_code}")
                continue
                
            props = r.json().get('properties', {})
            grid_id = props.get('gridId')
            grid_x = props.get('gridX')
            grid_y = props.get('gridY')
            
            if not grid_id:
                logger.error(f"No grid info for {station.id}")
                continue
            
            # B. Get Gridpoints Data (QPF)
            gridpoints_url = f"https://api.weather.gov/gridpoints/{grid_id}/{grid_x},{grid_y}"
            r = requests.get(gridpoints_url, headers=headers, timeout=10)
            if r.status_code != 200:
                logger.error(f"Failed to get gridpoints for {station.id}: {r.status_code}")
                continue
                
            qpf_data = r.json().get('properties', {}).get('quantitativePrecipitation', {})
            values = qpf_data.get('values', [])
            uom = qpf_data.get('uom', 'wmoUnit:mm')
            
            # C. Parse and Sum
            total_mm = 0.0
            max_valid_time = now # Track latest forecast time
            
            for item in values:
                # Format: "2026-01-18T19:00:00+00:00/PT6H"
                vt_str = item.get('validTime')
                val = item.get('value', 0) or 0 # Handle None
                
                if "/" not in vt_str:
                    continue
                    
                start_str, dur_str = vt_str.split("/")
                start_time = datetime.fromisoformat(start_str)
                duration = parse_duration(dur_str)
                end_time = start_time + duration
                
                # Check overlap: (Start < MonthEnd) AND (End > Now)
                # We want sum of future rain in this month.
                # Simplification: If the block ends after Now and starts before MonthEnd.
                
                if end_time > now and start_time < month_end:
                    total_mm += val
                    
                if end_time > max_valid_time:
                    max_valid_time = end_time
                    
            # D. Convert and Save
            total_inches = total_mm * 0.0393701
            
            is_partial = max_valid_time < month_end
            # NWS is usually 7 days, so always partially implies "Month End" if > 7 days away.
            
            observed = get_latest_observation(station.id)
            
            save_forecast(
                location_id=station.id,
                model_name="NWS",
                init_time=now.isoformat(),
                observed_mtd=observed,
                forecast_remainder=float(total_inches),
                is_partial=is_partial
            )
            
            logger.info(f"Updated NWS for {station.name}: {total_inches:.2f} inches")
            
        except Exception as e:
            logger.error(f"Error processing NWS for {station.id}: {e}")


def fetch_nbm_forecasts():
    """
    Fetches NBM Hourly Text (NBH) product from S3.
    Replaces HRRR/NAM.
    """
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config
    
    logger.info("Fetching data from NBM Text Product...")
    
    s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))
    bucket = "noaa-nbm-grib2-pds"
    
    # 1. Find Latest File
    now = datetime.now(timezone.utc)
    found_key = None
    
    # Try last 5 hours
    for i in range(6):
        t = now - timedelta(hours=i)
        ymd = t.strftime("%Y%m%d")
        hour = t.hour
        # blend.{ymd}/{init_hour:02d}/text/blend_nbhtx.t{init_hour:02d}z
        key = f"blend.{ymd}/{hour:02d}/text/blend_nbhtx.t{hour:02d}z"
        try:
            s3.head_object(Bucket=bucket, Key=key)
            found_key = key
            logger.info(f"Found NBM file: {key}")
            break
        except:
            continue
            
    if not found_key:
        logger.error("Could not find recent NBM text file.")
        return

    # 2. Stream and Parse
    # We need to buffer data for all stations.
    # Structure: { station_id: { valid_time: value_inches } }
    station_data = {sid: {} for sid in STATIONS}
    
    # Helper to calculate end of month
    current_month = now.month
    current_year = now.year
    if current_month == 12:
        next_month = datetime(current_year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(current_year, current_month + 1, 1, tzinfo=timezone.utc)
    month_end = next_month - timedelta(seconds=1)
    
    try:
        response = s3.get_object(Bucket=bucket, Key=found_key)
        stream = response['Body']
        
        current_station = None
        base_date = None # From header
        current_dates = [] # List of datetimes corresponding to columns
        
        # State:
        # We look for Station ID line.
        # Then we look for header line with Date? Or Station ID line IS the header?
        # Header: "086092 NBM V4.3 ..." 
        # Station line: "KLOX    NBM V4.3 ..." - Wait, the test script output showed "086092" first?
        # The test script output:
        # "Captured block for KLOX"
        # "UTC: UTC 04 05..."
        # But wait, did I see the line *containing* KLOX in the snippet?
        # Snippet: " 086092 NBM V4.3 ... KLOX found!"
        # Ah, looking at `test_nbm.py` output again...
        # "Captured block for KLOX"
        # The line triggering "Found station" was: "KLOX   NBM V4.3 NBH GUIDANCE ..." (Presumably, I need to verify EXACT format).
        # Actually my test script checked `if parts[0] in target_stations`.
        # So the line starts with "KLOX".
        
        for line_bytes in stream.iter_lines():
            if not line_bytes: continue
            line = line_bytes.decode('utf-8', errors='ignore')
            parts = line.split()
            if not parts: continue
            
            # Check for Station Header
            if parts[0] in STATIONS:
                current_station = parts[0]
                # Parse Date from header line
                # "KLOX   NBM V4.3 NBH GUIDANCE    1/19/2026  0300 UTC"
                # Date is usually at index -3 (date) and -2 (time)?
                # Let's find the date part "M/D/YYYY".
                try:
                    date_str = next((p for p in parts if "/" in p and p[0].isdigit()), None)
                    if date_str:
                         # e.g. 1/19/2026
                         month, day, year = map(int, date_str.split('/'))
                         # We need a base localized time.
                         # NBM is UTC.
                         base_date = datetime(year, month, day, tzinfo=timezone.utc)
                except:
                    pass
                continue
            
            if current_station:
                # 3. Parse UTC Line
                # "UTC  04 05 06 ... 23 00 01 ..."
                if parts[0] == "UTC":
                    if not base_date: continue
                    
                    current_dates = []
                    # Logic to reconstructing full timestamps
                    # The first hour corresponds to base_date + some offset?
                    # Or does the day increment when hour rolls over?
                    # "1/19/2026" and hours "04 05..." (starts at 4am on 19th?)
                    # If 0300 UTC run, output starts 0400 UTC.
                    
                    # We assume sequential hours.
                    # Find start hour
                    hrs = [int(h) for h in parts[1:]]
                    if not hrs: continue
                    
                    # If first hour < run_hour? No, just assume forward.
                    # But date rollover?
                    # Use a running pointer.
                    
                    # Construct timestamps
                    # Start with base_date. 
                    # If first hour is say 04, and base_date hour is 00?
                    # Date in header is usually Run Date.
                    
                    # Heuristic: 
                    # Create a candidate time for first column using base_date + hour.
                    # If candidate < base_date (e.g. 1/19 0100 for 1/19 header?), usually unlikely if forecasts are future.
                    # But 0300 UTC run might have 0400 UTC first.
                    
                    # Let's track expected date.
                    dt_ptr = base_date.replace(hour=hrs[0], minute=0, second=0, microsecond=0)
                    # If header date/time is available, strictly use it.
                    # Assuming header date is valid for the start.
                    
                    last_h = hrs[0]
                    for h in hrs:
                        if h < last_h:
                            # Rollover midnight
                            dt_ptr += timedelta(days=1)
                        
                        # Set hour
                        dt_ptr = dt_ptr.replace(hour=h)
                        current_dates.append(dt_ptr)
                        last_h = h
                        
                # 4. Parse Q01 Line
                # "Q01   0  0  0 ..." (hundredths of inch)
                elif parts[0] == "Q01":
                    if not current_dates: continue
                    
                    vals = parts[1:]
                    for t_idx, val_str in enumerate(vals):
                        if t_idx >= len(current_dates): break
                        
                        try:
                            val_hundredths = int(val_str)
                            val_inches = val_hundredths / 100.0
                            
                            dt = current_dates[t_idx]
                            
                            # Add to station data
                            if dt not in station_data[current_station]:
                                station_data[current_station][dt] = 0.0
                            station_data[current_station][dt] = val_inches
                        except:
                            pass
                            
                    # End of block for this station? usually multiple lines.
                    # But we got what we needed from this block.
                    # Don't reset current_station immediately, maybe there's P01?
                    # But we only need Q01.
                    pass
    
    except Exception as e:
        logger.error(f"Error streaming NBM: {e}")
        
    # 5. Save to DB
    for sid, data in station_data.items():
        if not data: continue
        
        # Sum valid future rain
        total_precip = 0.0
        max_time = now
        
        for dt, val in data.items():
            if dt > now and dt <= month_end:
                total_precip += val
            if dt > max_time:
                max_time = dt
        
        is_partial = max_time < month_end
        
        observed = get_latest_observation(sid)
        
        save_forecast(
            location_id=sid,
            model_name="NBM", # User requested replacement for HRRR/NAM
            init_time=now.isoformat(),
            observed_mtd=observed,
            forecast_remainder=float(total_precip),
            is_partial=is_partial
        )
        logger.info(f"Updated NBM for {STATIONS[sid].name}: {total_precip:.2f} inches")

if __name__ == "__main__":
    fetch_open_meteo_forecasts()
    fetch_nws_forecasts()
    fetch_nbm_forecasts()

