#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import shutil
import threading
from tqdm import tqdm

# Dynamically resolve the repo root
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_DIR = os.path.join(REPO_ROOT, "results/raw_logs")
TEL_DIR = os.path.join(REPO_ROOT, "results/telemetry")

# FAULT TOLERANCE CHECKLIST:
# To run specific ones only, comment out the rest.
TEST_SUITE = [
    {"engine": "rocksdb",    "skew_name": "uniform",          "param": 0.0,  "duration": 7200},
    {"engine": "wiredtiger", "skew_name": "uniform",          "param": 0,    "duration": 7200},
    {"engine": "rocksdb",    "skew_name": "zipfian_standard", "param": 0.99, "duration": 7200},
    {"engine": "wiredtiger", "skew_name": "zipfian_standard", "param": 80,   "duration": 7200},
    {"engine": "rocksdb",    "skew_name": "zipfian_extreme",  "param": 1.20, "duration": 7200},
    {"engine": "wiredtiger", "skew_name": "zipfian_extreme",  "param": 99,   "duration": 7200},
]

def keep_sudo_alive():
    """Background thread to prevent sudo session timeout during long benchmarks."""
    while True:
        subprocess.run(["sudo", "-v"], check=False)
        time.sleep(300)

def run_benchmark(test, progress_bar):
    engine = test["engine"]
    skew = test["skew_name"]
    param = test["param"]
    duration = test["duration"]
    
    progress_bar.set_description(f"Running {engine.upper()} ({skew})")
    
    # 1. Clean previous state safely
    if engine == "rocksdb":
        db_path = os.path.join(REPO_ROOT, "rocksdb/exp_db")
        if os.path.exists(db_path): 
            shutil.rmtree(db_path)
    elif engine == "wiredtiger":
        wt_test_path = os.path.join(REPO_ROOT, "wiredtiger/build/WT_TEST")
        if os.path.exists(wt_test_path): 
            shutil.rmtree(wt_test_path)
        os.makedirs(wt_test_path, exist_ok=True)
    
    # 2. Start telemetry daemon
    tel_out = open(os.path.join(TEL_DIR, f"{engine}_{skew}.csv"), "w")
    tel_proc = subprocess.Popen(
        ["sudo", "python3", os.path.join(REPO_ROOT, "scripts/telemetry_daemon.py")],
        stdout=tel_out, stderr=subprocess.DEVNULL
    )
    time.sleep(2)
    
    # 3. Build command
    if engine == "rocksdb":
        cmd = [
            f"{REPO_ROOT}/rocksdb/db_bench",
            "--benchmarks=fillrandom,readrandomwriterandom",
            "--use_existing_db=0",
            "--num=2000000",
            "--value_size=100",
            f"--duration={duration}",
            "--threads=4",
            "--histogram=1",
            f"--key_dist_a={param}",
            f"--db={REPO_ROOT}/rocksdb/exp_db"
        ]
        cwd = os.path.join(REPO_ROOT, "rocksdb")
    else:
        cmd = [
            f"{REPO_ROOT}/wiredtiger/build/bench/wtperf/wtperf",
            "-o", "create=true",
            "-o", "icount=500000",
            f"-o", f"run_time={duration}",
            "-o", "threads=((count=4,reads=50,updates=50))",
            f"-o", f"pareto={param}",
            "-o", "checkpoint_interval=15",
            "-o", "table_name=exp_wt"
        ]
        cwd = os.path.join(REPO_ROOT, "wiredtiger/build")

    # 4. Execute benchmark
    bench_log_path = os.path.join(LOG_DIR, f"{engine}_{skew}.log")
    with open(bench_log_path, "w") as bench_log:
        bench_proc = subprocess.Popen(cmd, stdout=bench_log, stderr=bench_log, cwd=cwd)
        
        start_time = time.time()
        last_elapsed = 0
        while bench_proc.poll() is None:
            elapsed = time.time() - start_time
            delta = elapsed - last_elapsed
            progress_bar.update(delta)
            last_elapsed = elapsed
            
            if elapsed > (duration + 30):
                print(f"\n[!] {engine} hung during teardown. Force killing.")
                bench_proc.kill()
                break
                
            time.sleep(1)
            
    # 5. Extract WiredTiger stats
    if engine == "wiredtiger":
        stat_src = os.path.join(REPO_ROOT, "wiredtiger/build/WT_TEST/exp_wt.stat")
        stat_dst = os.path.join(LOG_DIR, f"wt_stat_{skew}.txt")
        if os.path.exists(stat_src): 
            shutil.copy2(stat_src, stat_dst)

    # 6. Clean telemetry daemon
    try:
        subprocess.run(["sudo", "pkill", "-f", "telemetry_daemon.py"], check=False)
        tel_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    tel_out.close()

def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(TEL_DIR, exist_ok=True)
    
    subprocess.run(["sudo", "-v"], check=True)
    threading.Thread(target=keep_sudo_alive, daemon=True).start()
    
    total_seconds = sum(t["duration"] for t in TEST_SUITE)
    print("=== NVMe Storage Engine Comparative Suite ===")
    
    with tqdm(total=total_seconds, unit="s", desc="Overall Progress") as pbar:
        for test in TEST_SUITE:
            run_benchmark(test, pbar)
            
    print("\n[+] Benchmark suite complete.")

if __name__ == "__main__":
    main()
