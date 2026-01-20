from pydantic import BaseModel
from typing import Dict, List, Optional
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent # rain_forecast/
BACKEND_DIR = BASE_DIR / "backend"
DATA_DIR = BACKEND_DIR / "data"
DB_PATH = DATA_DIR / "raincheck.db"

class Station(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    kalshi_ticker: str
    nws_station_id: str
    wfo_id: str

# Station Configuration
STATIONS: Dict[str, Station] = {
    "NYC": Station(
        id="KNYC", 
        name="Central Park, NY", 
        lat=40.7829, 
        lon=-73.9654, 
        kalshi_ticker="KXRAINNYCM", # Verified
        nws_station_id="NYC",
        wfo_id="OKX" 
    ),
    "CLILAX": Station(
        id="KLOX",
        name="Los Angeles (KLOX), CA",
        lat=34.2008, 
        lon=-119.2006,
        kalshi_ticker="KXRAINLAXM", # Assumption: LAX based
        nws_station_id="LAX",
        wfo_id="LOX"
    ),
    "MIA": Station(
        id="KMIA",
        name="Miami International Airport, FL",
        lat=25.7932,
        lon=-80.2906,
        kalshi_ticker="KXRAINMIAM",
        nws_station_id="MIA",
        wfo_id="MFL"
    ),
    "CHI": Station(
        id="KMDW",
        name="Chicago Midway, IL",
        lat=41.7868,
        lon=-87.7522,
        kalshi_ticker="KXRAINCHIM",
        nws_station_id="MDW",
        wfo_id="LOT"
    ),
    "SFO": Station(
        id="KSFO",
        name="San Francisco International Airport, CA",
        lat=37.6188,
        lon=-122.3754,
        kalshi_ticker="KXRAINSFOM", # User provided
        nws_station_id="SFO",
        wfo_id="MTR"
    ),
    "HOU": Station(
        id="KIAH",
        name="Houston Intercontinental, TX",
        lat=29.9844,
        lon=-95.3414,
        kalshi_ticker="KXRAINHOUM", # Assumed pattern
        nws_station_id="IAH",
        wfo_id="HGX"
    ),
    "SEA": Station(
        id="KSEA",
        name="Seattle-Tacoma International Airport, WA",
        lat=47.4502,
        lon=-122.3088,
        kalshi_ticker="KXRAINSEAM", # User provided
        nws_station_id="SEA", # User requested SEA issued product
        wfo_id="SEW"
    ),
    "AUS": Station(
        id="KAUS",
        name="Austin-Bergstrom International Airport, TX",
        lat=30.1975,
        lon=-97.6664,
        kalshi_ticker="KXRAINAUSM", # User provided
        nws_station_id="ATT",
        wfo_id="EWX"
    ),
    "DFW": Station(
        id="KDFW",
        name="Dallas/Fort Worth International Airport, TX",
        lat=32.8998,
        lon=-97.0403,
        kalshi_ticker="KXRAINDALM", # User provided (Dallas)
        nws_station_id="DFW",
        wfo_id="FWD"
    ),
    "DEN": Station(
        id="KDEN",
        name="Denver International Airport, CO",
        lat=39.8561,
        lon=-104.6737,
        kalshi_ticker="KXRAINDENM", # User provided
        nws_station_id="DEN",
        wfo_id="BOU"
    )
}

# Open-Meteo API Configurations
MODELS = {
    "GFS": "gfs_seamless",
    "ECMWF IFS": "ecmwf_ifs",
    "ECMWF IFS 0.25": "ecmwf_ifs025",
    "ECMWF AIFS": "ecmwf_aifs025_single",
    "NAM": "nam_us",
    "HRRR": "hrrr_us",
    "ICON": "icon_seamless",
    "GEM": "gem_global"
}
