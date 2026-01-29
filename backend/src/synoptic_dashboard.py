"""
Dash Plotly dashboard for real-time temperature observations from Synoptic API.
"""

import requests
import logging
from datetime import datetime, timedelta
from dash import Dash, html, dcc, Output, Input, State
import plotly.graph_objects as go
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.src.db import (
    init_db, 
    save_synoptic_observation, 
    get_synoptic_observations,
    clear_old_synoptic_observations
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Synoptic API Configuration
SYNOPTIC_API_URL = "https://api.synopticdata.com/v2/stations/timeseries"

# Read token from .token file (not committed to git)
def _load_token():
    """Load Synoptic API token from .token file."""
    token_paths = [
        Path(__file__).resolve().parent.parent.parent / ".token",  # /app/.token in container
        Path("/app/.token"),  # Docker mount path
        Path.home() / "kalshi_rain" / ".token",  # Local development
    ]
    for token_path in token_paths:
        if token_path.exists():
            with open(token_path, 'r') as f:
                return f.read().strip()
    logger.warning("No .token file found, using empty token")
    return ""

SYNOPTIC_TOKEN = _load_token()

# Station configuration (with lat/lon for Open-Meteo forecast)
STATIONS = {
    "KNYC": {"name": "NYC (Central Park)", "timezone": "America/New_York", "lat": 40.7829, "lon": -73.9654},
    "KLAX": {"name": "Los Angeles International Airport", "timezone": "America/Los_Angeles", "lat": 33.93806, "lon": -118.38889},
    "KMIA": {"name": "Miami International Airport", "timezone": "America/New_York", "lat": 25.7932, "lon": -80.2906},
    "KMDW": {"name": "Chicago Midway", "timezone": "America/Chicago", "lat": 41.7868, "lon": -87.7522},
    "KSFO": {"name": "San Francisco International Airport", "timezone": "America/Los_Angeles", "lat": 37.6188, "lon": -122.3754},
    "KSEA": {"name": "Seattle-Tacoma International Airport", "timezone": "America/Los_Angeles", "lat": 47.44472, "lon": -122.31361},
    "KAUS": {"name": "Austin-Bergstrom International Airport", "timezone": "America/Chicago", "lat": 30.18, "lon": -97.68},
    "KDEN": {"name": "Denver International Airport", "timezone": "America/Denver", "lat": 39.8561, "lon": -104.6737},
    "KDCA": {"name": "Washington DC (Reagan National)", "timezone": "America/New_York", "lat": 38.84833, "lon": -77.03417},
    "KPHL": {"name": "Philadelphia International Airport", "timezone": "America/New_York", "lat": 39.87327, "lon": -75.22678},
    "KMSY": {"name": "New Orleans International Airport", "timezone": "America/Chicago", "lat": 29.99278, "lon": -90.25083},
    "KLAS": {"name": "Las Vegas (McCarran)", "timezone": "America/Los_Angeles", "lat": 36.07188, "lon": -115.16340},
}

# Open-Meteo 15-minute forecast API
OPENMETEO_API_URL = "https://api.open-meteo.com/v1/forecast"


def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit: F = C * 9/5 + 32"""
    return celsius * 9.0 / 5.0 + 32.0


def fetch_openmeteo_forecast(lat: float, lon: float, timezone: str) -> dict:
    """
    Fetch hourly temperature forecast from Open-Meteo API for next 24 hours.
    
    Args:
        lat: Latitude
        lon: Longitude
        timezone: Timezone string (e.g., 'America/Los_Angeles')
    
    Returns:
        Dictionary with 'times' and 'temps_celsius' lists
    """
    import pytz
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m",
        "forecast_days": 1,
        "timezone": timezone,
    }
    
    try:
        response = requests.get(OPENMETEO_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        
        if not times or not temps:
            logger.warning(f"No forecast data from Open-Meteo for lat={lat}, lon={lon}")
            return {"times": [], "temps_celsius": []}
        
        # Convert times to match Synoptic format (with timezone offset)
        tz = pytz.timezone(timezone)
        formatted_times = []
        for t in times:
            # Parse the time (Open-Meteo returns "2026-01-28T00:00")
            dt = datetime.strptime(t, "%Y-%m-%dT%H:%M")
            # Localize to the station timezone
            dt_local = tz.localize(dt)
            # Format with timezone offset to match Synoptic
            formatted_times.append(dt_local.strftime("%Y-%m-%dT%H:%M:%S%z"))
        
        return {"times": formatted_times, "temps_celsius": temps}
        
    except Exception as e:
        logger.error(f"Failed to fetch Open-Meteo forecast: {e}")
        return {"times": [], "temps_celsius": []}


def fetch_synoptic_data(station_id: str, recent_minutes: int = 1440) -> dict:
    """
    Fetch temperature time series from Synoptic API in Celsius.
    
    Args:
        station_id: Station ID (e.g., 'KSEA')
        recent_minutes: Number of minutes of recent data to fetch
    
    Returns:
        Dictionary with 'times' and 'temps_celsius' lists (temperatures in Celsius)
    """
    params = {
        "stid": station_id,
        "recent": recent_minutes,
        "vars": "air_temp",
        "token": SYNOPTIC_TOKEN,
        "units": "metric",  # Request Celsius
        "obtimezone": "local",
    }
    
    try:
        response = requests.get(SYNOPTIC_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get("SUMMARY", {}).get("RESPONSE_CODE") != 1:
            logger.error(f"Synoptic API error: {data.get('SUMMARY', {}).get('RESPONSE_MESSAGE')}")
            return {"times": [], "temps_celsius": []}
        
        stations = data.get("STATION", [])
        if not stations:
            logger.warning(f"No data returned for station {station_id}")
            return {"times": [], "temps_celsius": []}
        
        obs = stations[0].get("OBSERVATIONS", {})
        times = obs.get("date_time", [])
        
        # Find air_temp key (may have suffix like _set_1)
        temp_key = None
        for key in obs.keys():
            if key.startswith("air_temp"):
                temp_key = key
                break
        
        if not temp_key:
            logger.warning(f"No air_temp data for station {station_id}")
            return {"times": [], "temps_celsius": []}
        
        temps_celsius = obs.get(temp_key, [])
        
        return {"times": times, "temps_celsius": temps_celsius}
        
    except Exception as e:
        logger.error(f"Failed to fetch Synoptic data for {station_id}: {e}")
        return {"times": [], "temps_celsius": []}


def store_synoptic_data(station_id: str, times: list, temps_celsius: list):
    """Store synoptic observations in database (store in Fahrenheit for consistency)."""
    for t, temp_c in zip(times, temps_celsius):
        if temp_c is not None:
            temp_f = celsius_to_fahrenheit(temp_c)
            save_synoptic_observation(station_id, t, temp_f)
    
    # Clean up old data (keep 48 hours)
    clear_old_synoptic_observations(station_id, keep_hours=48)


# Initialize database
init_db()

# Create Dash app
app = Dash(__name__, url_base_pathname='/obs/')

app.layout = html.Div([
    # URL location component for reading query parameters
    dcc.Location(id='url', refresh=False),
    
    html.H1("Real-Time Temperature Observations", 
            style={'textAlign': 'center', 'color': '#1e3a5f', 'marginBottom': '10px'}),
    
    html.Div([
        html.Label("Station: ", style={'fontWeight': 'bold', 'marginRight': '10px'}),
        dcc.Dropdown(
            id='station-dropdown',
            options=[{'label': f"{v['name']} ({k})", 'value': k} for k, v in STATIONS.items()],
            value='KSEA',  # Default, will be overridden by URL param
            style={'width': '400px', 'display': 'inline-block'}
        ),
        html.Label("  Time Range: ", style={'fontWeight': 'bold', 'marginLeft': '30px', 'marginRight': '10px'}),
        dcc.Dropdown(
            id='time-dropdown',
            options=[
                {'label': 'Last 1 Hour', 'value': 60},
                {'label': 'Last 6 Hours', 'value': 360},
                {'label': 'Last 12 Hours', 'value': 720},
                {'label': 'Last 24 Hours', 'value': 1440},
            ],
            value=1440,
            style={'width': '200px', 'display': 'inline-block'}
        ),
        html.Label("  Unit: ", style={'fontWeight': 'bold', 'marginLeft': '30px', 'marginRight': '10px'}),
        dcc.RadioItems(
            id='unit-toggle',
            options=[
                {'label': ' °F', 'value': 'F'},
                {'label': ' °C', 'value': 'C'},
            ],
            value='F',
            inline=True,
            style={'display': 'inline-block'},
            inputStyle={'marginRight': '5px'},
            labelStyle={'marginRight': '15px', 'fontWeight': 'normal'}
        ),
    ], style={'textAlign': 'center', 'marginBottom': '20px'}),
    
    dcc.Graph(id='temp-graph', style={'height': '500px'}),
    
    html.Div(id='last-update', style={'textAlign': 'center', 'color': '#666', 'marginTop': '10px'}),
    
    # Store for tracking last observation time
    dcc.Store(id='last-obs-time', data=''),
    
    # Check for new data every 1 minute
    dcc.Interval(
        id='interval-component',
        interval=60*1000,  # 1 minute in milliseconds
        n_intervals=0
    ),
    
    html.Div([
        html.A("← Back to Temperature Forecast", href="/forecast/temperature",
               style={'color': '#3b82f6', 'textDecoration': 'none', 'fontSize': '14px'})
    ], style={'textAlign': 'center', 'marginTop': '20px'}),
    
], style={'fontFamily': 'Arial, sans-serif', 'maxWidth': '1200px', 'margin': '0 auto', 'padding': '20px'})


@app.callback(
    Output('station-dropdown', 'value'),
    Input('url', 'search'),
    prevent_initial_call=False
)
def set_station_from_url(search):
    """Set station dropdown value from URL query parameter."""
    from urllib.parse import parse_qs
    
    if search:
        # Parse query string (e.g., "?station=KDCA")
        params = parse_qs(search.lstrip('?'))
        station = params.get('station', [None])[0]
        if station and station in STATIONS:
            return station
    
    # Default to first station in list
    return list(STATIONS.keys())[0]


@app.callback(
    Output('temp-graph', 'figure'),
    Output('last-update', 'children'),
    Output('last-obs-time', 'data'),
    Input('station-dropdown', 'value'),
    Input('time-dropdown', 'value'),
    Input('unit-toggle', 'value'),
    Input('interval-component', 'n_intervals'),
    State('last-obs-time', 'data')
)
def update_graph(station_id, time_range, unit, n_intervals, last_obs_time):
    """Update the temperature graph when new observation is available."""
    
    # Fetch fresh data from Synoptic API (returns Celsius)
    data = fetch_synoptic_data(station_id, recent_minutes=time_range)
    
    # Fetch Open-Meteo 15-minute forecast
    station_info = STATIONS.get(station_id, {})
    forecast_data = fetch_openmeteo_forecast(
        station_info.get("lat", 0),
        station_info.get("lon", 0),
        station_info.get("timezone", "UTC")
    )
    
    # Get latest observation time
    latest_obs_time = data["times"][-1] if data["times"] else ""
    is_new_data = latest_obs_time != last_obs_time and latest_obs_time != ""
    
    # Store in database (converts to F internally)
    if data["times"] and data["temps_celsius"]:
        store_synoptic_data(station_id, data["times"], data["temps_celsius"])
    
    # Create figure
    fig = go.Figure()
    
    # Add Open-Meteo forecast line (light gray, behind observation)
    if forecast_data["times"] and forecast_data["temps_celsius"]:
        forecast_valid = []
        for t, temp_c in zip(forecast_data["times"], forecast_data["temps_celsius"]):
            if temp_c is not None:
                if unit == 'F':
                    temp_display = celsius_to_fahrenheit(temp_c)
                else:
                    temp_display = temp_c
                forecast_valid.append((t, temp_display))
        
        if forecast_valid:
            fc_times, fc_temps = zip(*forecast_valid)
            fig.add_trace(go.Scatter(
                x=fc_times,
                y=fc_temps,
                mode='lines',
                name='Forecast (Open-Meteo)',
                line=dict(color='#9ca3af', width=2, dash='dot'),  # Light gray, dotted
                hovertemplate=f'%{{x}}<br>Forecast: %{{y:.2f}}°{unit}<extra></extra>'
            ))
    
    # Add observation data (on top of forecast)
    if data["times"] and data["temps_celsius"]:
        # Filter out None values and convert based on selected unit
        valid_data = []
        for t, temp_c in zip(data["times"], data["temps_celsius"]):
            if temp_c is not None:
                if unit == 'F':
                    temp_display = celsius_to_fahrenheit(temp_c)
                else:
                    temp_display = temp_c
                valid_data.append((t, temp_display))
        
        if valid_data:
            times, temps = zip(*valid_data)
            
            # Color based on unit (red for F, blue for C)
            line_color = '#ef4444' if unit == 'F' else '#3b82f6'
            fill_color = 'rgba(239, 68, 68, 0.1)' if unit == 'F' else 'rgba(59, 130, 246, 0.1)'
            
            fig.add_trace(go.Scatter(
                x=times,
                y=temps,
                mode='lines',
                name='Observed (Synoptic)',
                line=dict(color=line_color, width=2),
                fill='tozeroy',
                fillcolor=fill_color,
                hovertemplate=f'%{{x}}<br>Observed: %{{y:.2f}}°{unit}<extra></extra>'
            ))
            
            # Add current temp annotation with 2 decimal precision
            current_temp = temps[-1] if temps else None
            if current_temp:
                fig.add_annotation(
                    x=times[-1],
                    y=current_temp,
                    text=f"<b>{current_temp:.2f}°{unit}</b>",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor=line_color,
                    font=dict(size=14, color=line_color),
                    bgcolor="white",
                    bordercolor=line_color,
                    borderwidth=1,
                    borderpad=4
                )
    
    station_name = STATIONS.get(station_id, {}).get('name', station_id)
    unit_label = "Fahrenheit" if unit == 'F' else "Celsius"
    
    fig.update_layout(
        title=dict(
            text=f"Temperature at {station_name}",
            font=dict(size=18, color='#1e3a5f')
        ),
        xaxis=dict(
            title="Time (Local)",
            showgrid=True,
            gridcolor='rgba(0,0,0,0.1)'
        ),
        yaxis=dict(
            title=f"Temperature (°{unit})",
            showgrid=True,
            gridcolor='rgba(0,0,0,0.1)'
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='x unified',
        margin=dict(l=60, r=40, t=60, b=60),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Status message with new data indicator
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_indicator = " | 🟢 NEW DATA" if is_new_data else ""
    last_update = f"Last checked: {now_str} | Latest obs: {latest_obs_time} | Points: {len(data['times'])} | {unit_label}{new_indicator}"
    
    return fig, last_update, latest_obs_time


# For running standalone
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8050, debug=False)
