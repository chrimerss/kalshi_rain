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

def get_next_temperature_run() -> datetime:
    mst_tz = ZoneInfo("America/Denver")
    now_mst = datetime.now(mst_tz)
    target = now_mst.replace(hour=18, minute=0, second=0, microsecond=0)
    if now_mst >= target:
        target = target + timedelta(days=1)
    return target

def run_temperature_rollover():
    """
    Daily temperature rollover at 6 PM MST:
    1. Verify today's observed temps (compare with yesterday's forecast)
    2. Fetch tomorrow's forecasts (high and low)
    3. Update Kalshi markets
    Historical forecast data is preserved for accuracy tracking.
    """
    run_temperature_verify()
    run_temperature_forecast()
    run_kalshi()

if __name__ == "__main__":
    logger.info("Starting Scheduler...")
    
    # Run immediately on startup
    run_kalshi()
    run_ingest()
    run_scraper()
    run_temperature_forecast()
    
    last_ingest_time = time.time()
    last_scrape_time = time.time()
    next_temp_run = get_next_temperature_run()
    
    while True:
        current_time = time.time()
        
        # Run Kalshi every minute
        run_kalshi()
        
        # Run Ingest every 6 hours (6 * 3600 seconds)
        if current_time - last_ingest_time > 6 * 3600:
            run_ingest()
            last_ingest_time = current_time

        # Run scraper every 6 hours (6 * 3600 seconds)
        if current_time - last_scrape_time > 6 * 3600:
            run_scraper()
            run_temperature_verify()
            last_scrape_time = current_time

        if datetime.now(ZoneInfo("America/Denver")) >= next_temp_run:
            run_temperature_rollover()
            next_temp_run = get_next_temperature_run()
            
        # Sleep for 60 seconds
        time.sleep(60)
