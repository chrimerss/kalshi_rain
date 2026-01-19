import requests
import json

def test_nws_api():
    # NYC Central Park
    lat, lon = 40.7829, -73.9654
    headers = {"User-Agent": "(raincheck-app, contact@example.com)"}
    
    # 1. Get Grid Points
    points_url = f"https://api.weather.gov/points/{lat},{lon}"
    print(f"Fetching points: {points_url}")
    r = requests.get(points_url, headers=headers)
    if r.status_code != 200:
        print(f"Error fetching points: {r.text}")
        return
    
    points_data = r.json()
    props = points_data.get('properties', {})
    grid_id = props.get('gridId')
    grid_x = props.get('gridX')
    grid_y = props.get('gridY')
    forecast_hourly_url = props.get('forecastHourly')
    
    print(f"Grid: {grid_id} ({grid_x}, {grid_y})")
    print(f"Forecast Hourly URL: {forecast_hourly_url}")
    
    # 2. Get Gridpoints Data (Raw)
    gridpoints_url = f"https://api.weather.gov/gridpoints/{grid_id}/{grid_x},{grid_y}"
    print(f"Fetching gridpoints: {gridpoints_url}")
    
    r = requests.get(gridpoints_url, headers=headers)
    if r.status_code != 200:
        print(f"Error fetching gridpoints: {r.text}")
        return
        
    grid_data = r.json()
    props = grid_data.get('properties', {})
    qpf = props.get('quantitativePrecipitation', {})
    
    print("Quantitative Precipitation:")
    print(json.dumps(qpf, indent=2))


if __name__ == "__main__":
    test_nws_api()
