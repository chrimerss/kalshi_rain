import requests
import json

URL = "https://api.open-meteo.com/v1/forecast"

def test_single():
    # User requested: ecmwf_ifs025, ecmwf_aifs025_single, ecmwf_ifs
    # We will test these.
    models_to_test = ["ecmwf_ifs"]
    
    for m in models_to_test:
        print(f"\nTesting {m}...")
        params = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "hourly": "precipitation",
            "models": m,
            "forecast_days": 3,
            "precipitation_unit": "inch",
            "timezone": "UTC"
        }
        try:
            r = requests.get(URL, params=params)
            if r.status_code != 200:
                print(f"Failed: {r.status_code} {r.text}")
                continue
                
            data = r.json()
            hourly = data.get('hourly', {})
            # Key logic: precipitation OR precipitation_modelname
            key = "precipitation"
            if key not in hourly:
                key = f"precipitation_{m}"
            
            vals = hourly.get(key, [])
            print(f"Keys: {list(hourly.keys())}")
            print(f"Head: {vals[:5]}")
            
            # Check for non-null
            non_null = [x for x in vals if x is not None]
            print(f"Non-null count: {len(non_null)}")
            if non_null:
                print(f"Sum: {sum(non_null)}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_single()
