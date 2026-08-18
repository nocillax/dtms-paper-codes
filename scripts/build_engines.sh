#!/bin/bash
set -e

# Move to the root of the repository regardless of where the script is run from
cd "$(dirname "$0")/.."

echo "=== Building WiredTiger ==="
if [ ! -d "wiredtiger" ]; then
    git clone https://github.com/wiredtiger/wiredtiger.git
fi
cd wiredtiger
mkdir -p build
cd build
cmake ..
make -j$(nproc)
cd ../..

echo "=== Building RocksDB ==="
if [ ! -d "rocksdb" ]; then
    git clone https://github.com/facebook/rocksdb.git
fi
cd rocksdb
# db_bench is the specific benchmarking binary we need
make db_bench -j$(nproc)
cd ..

echo "[+] Both storage engines successfully built."