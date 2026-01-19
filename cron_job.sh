#!/bin/bash
# RainCheck Backend Scheduler
# Usage: ./cron_job.sh
# Can be added to crontab: 0 */6 * * * /path/to/cron_job.sh >> /path/to/cron.log 2>&1

# Set paths
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

# Activate environment
# Assuming conda is available or using the local env python directly
PYTHON_EXEC="$BASE_DIR/backend/env/bin/python"
LOG_FILE="$BASE_DIR/cron.log"

# Run Open-Meteo Ingestion (All Models)
echo "--- Starting Open-Meteo Ingestion: $(date) ---" >> "$LOG_FILE"
"$PYTHON_EXEC" "$BASE_DIR/backend/src/ingest_api.py" >> "$LOG_FILE" 2>&1
echo "--- Ingestion Complete: $(date) ---" >> "$LOG_FILE"

# Run Kalshi Ingestion (Market Data)
echo "--- Starting Kalshi Ingestion: $(date) ---" >> "$LOG_FILE"
"$PYTHON_EXEC" "$BASE_DIR/backend/src/kalshi.py" >> "$LOG_FILE" 2>&1
echo "--- Kalshi Complete: $(date) ---" >> "$LOG_FILE"

echo "========================================"
echo "Starting RainCheck Update: $(date)"

# 1. Scrape NWS Observation
echo "Running NWS Scraper..."
"$PYTHON_EXEC" -m backend.src.scraper
if [ $? -ne 0 ]; then
    echo "ERROR: Scraper failed."
fi

echo "========================================" >> "$BASE_DIR/cron.log"
