import requests
import pandas as pd
from datetime import datetime

# Open-Meteo URL
URL = "https://api.open-meteo.com/v1/forecast"

def debug_austin():
    # Austin coordinates
    lat = 30.1975
    lon = -97.6664
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation",
        "models": "ecmwf_ifs04,ecmwf_aifs025,gfs_seamless",
        "forecast_days": 14,
        "precipitation_unit": "inch",
        "timezone": "UTC"
    }
    
    print("Fetching Austin Data...")
    r = requests.get(URL, params=params)
    data = r.json()
    
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    
    ifs = hourly.get("precipitation_ecmwf_ifs04", [])
    aifs = hourly.get("precipitation_ecmwf_aifs025", [])
    gfs = hourly.get("precipitation_gfs_seamless", [])
    
    df = pd.DataFrame({
        "time": times,
        "IFS": ifs,
        "AIFS": aifs,
        "GFS": gfs
    })
    
    print("Data Sample (First 10 non-zero GFS?):")
    # Filter where GFS > 0 to see rain events
    rainy = df[df["GFS"] > 0].head(10)
    print(rainy)
    
    print("\nNon-Null Counts:")
    print(df.count())
    
    print("\nSums:")
    print(df[["IFS", "AIFS", "GFS"]].sum())

if __name__ == "__main__":
    debug_austin()
