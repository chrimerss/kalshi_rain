import boto3
from botocore import UNSIGNED
from botocore.config import Config
from datetime import datetime, timezone, timedelta

def test_nbm():
    # Configure anonymous S3 access
    s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))
    bucket = "noaa-nbm-grib2-pds"
    
    # 1. Determine latest available run
    # Try current hour, then previous hours
    now = datetime.now(timezone.utc)
    
    for i in range(5):
        t = now - timedelta(hours=i)
        ymd = t.strftime("%Y%m%d")
        hour = t.hour
        # File key: blend.{ymd}/{init_hour:02d}/text/blend_nbhtx.t{init_hour:02d}z
        key = f"blend.{ymd}/{hour:02d}/text/blend_nbhtx.t{hour:02d}z"
        
        print(f"Trying key: {key}")
        
        try:
            # Head object to check existence
            s3.head_object(Bucket=bucket, Key=key)
            print("Found!")
            
            # Download entire file (streaming) to find our stations
            # This file is text, likely ~5-10MB?
            print("Streaming file...")
            response = s3.get_object(Bucket=bucket, Key=key)
            
            # Using a line-based iterator
            # We need to handle decoding carefully if chunks split utf-8 characters, 
            # but usually these are ascii.
            
            # Simple approach: read line by line from stream
            stream = response['Body']
            
            # Stations to find
            target_stations = ["KLAX", "KNYC", "KMIA"] 
            found_data = {}
            
            current_station = None
            buffer = []
            
            for line_bytes in stream.iter_lines():
                if not line_bytes: continue
                line = line_bytes.decode('utf-8', errors='ignore')
                
                # Check for station header
                # Header format: "KLAX   NBM V4.1 ..." or similar? 
                # In the snippet: " 086092 NBM V4.3 ..." - The first token was 086092.
                # Maybe station ID is there? 
                # Let's look for our target stations in the line.
                
                parts = line.split()
                if len(parts) > 0 and parts[0] in target_stations:
                    current_station = parts[0]
                    # print(f"Found station: {current_station}")
                    buffer = [line] # Start buffering
                    continue
                
                if current_station:
                    buffer.append(line)
                    # Blocks are usually ~30 lines. Wait until we see Q01 (or end of block).
                    # Actually, just capture ~30 lines then process.
                    if len(buffer) > 35:
                        # Process buffer
                        found_data[current_station] = buffer[:]
                        print(f"Captured block for {current_station}")
                        
                        # Reset
                        current_station = None
                        buffer = []
                        
                        if len(found_data) == len(target_stations):
                            break
            
            # Analyze captured blocks
            for st, lines in found_data.items():
                print(f"\n--- Analysis for {st} ---")
                utc_line = next((l for l in lines if l.strip().startswith("UTC")), None)
                q01_line = next((l for l in lines if l.strip().startswith("Q01")), None)
                
                if utc_line: print(f"UTC: {utc_line.strip()}")
                if q01_line: print(f"Q01: {q01_line.strip()}")
            
            break
            
        except Exception as e:
            print(f"Not found or error: {e}")

if __name__ == "__main__":
    test_nbm()
