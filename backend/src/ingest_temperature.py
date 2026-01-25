
import requests
import logging
import pytz
from datetime import datetime, timedelta
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

# Models to query
TEMP_MODELS = [
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

MODEL_NAMES_MAP = {
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


def get_next_day_date(station: Station) -> tuple[datetime, str]:
    """Returns (datetime_obj, date_string) for 'Tomorrow' in station's local time."""
    tz = pytz.timezone(station.timezone)
    now_local = datetime.now(tz)
    tomorrow_local = now_local + timedelta(days=1)
    return tomorrow_local, tomorrow_local.strftime("%Y-%m-%d")


def fetch_open_meteo_temp():
    """Fetches Next Day Max and Min Temp from Open-Meteo for all stations."""
    logger.info("Fetching Temperature (High & Low) from Open-Meteo...")
    
    for station_id, station in STATIONS.items():
        tomorrow_dt, tomorrow_str = get_next_day_date(station)
        
        # Request both max and min temperatures
        params = {
            "latitude": station.lat,
            "longitude": station.lon,
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": station.timezone,
            "models": ",".join(TEMP_MODELS),
            "temperature_unit": "fahrenheit",
            "start_date": tomorrow_str,
            "end_date": tomorrow_str 
        }
        
        try:
            r = requests.get(OPEN_METEO_URL, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            daily_data = data.get("daily", {})
            
            for api_model in TEMP_MODELS:
                friendly_name = MODEL_NAMES_MAP.get(api_model, api_model)
                
                # High temperature
                max_key = f"temperature_2m_max_{api_model}"
                if max_key in daily_data:
                    vals = daily_data[max_key]
                    if vals and vals[0] is not None:
                        val = float(vals[0])
                        save_temperature_forecast(
                            location_id=station.id,
                            target_date=tomorrow_str,
                            model_name=friendly_name,
                            forecast_value=val,
                            forecast_type='high'
                        )
                        logger.info(f"{station.id} {friendly_name} HIGH ({tomorrow_str}): {val:.1f} F")
                
                # Low temperature
                min_key = f"temperature_2m_min_{api_model}"
                if min_key in daily_data:
                    vals = daily_data[min_key]
                    if vals and vals[0] is not None:
                        val = float(vals[0])
                        save_temperature_forecast(
                            location_id=station.id,
                            target_date=tomorrow_str,
                            model_name=friendly_name,
                            forecast_value=val,
                            forecast_type='low'
                        )
                        logger.info(f"{station.id} {friendly_name} LOW ({tomorrow_str}): {val:.1f} F")
                        
        except Exception as e:
            logger.error(f"Failed Open-Meteo for {station.id}: {e}")


def fetch_nws_temp():
    """Fetches Next Day Max and Min Temp from NWS Gridpoints."""
    logger.info("Fetching Temperature (High & Low) from NWS...")
    
    headers = {"User-Agent": "(raincheck-app, contact@example.com)"}
    
    for station_id, station in STATIONS.items():
        try:
            tomorrow_dt, tomorrow_str = get_next_day_date(station)
            
            # 1. Get Points
            points_url = f"https://api.weather.gov/points/{station.lat},{station.lon}"
            r = requests.get(points_url, headers=headers, timeout=10)
            if r.status_code != 200: 
                continue
            
            props = r.json().get('properties', {})
            grid_id = props.get('gridId')
            grid_x = props.get('gridX')
            grid_y = props.get('gridY')
            
            # 2. Get Gridpoints
            grid_url = f"https://api.weather.gov/gridpoints/{grid_id}/{grid_x},{grid_y}"
            r = requests.get(grid_url, headers=headers, timeout=10)
            if r.status_code != 200: 
                continue
            
            data = r.json().get('properties', {})
            
            tz = pytz.timezone(station.timezone)
            tomorrow_start = datetime.strptime(tomorrow_str, "%Y-%m-%d").replace(tzinfo=tz)
            tomorrow_end = tomorrow_start + timedelta(days=1)
            
            # Helper to find temperature value for tomorrow
            def find_temp_for_tomorrow(temp_data):
                for item in temp_data:
                    vt_str = item['validTime'].split('/')[0]
                    dt = datetime.fromisoformat(vt_str)
                    if tomorrow_start <= dt < tomorrow_end:
                        val = item['value']
                        if val is None:
                            continue
                        # NWS returns Celsius by default
                        val = (val * 9/5) + 32
                        return val
                return None
            
            # Max Temperature (High)
            max_temp_data = data.get("maxTemperature", {}).get("values", [])
            max_val = find_temp_for_tomorrow(max_temp_data)
            if max_val is not None:
                save_temperature_forecast(
                    location_id=station.id,
                    target_date=tomorrow_str,
                    model_name="NWS",
                    forecast_value=max_val,
                    forecast_type='high'
                )
                logger.info(f"{station.id} NWS HIGH ({tomorrow_str}): {max_val:.1f} F")
            
            # Min Temperature (Low)
            min_temp_data = data.get("minTemperature", {}).get("values", [])
            min_val = find_temp_for_tomorrow(min_temp_data)
            if min_val is not None:
                save_temperature_forecast(
                    location_id=station.id,
                    target_date=tomorrow_str,
                    model_name="NWS",
                    forecast_value=min_val,
                    forecast_type='low'
                )
                logger.info(f"{station.id} NWS LOW ({tomorrow_str}): {min_val:.1f} F")
                
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
