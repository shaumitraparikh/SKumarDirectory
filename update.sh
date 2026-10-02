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

echo "Restarting local seller server..."
# Kill old server if running
if [ -f server.pid ]; then
    kill $(cat server.pid) 2>/dev/null || true
    rm server.pid
fi
lsof -i:8766 -t | xargs kill -9 2>/dev/null || true

# Start new server
python3 src/seller/local_seller.py > server.log 2>&1 &
echo $! > server.pid
echo "Server started (PID $(cat server.pid))."

echo ""
echo "======================================================="
echo "  UPDATE COMPLETE!"
echo "  The app is running at: http://127.0.0.1:8766/?edit=true"
echo "======================================================="
