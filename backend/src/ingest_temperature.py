
import requests
import logging
import pytz
from datetime import datetime, timedelta
import pandas as pd
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.src.config import STATIONS, MODELS, Station
from backend.src.db import save_temperature_forecast
from backend.src.scraper import update_observed_temperature

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

def get_next_day_date(station: Station) -> tuple[datetime, str]:
    """
    Returns the (datetime_obj, date_string) for 'Tomorrow' in the station's local time.
    """
    tz = pytz.timezone(station.timezone)
    now_local = datetime.now(tz)
    tomorrow_local = now_local + timedelta(days=1)
    return tomorrow_local, tomorrow_local.strftime("%Y-%m-%d")

def fetch_open_meteo_temp():
    """
    Fetches Next Day Max Temp from Open-Meteo.
    """
    logger.info("Fetching Temperature from Open-Meteo...")
    
    # Process station by station to ensure correct timezone handling
    for station_id, station in STATIONS.items():
        tomorrow_dt, tomorrow_str = get_next_day_date(station)
        
        # Models to query
        models = [
            "gfs_hrrr",
            "ncep_nbm_conus",
            "gfs_graphcast025",
            "gfs_seamless",
            "gem_global",
            "icon_seamless",
            "ecmwf_ifs",
            "ecmwf_ifs025",
            "ecmwf_aifs025_single",
        ]
        model_names_map = {
             "gfs_hrrr": "HRRR",
             "ncep_nbm_conus": "NBM",
             "gfs_graphcast025": "GraphCast",
             "gfs_seamless": "GFS",
             "gem_global": "GEM",
             "icon_seamless": "ICON",
             "ecmwf_ifs": "ECMWF IFS",
             "ecmwf_ifs025": "ECMWF IFS 0.25",
             "ecmwf_aifs025_single": "ECMWF AIFS",
        }
        
        params = {
            "latitude": station.lat,
            "longitude": station.lon,
            "daily": "temperature_2m_max",
            "timezone": station.timezone, # Explicit timezone
            "models": ",".join(models),
            "temperature_unit": "fahrenheit",
            "start_date": tomorrow_str,
            "end_date": tomorrow_str 
        }
        
        try:
            r = requests.get(OPEN_METEO_URL, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            
            # API returns a list if multiple models? 
            # No, if 'models' is comma-separated, it typically returns one JSON with fields `daily: { temperature_2m_max_modelname: [...] }`
            # Wait, Open-Meteo docs say: if multiple models, `daily` has keys like `temperature_2m_max_gfs_seamless`.
            
            daily_data = data.get("daily", {})
            
            for api_model in models:
                key = f"temperature_2m_max_{api_model}"
                # If only 1 model requested, suffix might be omitted? No, usually if 'models' param is present, suffixes are used.
                # But let's check.
                if key not in daily_data and "temperature_2m_max" in daily_data and len(models) == 1:
                     key = "temperature_2m_max"
                
                if key in daily_data:
                    vals = daily_data[key]
                    if vals and vals[0] is not None:
                        val = float(vals[0])
                        friendly_name = model_names_map.get(api_model, api_model)
                        
                        save_temperature_forecast(
                            location_id=station.id,
                            target_date=tomorrow_str,
                            model_name=friendly_name,
                            forecast_value=val
                        )
                        logger.info(f"{station.id} {friendly_name} ({tomorrow_str}): {val} F")
                        
        except Exception as e:
            logger.error(f"Failed usage Open-Meteo for {station.id}: {e}")

def parse_duration(pt_string):
    if not pt_string.startswith("PT"): return timedelta(0)
    try:
        val = int(pt_string[2:-1])
        unit = pt_string[-1]
        if unit == 'H': return timedelta(hours=val)
        if unit == 'M': return timedelta(minutes=val)
    except:
        pass
    return timedelta(0)

def fetch_nws_temp():
    """
    Fetches Next Day Max Temp from NWS Gridpoints.
    """
    logger.info("Fetching Temperature from NWS...")
    
    headers = {"User-Agent": "(raincheck-app, contact@example.com)"}
    
    for station_id, station in STATIONS.items():
        try:
            tomorrow_dt, tomorrow_str = get_next_day_date(station)
            
            # 1. Get Points
            points_url = f"https://api.weather.gov/points/{station.lat},{station.lon}"
            r = requests.get(points_url, headers=headers, timeout=10)
            if r.status_code != 200: continue
            
            props = r.json().get('properties', {})
            grid_id = props.get('gridId')
            grid_x = props.get('gridX')
            grid_y = props.get('gridY')
            
            # 2. Get Gridpoints
            grid_url = f"https://api.weather.gov/gridpoints/{grid_id}/{grid_x},{grid_y}"
            r = requests.get(grid_url, headers=headers, timeout=10)
            if r.status_code != 200: continue
            
            data = r.json().get('properties', {})
            
            # Check unit
            temp_uom = data.get("temperature", {}).get("uom", "wmoUnit:degC")
            
            # maxTemperature
            max_temp_data = data.get("maxTemperature", {}).get("values", [])
            
            found_val = None
            
            # Find the value that covers "Tomorrow"
            # NWS MaxT usually is a 12-hour or 24-hour block?
            # We want the Max T for the calendar day of Tomorrow.
            # Gridpoints usually gives "Daily Max" valid for a specific window (e.g. 7am - 7pm).
            
            # We look for a validTime that *starts* on Tomorrow's date (local).
            # The validTime is ISO8601 (often with offset).
            
            tz = pytz.timezone(station.timezone)
            tomorrow_start = datetime.strptime(tomorrow_str, "%Y-%m-%d").replace(tzinfo=tz)
            tomorrow_end = tomorrow_start + timedelta(days=1)
            
            for item in max_temp_data:
                vt_str = item['validTime'].split('/')[0]
                # parse ISO
                dt = datetime.fromisoformat(vt_str)
                
                # Compare
                # If dt is within [tomorrow_start, tomorrow_end)
                if tomorrow_start <= dt < tomorrow_end:
                    val = item['value']
                    # Convert to F
                    if "degC" in temp_uom:
                        val = (val * 9/5) + 32
                    
                    found_val = val
                    break
            
            if found_val is not None:
                save_temperature_forecast(
                    location_id=station.id,
                    target_date=tomorrow_str,
                    model_name="NWS",
                    forecast_value=found_val
                )
                logger.info(f"{station.id} NWS ({tomorrow_str}): {found_val:.1f} F")
                
        except Exception as e:
            logger.error(f"Failed NWS for {station.id}: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--forecast", action="store_true", help="Run forecast ingestion")
    parser.add_argument("--verify", action="store_true", help="Run verification (update observations)")
    args = parser.parse_args()
    
    # If no args, maybe run both? Or default to forecast? 
    # Let's run based on args.
    
    if args.forecast:
        fetch_open_meteo_temp()
        fetch_nws_temp()
        
    if args.verify:
        update_observed_temperature() # Updates "Yesterday"
        
    if not args.forecast and not args.verify:
         print("Usage: --forecast or --verify")
