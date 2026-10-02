#!/bin/bash
set -e

echo "======================================================="
echo "        S. KUMAR & BROS - CATALOG UPDATER"
echo "======================================================="
echo ""

echo "Pulling latest changes..."
git pull origin main

echo "Rebuilding the catalogs from the current CSV, templates, and images..."
python3 src/build_catalog.py

echo "Running tests..."
pytest tests/test_end_to_end.py

echo "Starting local seller server..."
if lsof -i:8766 -t >/dev/null; then
    echo "Seller server already running on port 8766."
else
    python3 src/seller/local_seller.py > server.log 2>&1 &
    echo $! > server.pid
    echo "Server started (PID $(cat server.pid))."
fi

echo "Open: http://127.0.0.1:8766/?edit=true"
echo "======================================================="
echo "  UPDATE COMPLETE!"
echo "======================================================="
