import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from typing import Optional, Tuple
import logging

import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.src.config import STATIONS, Station
from backend.src.db import save_forecast

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_cli_product(station: Station) -> Optional[str]:
    """Fetches the latest CLI product text for a given station."""
    # URL construction based on user example:
    # https://forecast.weather.gov/product.php?site=OKX&issuedby=NYC&product=CLI&format=txt&version=1&glossary=0
    url = f"https://forecast.weather.gov/product.php?site={station.wfo_id}&issuedby={station.nws_station_id}&product=CLI&format=txt&version=1&glossary=0"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        logger.error(f"Failed to fetch CLI for {station.id}: {e}")
        return None

def parse_precipitation(html_content: bytes) -> Optional[float]:
    """Parses the Month-to-Date precipitation from CLI HTML content."""
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Find the pre tag containing the data
    # The user snippet looked for "PRECIPITATION (IN)" inside pre tags
    pre_tags = soup.find_all("pre")
    
    target_pre = None
    for pre in pre_tags:
        if pre.text and ("PRECIPITATION (IN)" in pre.text or "SNOWFALL (IN)" in pre.text):
            target_pre = pre
            break
            
    if not target_pre:
        logger.warning("Could not find PRECIPITATION section in CLI product")
        return None
        
    lines = target_pre.text.split('\n')
    
    # State machine to find the value
    # Looking for "MONTH TO DATE" line, then extracting the value
    # The structure usually aligns column-wise or follows immediately
    # Example:
    # PRECIPITATION (IN)
    #   ...
    #   MONTH TO DATE    5.12
    
    for i, line in enumerate(lines):
        if "MONTH TO DATE" in line:
            # Check if this line belongs to Precipitation section (simple heuristic: look back a few lines?)
            # Actually, the snippet used a section finder.
            # Let's try to extract the last number on the line, or the one corresponding to the column.
            # Typical line: "MONTH TO DATE           T       5.12      -1.23 ... "
            # Columns: Yesterday, Month-to-Date, ...
            # Wait, usually it is: 
            #               YESTERDAY   MONTH TO DATE
            # TOTAL            0.00        1.23
            
            # OR
            # ELEMENT           ...      MONTH TO DATE
            # PRECIPITATION (IN) ...        1.23
            
            # Let's re-examine the user's snippet logic:
            # if 'MONTH TO DATE' in line:
            #     precipitation_month_to_date = float(line.split()[3]) (assuming specific column)
            
            # We need to be careful about columns.
            # Let's assume the value is the token after 'DATE' or near the end.
            
            parts = line.split()
            # parts: ['MONTH', 'TO', 'DATE', 'T', '5.12', ...]
            # The value usually comes after "DATE".
            
            # Let's try to find the first numeric or 'T' value after 'DATE'
            try:
                # Find index of 'DATE'
                date_idx = parts.index('DATE')
                # Look at subsequent tokens
                if date_idx + 1 < len(parts):
                    val_str = parts[date_idx + 1]
                    
                    # Clean the value
                    val_str = val_str.strip()
                    
                    if val_str == 'T':
                        return 0.00
                    
                    # Remove any non-numeric chars except dot (sometimes attached to letters?)
                    # Usually clean.
                    try:
                        return float(val_str)
                    except ValueError:
                        # Maybe next column?
                        if date_idx + 2 < len(parts):
                             val_str = parts[date_idx + 2]
                             if val_str == 'T': return 0.00
                             return float(val_str)
            except ValueError:
                continue
                
    return None

def update_observed_precipitation():
    """Runs the scraper for all stations and updates the DB."""
    for station_code, station in STATIONS.items():
        logger.info(f"Scraping {station.name} ({station.id})...")
        content = fetch_cli_product(station)
        if content:
            mtd_precip = parse_precipitation(content)
            if mtd_precip is not None:
                logger.info(f"Found MTD Precip for {station.id}: {mtd_precip}")
                # Save to DB
                # init_time is now (observation time)
                # forecast_remainder = 0 (since this is observation)
                # But wait, the goal is Total = Observed + Forecast.
                # Here we just save the observed part.
                # We can store it as a 'forecast' with 0 remainder, or handle it differently.
                # The schema has `observed_mtd`.
                # We'll treat this as an update to the 'latest state'.
                
                # Actually, we should probably save a record that represents "Current Observation"
                save_forecast(
                    location_id=station.id,
                    model_name="NWS_CLI",
                    init_time=datetime.utcnow().isoformat(),
                    observed_mtd=mtd_precip,
                    forecast_remainder=0.0,
                    is_partial=False
                )
            else:
                logger.warning(f"Could not parse precip for {station.id}")

if __name__ == "__main__":
    update_observed_precipitation()
