import argparse
import logging
import sys
from datetime import datetime, timezone

# Add backend to path
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.src.ingest import get_latest_run_time, process_model_run
from backend.src.config import MODELS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Verify ingestion for a specific model")
    parser.add_argument("--model", type=str, required=True, help="Model name (GFS, NAM, HRRR, ECMWF)")
    args = parser.parse_args()

    model_name = args.model.upper()
    
    if model_name not in MODELS:
        print(f"Error: Model {model_name} not found in config.")
        sys.exit(1)

    print(f"--- Verifying Ingestion for {model_name} ---")
    
    try:
        latest = get_latest_run_time(model_name)
        print(f"Latest identified run: {latest}")
        
        process_model_run(model_name, latest)
        print(f"Successfully processed {model_name}")
        
    except Exception as e:
        logger.exception(f"Ingestion failed for {model_name}")
        sys.exit(1)

if __name__ == "__main__":
    main()
