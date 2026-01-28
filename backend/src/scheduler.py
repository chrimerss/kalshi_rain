import time
import subprocess
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = BASE_DIR / "backend"
PYTHON_EXEC = sys.executable

def run_ingest():
    logger.info("Running Ingest API...")
    try:
        subprocess.run([PYTHON_EXEC, str(BACKEND_DIR / "src/ingest_api.py")], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Ingest API failed: {e}")

def run_kalshi():
    logger.info("Running Kalshi Market Ingestion...")
    try:
        subprocess.run([PYTHON_EXEC, str(BACKEND_DIR / "src/kalshi.py")], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Kalshi failed: {e}")

def run_scraper():
    logger.info("Running NWS Scraper...")
    try:
        subprocess.run([PYTHON_EXEC, "-m", "backend.src.scraper"], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"NWS scraper failed: {e}")

def run_temperature_forecast():
    """
    Fetches temperature forecasts from Open-Meteo and NWS.
    Target date logic (based on MST):
    - Before 6 PM MST: forecast TODAY's temperature
    - After 6 PM MST: forecast TOMORROW's temperature
    """
    logger.info("Running Temperature Forecast Ingestion...")
    try:
        subprocess.run([PYTHON_EXEC, "-m", "backend.src.ingest_temperature", "--forecast"], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Temperature forecast failed: {e}")

def run_temperature_verify():
    logger.info("Running Temperature Verification...")
    try:
        subprocess.run([PYTHON_EXEC, "-m", "backend.src.ingest_temperature", "--verify"], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Temperature verification failed: {e}")

def get_next_8pm_run() -> datetime:
    """Get next 8 PM MST time for scraping and verification."""
    mst_tz = ZoneInfo("America/Denver")
    now_mst = datetime.now(mst_tz)
    target = now_mst.replace(hour=20, minute=0, second=0, microsecond=0)
    if now_mst >= target:
        target = target + timedelta(days=1)
    return target

def run_8pm_rollover():
    """
    Daily rollover at 8 PM MST:
    1. Run scraper to get today's observed temps from NWS CLI reports
       (pushed to 8 PM because some stations don't update by 6 PM)
    2. Verify today's observed temps against yesterday's 6 PM forecast
    3. Update Kalshi markets
    """
    run_scraper()
    run_temperature_verify()
    run_kalshi()

if __name__ == "__main__":
    logger.info("Starting Scheduler...")
    
    # Run immediately on startup
    run_kalshi()
    run_ingest()
    run_scraper()
    run_temperature_forecast()
    
    last_ingest_time = time.time()
    last_temp_forecast_time = time.time()
    next_8pm_run = get_next_8pm_run()
    
    while True:
        current_time = time.time()
        
        # Run Kalshi every minute
        run_kalshi()
        
        # Run Ingest (rain forecast) every 6 hours (6 * 3600 seconds)
        if current_time - last_ingest_time > 6 * 3600:
            run_ingest()
            last_ingest_time = current_time

        # Run temperature forecast every hour (3600 seconds)
        # Target date switches from today to tomorrow at 8 PM MST
        if current_time - last_temp_forecast_time > 3600:
            run_temperature_forecast()
            last_temp_forecast_time = current_time

        # Daily 8 PM MST: scrape observed temps and verify against yesterday's forecast
        if datetime.now(ZoneInfo("America/Denver")) >= next_8pm_run:
            run_8pm_rollover()
            next_8pm_run = get_next_8pm_run()
            
        # Sleep for 60 seconds
        time.sleep(60)
