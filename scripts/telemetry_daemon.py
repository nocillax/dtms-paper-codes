import subprocess
import json
import time
import sys

def get_nvme_bytes_written(device="/dev/nvme1n1"):
    try:
        result = subprocess.run(
            ['sudo', 'nvme', 'smart-log', device, '-o', 'json'],
            capture_output=True, text=True, check=True
        )
        data = json.loads(result.stdout)
        # NVMe spec: data_units_written is in thousands of 512-byte blocks
        units = data.get("data_units_written", 0)
        return units * 1000 * 512
    except Exception as e:
        print(f"Error reading NVMe SMART log: {e}", file=sys.stderr)
        return None

def main():
    print("timestamp_sec,elapsed_sec,total_physical_mb_written,interval_mb_written,write_rate_mbps", flush=True)
    start_time = time.time()
    last_bytes = get_nvme_bytes_written()
    
    if last_bytes is None:
        sys.exit(1)

    while True:
        try:
            time.sleep(2)
            current_time = time.time()
            elapsed = current_time - start_time
            
            current_bytes = get_nvme_bytes_written()
            if current_bytes is not None:
                interval_bytes = current_bytes - last_bytes
                interval_mb = interval_bytes / (1024 * 1024)
                total_mb = current_bytes / (1024 * 1024)
                rate_mbps = interval_mb / 2.0
                
                print(f"{current_time:.2f},{elapsed:.2f},{total_mb:.2f},{interval_mb:.2f},{rate_mbps:.2f}", flush=True)
                last_bytes = current_bytes
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
