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
        
        tickers_to_fetch = []
        if station.kalshi_ticker:
            tickers_to_fetch.append(station.kalshi_ticker)
        if station.kalshi_temp_ticker:
            tickers_to_fetch.append(station.kalshi_temp_ticker)
        if station.kalshi_low_temp_ticker:
            tickers_to_fetch.append(station.kalshi_low_temp_ticker)
            
        for ticker in tickers_to_fetch:
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
                        market_ticker = m.get('ticker')
                        title = m.get('title')
                        subtitle = m.get('subtitle', '') 
                        yes_sub = m.get('yes_sub_title', '')
                        yes_ask = m.get('yes_ask', 0) or 0
                        no_ask = m.get('no_ask', 0) or 0

                        # Always store ask prices for display.
                        yes_price = yes_ask
                        no_price = no_ask
                        status = m.get('status')
                        
                        # Parsing Date from Ticker or Title
                        # Expected Ticker format for Daily High: KXHIGHLOC-YYMMMDD-STRIKE
                        # e.g. KXHIGHNYCD-26JAN23-T66
                        
                        target_date_val = None
                        try:
                            parts = market_ticker.split('-')
                            # Iterate parts to find the date
                            for part in parts:
                                # Attempt YYMMMDD (Daily)
                                try:
                                    dt = datetime.strptime(part, "%y%b%d")
                                    target_date_val = dt.strftime("%Y-%m-%d")
                                    break # Found it
                                except ValueError:
                                    pass
                                    
                                # Attempt YYMMM (Monthly)
                                try:
                                    dt = datetime.strptime(part, "%y%b")
                                    target_date_val = dt.strftime("%Y-%m-%01") 
                                    break # Found it
                                except ValueError:
                                    pass
                        except:
                            pass

                        # Construct a display title
                        if yes_sub:
                            display_title = yes_sub
                        elif subtitle:
                            display_title = subtitle
                        else:
                            display_title = title
                        
                        save_market_data(
                            ticker=market_ticker,
                            location_id=station.id,
                            title=display_title,
                            yes_price=yes_price,
                            no_price=no_price,
                            status=status,
                            target_date=target_date_val
                        )
                else:
                    logger.error(f"Failed to fetch {ticker}: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.error(f"Error fetching {ticker}: {e}")

if __name__ == "__main__":
    fetch_kalshi_markets()
