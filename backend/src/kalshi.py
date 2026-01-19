import requests
import logging
import sys
from pathlib import Path
from datetime import datetime
import time

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.src.config import STATIONS
from backend.src.db import save_market_data, init_db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

KALSHI_API_URL = "https://api.elections.kalshi.com/trade-api/v2/markets"

def fetch_kalshi_markets():
    logger.info("Starting Kalshi Market Ingestion...")
    
    # Initialize DB (creates table if not exists)
    init_db()
    
    for station_id, station in STATIONS.items():
        time.sleep(0.2) # Rate limiting
        ticker = station.kalshi_ticker
        if not ticker:
            continue
            
        logger.info(f"Fetching markets for {station.name} ({ticker})...")
        
        try:
            params = {
                "series_ticker": ticker,
                "limit": 100,
                "status": "open" # Only want active trading markets
            }
            
            response = requests.get(KALSHI_API_URL, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                markets = data.get('markets', [])
                
                logger.info(f"Found {len(markets)} markets for {ticker}.")
                
                for m in markets:
                    # m keys: ticker, title, yes_bid, no_bid, status, etc.
                    # We want to display "Threshold" and "Prices"
                    # The title usually contains the info, e.g. "Rain in NYC in Jan 2026?"
                    # But the subtitle or other fields might specify ">1 inch".
                    # Let's verify 'subtitle' or 'cap_strike' if available?
                    # In my test output: "Rain in NYC in Jan 2026?" was the title.
                    # The different markets were differentiated by ticker: ...-26JAN-1, ...-26JAN-2.
                    # This implies the suffix is the threshold.
                    # We might need to parse the threshold from the ticker or subtitle.
                    # For now, let's save the 'subtitle' if it exists, or just the ticker.
                    
                    market_ticker = m.get('ticker')
                    title = m.get('title')
                    subtitle = m.get('subtitle', '') 
                    yes_sub = m.get('yes_sub_title', '')
                    yes_price = m.get('yes_bid', 0)
                    no_price = m.get('no_bid', 0)
                    status = m.get('status')
                    
                    # Construct a display title
                    # Prefer "Above X inches" (yes_sub_title)
                    if yes_sub:
                        display_title = yes_sub
                    elif subtitle:
                        display_title = subtitle
                    else:
                        display_title = title
                    
                    save_market_data(
                        ticker=market_ticker,
                        location_id=station.id, # Map back to our Station ID (KNYC, etc)
                        title=display_title,
                        yes_price=yes_price,
                        no_price=no_price,
                        status=status
                    )
            else:
                logger.error(f"Failed to fetch {ticker}: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Error fetching {ticker}: {e}")

if __name__ == "__main__":
    fetch_kalshi_markets()
