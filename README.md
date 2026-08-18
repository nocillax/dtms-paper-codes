# Comparative Evaluation of B-Tree vs. LSM-Tree Under Zipfian Skew on NVMe SSDs

This repository contains the complete experimental harness, telemetry pipeline, and parsing scripts to reproduce the findings presented in the DTMS course project. It compares the Write Amplification Factor (WAF) and throughput of WiredTiger (B-Tree) and RocksDB (LSM-Tree).

## Repository Structure

```text
.
├── scripts/
│   ├── setup_env.sh
│   ├── build_engines.sh
│   ├── 03_telemetry_daemon.py
│   ├── 04_run_suite.py
│   └── 05_parse_and_plot.py
├── results/
│   ├── raw_logs/      # Output logs containing operations/sec
│   ├── telemetry/     # 2-second interval NVMe CSV data
│   └── figures/       # Generated matplotlib charts
└── README.md

## System Requirements

- **OS:** Linux (Ubuntu 22.04 / Pop!_OS 22.04 recommended)
- **Storage:** Commodity NVMe SSD (Target block device: `/dev/nvme1n1`)
- **Privileges:** `sudo` access is strictly required for `nvme-cli` SMART telemetry polling.

## Reproducibility Workflow

**1. Clone the repository:**
```bash
git clone <https://github.com/your-username/nvme-kv-bench.git>
cd nvme-kv-bench
```

**2. Install Dependencies & Build Engines:**

Bash

```
bash scripts/setup_env.sh
bash scripts/build_engines.sh
```

**3. Execute the Benchmark Suite:**
This will run the 12-hour workload suite (Uniform, Standard Zipfian, Extreme Zipfian 2-hours for each of them for the 2 engines) for both engines while safely polling the NVMe SMART logs in the background. (Adjust the duration value in scripts/run_suite.py to lower the experiment runtime).

Bash

```
sudo python3 scripts/run_suite.py
```

**4. Parse Results & Generate Plots:**
Extracts the throughput and calculates the physical Write Amplification Factor (WAF), generating a publication-ready `.png` comparison chart.

Bash

```
python3 scripts/parse_and_plot.py
```

Results, including the raw engine logs, telemetry CSVs, and final figures, will be exported to the `results/` directory. 
_(Note: The results of the primary experiment are already available in the results folder)._

## License

This project is open-source and available under the MIT License.

## Author

**Md. Asif Chowdhury**
B.Sc. in Computer Science & Engineering
American International University-Bangladesh
Email: [asifjarif@gmail.com]
GitHub: @nocillax