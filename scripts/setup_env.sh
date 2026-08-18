#!/bin/bash
set -e

echo "=== Installing System Dependencies ==="
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    libsnappy-dev \
    zlib1g-dev \
    libbzip2-dev \
    liblz4-dev \
    libzstd-dev \
    nvme-cli \
    python3-tqdm \
    python3-matplotlib

echo "[+] Environment setup complete."