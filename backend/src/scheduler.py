import time
import subprocess
import logging
import sys
from pathlib import Path

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

if __name__ == "__main__":
    logger.info("Starting Scheduler...")
    
    # Run immediately on startup
    run_kalshi()
    run_ingest()
    run_scraper()
    
    last_ingest_time = time.time()
    last_scrape_time = time.time()
    
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
            # Run Temperature Verification
            try:
                logger.info("Running Temperature Verification...")
                subprocess.run([PYTHON_EXEC, "-m", "backend.src.ingest_temperature", "--verify"], check=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"Temp Verification failed: {e}")
                
            last_scrape_time = current_time
            
        # Sleep for 60 seconds
        time.sleep(60)
