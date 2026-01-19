# RainCheck - Rainfall Forecast System

A full-stack application to track monthly total precipitation for Kalshi betting markets.

## Project Structure
- `backend/`: Python backend for data ingestion and storage.
  - `src/scraper.py`: Scrapes NWS CLI product for observed MTD precipitation.
  - `src/ingest.py`: Downloads and processes GFS (and other) model data from AWS.
  - `data/raincheck.db`: SQLite database storing forecasts.
- `frontend/`: Next.js application for visualization.

## Setup

### Backend
1. **Prerequisites**: Conda or Python 3.10+.
2. **Environment**:
   ```bash
   conda env create -f backend/environment.yml
   conda activate raincheck
   ```
   *Note: If `raincheck` env name is used, otherwise check `backend/environment.yml` name.*

3. **Running Updates**:
   Use the provided script:
   ```bash
   ./cron_job.sh
   ```
   This runs the scraper and the GFS ingestion.

### Frontend
1. **Prerequisites**: Node.js 18+.
2. **Install**:
   ```bash
   cd frontend
   npm install
   ```
3. **Run Development Server**:
   ```bash
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000).

4. **Build for Production**:
   ```bash
   npm run build
   npm start
   ```

## Configuration
- **Stations**: Defined in `backend/src/config.py`.
- **Models**: GFS, ECMWF, NAM, and HRRR are supported in `backend/src/ingest.py` (config in `backend/src/config.py`).

## Data Sources
- **Observed**: NWS CLI Product (`forecast.weather.gov`).
- **Forecast**: NOAA GFS (`noaa-gfs-bdp-pds`), ECMWF (`ecmwf-forecasts`), NAM (`noaa-nam-pds`), HRRR (`noaa-hrrr-bdp-pds`).

## Automation
Add `./cron_job.sh` to your crontab to run every 6 hours (e.g., `0 */6 * * *`).
