import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
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

def _find_temperature_section(html_content: bytes) -> Optional[str]:
    """Finds the TEMPERATURE section in CLI HTML content."""
    soup = BeautifulSoup(html_content, "html.parser")
    pre_tags = soup.find_all("pre")
    
    for pre in pre_tags:
        if pre.text and ("TEMPERATURE (F)" in pre.text or "TEMPERATURE" in pre.text):
            return pre.text
    return None


def _parse_temp_line(lines: list, keyword: str) -> Optional[float]:
    """Parse temperature value from a line containing the keyword (MAXIMUM or MINIMUM)."""
    for line in lines:
        if keyword in line:
            parts = line.split()
            for part in parts[1:]:
                if part == keyword:
                    continue
                try:
                    return float(part)
                except ValueError:
                    continue
    return None


def parse_max_temperature(html_content: bytes) -> Optional[float]:
    """Parses the Maximum Temperature from CLI HTML content."""
    temp_section = _find_temperature_section(html_content)
    if not temp_section:
        logger.warning("Could not find TEMPERATURE section in CLI product")
        return None
    
    lines = temp_section.split('\n')
    return _parse_temp_line(lines, "MAXIMUM")


def parse_min_temperature(html_content: bytes) -> Optional[float]:
    """Parses the Minimum Temperature from CLI HTML content."""
    temp_section = _find_temperature_section(html_content)
    if not temp_section:
        logger.warning("Could not find TEMPERATURE section in CLI product")
        return None
    
    lines = temp_section.split('\n')
    return _parse_temp_line(lines, "MINIMUM")

def update_observed_temperature(target_date_str: Optional[str] = None):
    """
    Updates observed high and low temperature for ALL stations.
    If target_date_str is None, uses 'Today' in station's local time.
    This aligns with verifying today's forecast at 6 PM MST.
    """
    from .db import update_temperature_observation
    import pytz
    
    for station_code, station in STATIONS.items():
        logger.info(f"Scraping Temp for {station.name} ({station.id})...")
        content = fetch_cli_product(station)
        if not content:
            continue
            
        # Determine target date in station's timezone
        try:
            tz = pytz.timezone(station.timezone)
            now_local = datetime.now(tz)
            target_date = now_local.strftime("%Y-%m-%d")
            
            if target_date_str and target_date_str != target_date:
                logger.warning(f"CLI verification uses today's date ({target_date}), but {target_date_str} requested.")
                continue
        except Exception as e:
            logger.error(f"Error determining date for {station.id}: {e}")
            continue
        
        # Parse and save high temperature
        max_temp = parse_max_temperature(content)
        if max_temp is not None:
            logger.info(f"Found Max Temp (HIGH) for {station.id} ({target_date}): {max_temp}")
            try:
                update_temperature_observation(
                    location_id=station.id,
                    target_date=target_date,
                    observed_value=max_temp,
                    forecast_type='high'
                )
            except Exception as e:
                logger.error(f"Error saving HIGH temp for {station.id}: {e}")
        else:
            logger.warning(f"Could not parse Max Temp for {station.id}")
        
        # Parse and save low temperature
        min_temp = parse_min_temperature(content)
        if min_temp is not None:
            logger.info(f"Found Min Temp (LOW) for {station.id} ({target_date}): {min_temp}")
            try:
                update_temperature_observation(
                    location_id=station.id,
                    target_date=target_date,
                    observed_value=min_temp,
                    forecast_type='low'
                )
            except Exception as e:
                logger.error(f"Error saving LOW temp for {station.id}: {e}")
        else:
            logger.warning(f"Could not parse Min Temp for {station.id}")

if __name__ == "__main__":
    update_observed_precipitation()
