from pydantic import BaseModel
from typing import Dict, List, Optional
from pathlib import Path
import os

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent # rain_forecast/
BACKEND_DIR = BASE_DIR / "backend"
DATA_DIR = BACKEND_DIR / "data"
# Allow override via ENV for Docker
env_db = os.getenv("DB_PATH")
DB_PATH = Path(env_db) if env_db else (DATA_DIR / "raincheck.db")

class Station(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    kalshi_ticker: str
    kalshi_temp_ticker: Optional[str] = None      # High temp ticker (KXHIGH...)
    kalshi_low_temp_ticker: Optional[str] = None  # Low temp ticker (KXLOW...)
    nws_station_id: str
    wfo_id: str
    timezone: str

# Station Configuration
STATIONS: Dict[str, Station] = {
    "NYC": Station(
        id="KNYC", 
        name="Central Park, NY", 
        lat=40.7829, 
        lon=-73.9654, 
        kalshi_ticker="KXRAINNYCM", 
        kalshi_temp_ticker="KXHIGHNY",
        kalshi_low_temp_ticker="KXLOWTNY",
        nws_station_id="NYC",
        wfo_id="OKX",
        timezone="America/New_York"
    ),
    "CLILAX": Station(
        id="KLAX",
        name="Los Angeles (KLAX), CA",
        lat=33.93816, 
        lon=-118.3866,
        kalshi_ticker="KXRAINLAXM", 
        kalshi_temp_ticker="KXHIGHLAX",
        kalshi_low_temp_ticker="KXLOWTLAX",
        nws_station_id="LAX",
        wfo_id="LOX",
        timezone="America/Los_Angeles"
    ),
    "MIA": Station(
        id="KMIA",
        name="Miami International Airport, FL",
        lat=25.7932,
        lon=-80.2906,
        kalshi_ticker="KXRAINMIAM",
        kalshi_temp_ticker="KXHIGHMIA",
        kalshi_low_temp_ticker="KXLOWTMIA",
        nws_station_id="MIA",
        wfo_id="MFL",
        timezone="America/New_York"
    ),
    "CHI": Station(
        id="KMDW",
        name="Chicago Midway, IL",
        lat=41.7868,
        lon=-87.7522,
        kalshi_ticker="KXRAINCHIM",
        kalshi_temp_ticker="KXHIGHCHI",
        kalshi_low_temp_ticker="KXLOWTCHI",
        nws_station_id="MDW",
        wfo_id="LOT",
        timezone="America/Chicago"
    ),
    "SFO": Station(
        id="KSFO",
        name="San Francisco International Airport, CA",
        lat=37.6188,
        lon=-122.3754,
        kalshi_ticker="KXRAINSFOM", 
        kalshi_temp_ticker="KXHIGHTSFO",
        kalshi_low_temp_ticker="KXLOWTTSFO",
        nws_station_id="SFO",
        wfo_id="MTR",
        timezone="America/Los_Angeles"
    ),
    "HOU": Station(
        id="KHOU",
        name="HOUSTON/HOBBY AIRPORT, TX",
        lat=29.652400000000057,
        lon=-95.27722999999997,
        kalshi_ticker="KXRAINHOUM", 
        kalshi_temp_ticker="KXHIGHHOU",
        kalshi_low_temp_ticker="KXLOWTHOU",
        nws_station_id="HOU",
        wfo_id="NWS",
        timezone="America/Chicago"
    ),
    "SEA": Station(
        id="KSEA",
        name="Seattle-Tacoma International Airport, WA",
        lat=47.4502,
        lon=-122.3088,
        kalshi_ticker="KXRAINSEAM", 
        kalshi_temp_ticker="KXHIGHTSEA",
        kalshi_low_temp_ticker="KXLOWTTSEA",
        nws_station_id="SEA",
        wfo_id="SEW",
        timezone="America/Los_Angeles"
    ),
    "AUS": Station(
        id="KAUS",
        name="Austin-Bergstrom International Airport, TX",
        lat=30.18,
        lon=-97.68,
        kalshi_ticker="KXRAINAUSM", 
        kalshi_temp_ticker="KXHIGHAUS",
        kalshi_low_temp_ticker="KXLOWTAUS",
        nws_station_id="AUS",
        wfo_id="EWX",
        timezone="America/Chicago"
    ),
    "DFW": Station(
        id="KDFW",
        name="Dallas/Fort Worth International Airport, TX",
        lat=32.8998,
        lon=-97.0403,
        kalshi_ticker="KXRAINDALM", 
        kalshi_temp_ticker="KXHIGHDAL",
        kalshi_low_temp_ticker="KXLOWTDAL",
        nws_station_id="DFW",
        wfo_id="FWD",
        timezone="America/Chicago"
    ),
    "DEN": Station(
        id="KDEN",
        name="Denver International Airport, CO",
        lat=39.8561,
        lon=-104.6737,
        kalshi_ticker="KXRAINDENM", 
        kalshi_temp_ticker="KXHIGHDEN",
        kalshi_low_temp_ticker="KXLOWTDEN",
        nws_station_id="DEN",
        wfo_id="BOU",
        timezone="America/Denver"
    )
}

# Open-Meteo API Configurations
MODELS = {
    "GFS": "gfs_seamless",
    "ECMWF IFS": "ecmwf_ifs",
    "ECMWF IFS 0.25": "ecmwf_ifs025",
    "ECMWF AIFS": "ecmwf_aifs025_single",
    "NBM CONUS": "ncep_nbm_conus",
    "GFS Global": "gfs_global",
    "NAM": "nam_us",
    "HRRR": "hrrr_us",
    "ICON": "icon_seamless",
    "GEM": "gem_global"
}
