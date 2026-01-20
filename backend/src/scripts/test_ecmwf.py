import requests
import json
from datetime import datetime

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

def test_models():
    params = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "hourly": "precipitation",
        "models": "ecmwf_ifs04,ecmwf_aifs025",
        "forecast_days": 3,
        "precipitation_unit": "inch",
        "timezone": "UTC"
    }
    
    print("Testing Open-Meteo API for IFS and AIFS...")
    try:
        r = requests.get(OPEN_METEO_URL, params=params)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            hourly = data.get('hourly', {})
            print("Keys in hourly:", list(hourly.keys()))
            
            for key, val in hourly.items():
                if "precipitation" in key:
                    total = sum(v for v in val if v is not None)
                    print(f"{key} Total (3 days): {total}")
                    print(f"{key} First 5 values: {val[:5]}")
        else:
            print(r.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_models()
