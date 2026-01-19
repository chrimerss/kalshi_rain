import boto3
import botocore
from botocore import UNSIGNED
from botocore.config import Config
import xarray as xr
import cfgrib
import os
import numpy as np
from datetime import datetime, timedelta, timezone
from pathlib import Path
import logging
import shutil
import time
from typing import Optional

from .config import STATIONS, MODELS, Station, DATA_DIR
from .db import save_forecast, get_latest_observation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure anonymous S3 access
# Configure anonymous S3 access with timeouts
config = Config(
    signature_version=UNSIGNED,
    connect_timeout=10,
    read_timeout=30,
    retries={'max_attempts': 3}
)
s3 = boto3.client('s3', config=config)

def get_latest_run_time(model_name: str) -> datetime:
    """
    Determines the latest available run time for a model.
    """
    now = datetime.now(timezone.utc)
    config = MODELS.get(model_name)
    if not config:
        raise ValueError(f"Unknown model: {model_name}")
        
    bucket = config['bucket']
    
    cycle_step = 6
    if model_name in ["HRRR", "NAM"]:
        cycle_step = 1
    
    # Start from current hour
    current_cycle_start = now.replace(minute=0, second=0, microsecond=0)
    hour = (current_cycle_start.hour // cycle_step) * cycle_step
    current_cycle_start = current_cycle_start.replace(hour=hour)
    
    for i in range(12):
        t = current_cycle_start - timedelta(hours=cycle_step*i)
        
        date_str = t.strftime("%Y%m%d")
        cycle_str = f"{t.hour:02d}"
        
        if model_name == "ECMWF":
            step_str = "0"
        elif model_name == "GFS":
            step_str = "000"
        elif model_name == "NAM":
            step_str = "00"
        elif model_name == "HRRR":
            step_str = "00"
            
        key = config['prefix_template'].format(date=date_str, cycle=cycle_str, step=step_str)
        
        try:
            s3.head_object(Bucket=bucket, Key=key)
            logger.info(f"Found latest {model_name} run: {t}")
            return t
        except botocore.exceptions.ClientError:
            continue
            
    raise RuntimeError(f"Could not find any recent runs for {model_name}")

def download_grib_file(bucket: str, key: str, local_path: Path):
    if not local_path.parent.exists():
        local_path.parent.mkdir(parents=True)
        
    if local_path.exists() and local_path.stat().st_size > 0:
        return True # Skip if exists
        
    try:
        s3.download_file(bucket, key, str(local_path))
        return True
    except botocore.exceptions.ClientError as e:
        logger.warning(f"Failed to download {key}: {e}")
        return False

def open_precip_dataset(file_path: Path, model_name: str) -> tuple[Optional[xr.Dataset], Optional[str]]:
    """Open a GRIB file and return (dataset, precip_var_name) if found."""
    candidate_filters = []
    if model_name == "ECMWF":
        candidate_filters = [
            {"shortName": "tp", "typeOfLevel": "surface"},
        ]
    elif model_name in ["NAM", "HRRR"]:
        candidate_filters = [
            {"shortName": "apcp", "typeOfLevel": "surface"},
            {"shortName": "apcp"},
        ]
    else:  # GFS
        candidate_filters = [
            {"shortName": "apcp", "typeOfLevel": "surface"},
            {"shortName": "apcp"},
        ]

    for filt in candidate_filters:
        try:
            # indexpath='' prevents creation/usage of persistent .idx files
            datasets = cfgrib.open_datasets(file_path, filter_by_keys=filt, indexpath='')
            for ds in datasets:
                for var_name in ["tp", "apcp"]:
                    if var_name in ds.data_vars:
                        return ds, var_name
        except Exception:
            continue

    # Fallback: open without filter and search
    try:
        ds = xr.open_dataset(file_path, engine="cfgrib", backend_kwargs={'indexpath': ''})
        for var_name in ["tp", "apcp"]:
            if var_name in ds.data_vars:
                return ds, var_name
        ds.close()
    except Exception:
        pass

    logger.warning("No precip variable found in GRIB file")
    return None, None


def extract_precip_values(ds: xr.Dataset, var_name: str, stations: dict[str, Station]) -> dict[str, float]:
    """Extract precipitation values (in mm) from dataset for all stations."""
    lat_name = "latitude" if "latitude" in ds.coords else ("lat" if "lat" in ds.coords else None)
    lon_name = "longitude" if "longitude" in ds.coords else ("lon" if "lon" in ds.coords else None)

    results = {}
    if not lat_name or not lon_name:
        logger.warning("No lat/lon coords found in dataset")
        return {sid: 0.0 for sid in stations}

    try:
        lat_dims = ds[lat_name].dims
        
        # 1D Coordinates (Regular Grid like GFS)
        if len(lat_dims) == 1:
            # For 1D, we can loop or use vectorized selection if we construct arrays.
            # Looping is simple enough for 10 stations, but let's try to be efficient.
            # Actually, `sel` with lists creates a meshgrid by default on older xarray or if dimensions differ.
            # We want point-wise.
            
            # Efficient loop for 1D grid is fast enough (lookup is O(log N) or O(1)).
            ds_lons = ds[lon_name].values
            
            for sid, station in stations.items():
                target_lon = station.lon
                if (ds_lons > 180).any():
                    target_lon = station.lon % 360
                
                try:
                    val = ds[var_name].sel({lat_name: station.lat, lon_name: target_lon}, method="nearest").values.item()
                    results[sid] = float(val)
                except Exception:
                     results[sid] = 0.0

        # 2D Coordinates (Curvilinear like LAM, HRRR)
        else:
            lats = ds[lat_name].values
            lons = ds[lon_name].values
            if (lons > 180).any():
                lons = (lons + 180) % 360 - 180
            
            # We process all stations.
            # Optimization: could use KDTree, but brute force distance on 10 stations is fine if vectorized.
            # But the user asked to "pass all station coordinates".
            # Let's vectorize the distance calc for all stations against the whole grid? 
            # No, that's (N_stations, Y, X). 10 * 1000 * 1000 = 10M floats. manageable.
            
            # Better: iterate stations and find nearest index for each.
            # To be truly "batch", we would put stations in an array.
            
            station_ids = list(stations.keys())
            target_lats = np.array([stations[sid].lat for sid in station_ids])
            target_lons = np.array([stations[sid].lon for sid in station_ids])
            
            # Simple caching could go here but let's just do the search.
            # If we want to optimize, we can execute the search sequentially or parallel.
            # Since numpy releases GIL, we can just loop.
            
            for i, sid in enumerate(station_ids):
                # (Y, X) - scalar
                dist = (lats - target_lats[i]) ** 2 + (lons - target_lons[i]) ** 2
                min_idx = dist.argmin()
                y_idx, x_idx = np.unravel_index(min_idx, lats.shape)
                val = ds[var_name].isel(y=y_idx, x=x_idx).values.item()
                results[sid] = float(val)

        return results
    except Exception as e:
        logger.error(f"Batch extraction error: {e}")
        return {sid: 0.0 for sid in stations}

def process_model_run(model_name: str, run_time: datetime):
    config = MODELS[model_name]
    bucket = config['bucket']
    
    now = datetime.now(timezone.utc)
    current_month = now.month
    current_year = now.year
    
    if current_month == 12:
        next_month = datetime(current_year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(current_year, current_month + 1, 1, tzinfo=timezone.utc)
    
    month_end = next_month - timedelta(seconds=1)
    
    if now > month_end:
        logger.info("Current time is past month end.")
        return

    # Calculate time window relative to run_time
    t_start = max(run_time, now)
    t_end = month_end
    
    start_hour_offset = (t_start - run_time).total_seconds() / 3600
    end_hour_offset = (t_end - run_time).total_seconds() / 3600
    
    step_size = 6
    max_forecast_hour = 384
    
    if model_name == "NAM":
        step_size = 3
        max_forecast_hour = 84
    elif model_name == "HRRR":
        step_size = 1
        max_forecast_hour = 48
    elif model_name == "ECMWF":
        step_size = 6
        max_forecast_hour = 240
        
    # Logic for Cumulative vs Summing
    is_cumulative = model_name in ["ECMWF", "NAM", "HRRR"]
    
    relevant_steps = []
    
    if is_cumulative:
        step_start = int(start_hour_offset // step_size) * step_size
        step_end = int(end_hour_offset // step_size) * step_size
        step_end = min(step_end, max_forecast_hour)
        
        if step_start >= max_forecast_hour:
             relevant_steps = []
        else:
             relevant_steps = sorted(list(set([step_start, step_end])))
    else:
        # GFS Summing
        for h in range(step_size, max_forecast_hour + step_size, step_size):
            file_start_rel = h - step_size
            file_end_rel = h
            if file_end_rel > start_hour_offset and file_start_rel < end_hour_offset:
                relevant_steps.append(h)
    
    logger.info(f"Processing {model_name} {run_time} (Steps: {relevant_steps})")
    
    run_dir = DATA_DIR / f"{model_name}_{run_time.strftime('%Y%m%d_%H')}"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    values_at_steps = {sid: {} for sid in STATIONS} # {sid: {step: val}}
    
    for step in relevant_steps:
        date_str = run_time.strftime("%Y%m%d")
        cycle_str = f"{run_time.hour:02d}"
        
        if model_name == "ECMWF":
            step_str = str(step)
        elif model_name == "NAM":
            step_str = f"{step:02d}"
        elif model_name == "HRRR":
            step_str = f"{step:02d}"
        else: # GFS
            step_str = f"{step:03d}"
            
        key = config['prefix_template'].format(date=date_str, cycle=cycle_str, step=step_str)
        local_file = run_dir / f"{model_name}.t{cycle_str}z.f{step_str}.grib2"
        
        if download_grib_file(bucket, key, local_file):
            ds, var_name = open_precip_dataset(local_file, model_name)
            if ds is None or var_name is None:
                continue
            try:
                batch_vals = extract_precip_values(ds, var_name, STATIONS)
                for sid, val in batch_vals.items():
                    if sid == "NYC":
                         logger.info(f"DEBUG: {model_name} Step {step} Raw Val: {val}")
                    values_at_steps[sid][step] = val * 0.0393701
            finally:
                ds.close()
                
    # Cleanup
    if run_dir.exists():
        shutil.rmtree(run_dir)
    
    is_partial = end_hour_offset > max_forecast_hour
    
    for sid, station in STATIONS.items():
        forecast_val = 0.0
        
        if is_cumulative:
            steps = sorted(values_at_steps[sid].keys())
            if len(steps) >= 2:
                v_start = values_at_steps[sid].get(steps[0], 0.0)
                v_end = values_at_steps[sid].get(steps[-1], 0.0)
                forecast_val = max(0.0, v_end - v_start)
            elif len(steps) == 1:
                # Only one step recovered?
                # If it's the 'end' step, and 'start' step failed (maybe start was 0h?),
                # assume start was 0.
                if steps[0] > 0:
                     forecast_val = values_at_steps[sid].get(steps[0], 0.0)
                else:
                     forecast_val = 0.0
        else:
            # GFS Summing
            for step in relevant_steps:
                val = values_at_steps[sid].get(step, 0.0)
                bucket_start = step - step_size
                bucket_end = step
                overlap_start = max(bucket_start, start_hour_offset)
                overlap_end = min(bucket_end, end_hour_offset)
                
                if overlap_end > overlap_start:
                    fraction = (overlap_end - overlap_start) / step_size
                    forecast_val += (val * fraction)

        observed = get_latest_observation(station.id)
        
        save_forecast(
            location_id=station.id,
            model_name=model_name,
            init_time=run_time.isoformat(),
            observed_mtd=observed,
            forecast_remainder=forecast_val,
            is_partial=is_partial
        )
        logger.info(f"{model_name} {sid}: {forecast_val:.2f} in")

if __name__ == "__main__":
    for model in ["GFS", "ECMWF", "NAM", "HRRR"]:
        try:
            logger.info(f"--- Ingesting {model} ---")
            latest = get_latest_run_time(model)
            process_model_run(model, latest)
        except Exception as e:
            logger.error(f"{model} failed: {e}")
