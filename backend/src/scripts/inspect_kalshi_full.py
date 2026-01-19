import requests
import json

KALSHI_API_URL = "https://api.elections.kalshi.com/trade-api/v2/markets"

def inspect_kalshi():
    ticker = "KXRAINNYCM" 
    print(f"Testing Kalshi API for {ticker}...")
    
    params = {
        "series_ticker": ticker,
        "limit": 5,
        "status": "open"
    }
    
    try:
        r = requests.get(KALSHI_API_URL, params=params)
        if r.status_code == 200:
            data = r.json()
            markets = data.get('markets', [])
            if markets:
                print("First Market Object:")
                print(json.dumps(markets[0], indent=2))
                
                # Check specifics for differentiation
                for m in markets:
                     print(f"Ticker: {m['ticker']}")
                     print(f"Title: {m.get('title')}")
                     print(f"Subtitle: {m.get('subtitle')}")
                     print(f"Floor Strike: {m.get('floor_strike')}")
                     print(f"Cap Strike: {m.get('cap_strike')}")
                     print(f"Custom Strike: {m.get('custom_strike')}")
                     print("---")
            else:
                print("No markets found.")
        else:
            print(f"Error: {r.status_code} {r.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_kalshi()
