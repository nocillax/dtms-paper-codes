#!/usr/bin/env python3
import os
import glob
import re
import csv
import matplotlib
matplotlib.use('Agg') # Safe for headless Linux servers
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Dynamically resolve the repo root
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_DIR = os.path.join(REPO_ROOT, "results/raw_logs")
TEL_DIR = os.path.join(REPO_ROOT, "results/telemetry")
FIG_DIR = os.path.join(REPO_ROOT, "results/figures")

os.makedirs(FIG_DIR, exist_ok=True)

print("\n==============================================================")
print("             EXPERIMENT FINAL SUMMARY TABLE")
print("==============================================================\n")

# 1. Parse RocksDB
rocksdb_metrics = {}
print("--- ROCKSDB METRICS ---")
for f in sorted(glob.glob(f"{LOG_DIR}/rocksdb_*.log")):
    skew = os.path.basename(f).replace("rocksdb_", "").replace(".log", "")
    with open(f, 'r') as file:
        content = file.read()
        matches = re.findall(r"([\d\.]+)\s*micros/op\s*(\d+)\s*ops/sec", content)
        if matches:
            latency, ops = matches[-1]
            logical_mb = (int(ops) * 0.5 * 7200 * 100) / (1024 * 1024) # Adjust 7200 to the value used in the telemetry_daemon.py
            rocksdb_metrics[skew] = {"ops": int(ops), "logical_mb": logical_mb}
            print(f"Skew: {skew:<18} | Throughput: {int(ops):>8,} ops/sec | Logical Writes: {logical_mb:>8.2f} MB")

# 2. Parse WiredTiger
wt_metrics = {}
print("\n--- WIREDTIGER METRICS ---")
for f in sorted(glob.glob(f"{LOG_DIR}/wt_stat_*.txt")):
    skew = os.path.basename(f).replace("wt_stat_", "").replace(".txt", "")
    with open(f, 'r') as file:
        content = file.read()
        reads = re.search(r"Executed (\d+) read operations.*?\)\s*(\d+)\s*ops/sec", content)
        updates = re.search(r"Executed (\d+) update operations.*?\)\s*(\d+)\s*ops/sec", content)
        
        if reads and updates:
            updates_count = int(updates.group(1))
            update_ops_sec = int(updates.group(2))
            read_ops_sec = int(reads.group(2))
            total_ops = read_ops_sec + update_ops_sec
            
            logical_mb = (updates_count * 100) / (1024 * 1024)
            wt_metrics[skew] = {
                "ops": total_ops,
                "logical_mb": logical_mb
            }
            print(f"Skew: {skew:<18} | Throughput: {total_ops:>8,} ops/sec | Logical Writes: {logical_mb:>8.2f} MB")

# 3. Parse NVMe Telemetry & Calculate WAF
telemetry_metrics = {}
print("\n--- PHYSICAL SSD TELEMETRY & WRITE AMPLIFICATION (WAF) ---")
for f in sorted(glob.glob(f"{TEL_DIR}/*.csv")):
    run_name = os.path.basename(f).replace(".csv", "")
    total_physical_mb = 0.0
    count = 0
    try:
        with open(f, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    total_physical_mb += float(row['interval_mb_written'])
                    count += 1
                except (ValueError, KeyError):
                    pass
        if count > 0:
            engine, skew = run_name.split("_", 1)
            logical_mb = 0.0
            if engine == "rocksdb" and skew in rocksdb_metrics:
                logical_mb = rocksdb_metrics[skew]["logical_mb"]
            elif engine == "wiredtiger" and skew in wt_metrics:
                logical_mb = wt_metrics[skew]["logical_mb"]
                
            waf = (total_physical_mb / logical_mb) if logical_mb > 0 else 0.0
            telemetry_metrics[run_name] = {
                "physical_mb": total_physical_mb,
                "waf": waf
            }
            print(f"Run: {run_name:<28} | Physical: {total_physical_mb:>8.2f} MB | Logical: {logical_mb:>8.2f} MB | WAF: {waf:>5.2f}x")
    except Exception as e:
        pass


print("\n[+] Generating Figures...")
# Global Colors for Consistency
color_rocks = '#1f77b4'
color_wt = '#d62728'

# 4. Plot Figures: Bar Charts

skews = ["uniform", "zipfian_standard", "zipfian_extreme"]
labels = ["Uniform\n(\u03b8=0)", "Standard Zipfian\n(\u03b8=0.99)", "Extreme Zipfian\n(\u03b8=1.20)"]

r_ops = [rocksdb_metrics.get(s, {}).get("ops", 0) for s in skews]
w_ops = [wt_metrics.get(s, {}).get("ops", 0) for s in skews]
r_waf = [telemetry_metrics.get(f"rocksdb_{s}", {}).get("waf", 0) for s in skews]
w_waf = [telemetry_metrics.get(f"wiredtiger_{s}", {}).get("waf", 0) for s in skews]

x = np.arange(len(skews))
width = 0.35

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.5))
fig.suptitle("Performance and Write Amplification Comparison", fontsize=15, fontweight='bold', y=0.98)

# Throughput Bar Chart
ax1.bar(x - width/2, r_ops, width=width, label='RocksDB (LSM-Tree)', color=color_rocks, edgecolor='black', zorder=3)
ax1.bar(x + width/2, w_ops, width=width, label='WiredTiger (B-Tree)', color=color_wt, edgecolor='black', zorder=3)
ax1.set_ylabel('Throughput (Ops/sec)', fontsize=12, fontweight='bold')
ax1.set_title('Engine Throughput (Higher is Better)', fontsize=13, pad=10)
ax1.set_xticks(x)
ax1.set_xticklabels(labels, fontsize=11)
ax1.grid(axis='y', linestyle='--', alpha=0.7, zorder=0)
ax1.get_yaxis().set_major_formatter(plt.FuncFormatter(lambda val, loc: "{:,}".format(int(val))))
ax1.legend(frameon=True, shadow=True, fontsize=10)

# WAF Bar Chart
ax2.bar(x - width/2, r_waf, width=width, label='RocksDB', color=color_rocks, edgecolor='black', zorder=3)
ax2.bar(x + width/2, w_waf, width=width, label='WiredTiger', color=color_wt, edgecolor='black', zorder=3)
ax2.set_ylabel('Write Amplification Factor (WAF)', fontsize=12, fontweight='bold')
ax2.set_title('Write Amplification (Lower is Better)', fontsize=13, pad=10)
ax2.set_xticks(x)
ax2.set_xticklabels(labels, fontsize=11)
ax2.grid(axis='y', linestyle='--', alpha=0.7, zorder=0)

plt.tight_layout()
plt.subplots_adjust(top=0.88)
plt.savefig(os.path.join(FIG_DIR, "benchmark_summary_plots.png"), dpi=300)
print(f"  -> Saved {os.path.join(FIG_DIR, 'benchmark_summary_plots.png')}")


# 5. Plot Figures: Time-Series I/O Telemetry
datasets = {
    "Uniform (\u03b8=0)": (os.path.join(TEL_DIR, "rocksdb_uniform.csv"), os.path.join(TEL_DIR, "wiredtiger_uniform.csv")),
    "Standard Zipfian (\u03b8=0.99)": (os.path.join(TEL_DIR, "rocksdb_zipfian_standard.csv"), os.path.join(TEL_DIR, "wiredtiger_zipfian_standard.csv")),
    "Extreme Zipfian (\u03b8=1.20)": (os.path.join(TEL_DIR, "rocksdb_zipfian_extreme.csv"), os.path.join(TEL_DIR, "wiredtiger_zipfian_extreme.csv"))
}

time_limit = 600 # First 10 minutes

fig_ts, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True, sharey=True)
fig_ts.suptitle('Physical NVMe Write Rate: The Impact of Data Skew (First 10 Minutes)', fontsize=16, y=0.95)

for ax, (title, (r_file, w_file)) in zip(axes, datasets.items()):
    if os.path.exists(r_file) and os.path.exists(w_file):
        df_r = pd.read_csv(r_file)
        df_w = pd.read_csv(w_file)
        
        df_r_filt = df_r[df_r['elapsed_sec'] <= time_limit]
        df_w_filt = df_w[df_w['elapsed_sec'] <= time_limit]
        
        ax.plot(df_r_filt['elapsed_sec'], df_r_filt['write_rate_mbps'], label='RocksDB (LSM-Tree)', color=color_rocks, alpha=0.9, linewidth=1.2)
        ax.plot(df_w_filt['elapsed_sec'], df_w_filt['write_rate_mbps'], label='WiredTiger (B-Tree)', color=color_wt, alpha=0.8, linewidth=1.2)
        
        ax.set_title(title, fontsize=14)
        ax.set_ylabel('Write Rate (MB/s)', fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.6)
        
        if ax == axes[0]:
            ax.legend(loc='upper right', frameon=True, shadow=True)
    else:
        ax.set_title(f"{title} - DATA MISSING", fontsize=14, color='red')

axes[-1].set_xlabel('Elapsed Time (Seconds)', fontsize=12)

plt.tight_layout()
plt.subplots_adjust(top=0.92)
plt.savefig(os.path.join(FIG_DIR, "io_skew_comparison.png"), dpi=300)
print(f"  -> Saved {os.path.join(FIG_DIR, 'io_skew_comparison.png')}")

print("\n[+] All processing complete.")