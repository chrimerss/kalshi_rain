import requests
import json
from datetime import datetime

KALSHI_API_URL = "https://api.elections.kalshi.com/trade-api/v2"

def test_kalshi_public():
    # Try to fetch markets without auth
    # Endpoint: /markets
    # Filter by series_ticker if possible?
    
    # Example Ticker: KXRAINNYC (Base ticker for series?)
    # Config says "KX-RAIN-NYC" but Kalshi usually uses "KXRAINNYC" or similar
    
    ticker = "KXRAINLAM" 
    
    print(f"Testing Kalshi API for {ticker}...")
    
    url = f"{KALSHI_API_URL}/markets"
    params = {
        "series_ticker": ticker,
        "limit": 100,
        "status": "open"
    }
    
    try:
        r = requests.get(url, params=params)
        print(f"Status Code: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            markets = data.get('markets', [])
            print(f"Found {len(markets)} markets.")
            
            for m in markets[:5]:
                print(f"  - {m['ticker']}: {m['title']} (Yes: {m.get('yes_bid')}, No: {m.get('no_bid')})")
        else:
            print(f"Response: {r.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_kalshi_public()
