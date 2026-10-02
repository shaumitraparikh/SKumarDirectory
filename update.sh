#!/bin/bash
set -e

# Usage:
#   ./update.sh           pull, rebuild, test, restart the local seller server
#   ./update.sh --local   rebuild + test only (no git pull, no server restart)
#                         -- used by CI and when you just changed data/templates.
LOCAL_ONLY=false
if [ "${1:-}" = "--local" ]; then
    LOCAL_ONLY=true
fi

echo "======================================================="
echo "        S. KUMAR & BROS - CATALOG UPDATER"
echo "======================================================="
echo ""

if [ "$LOCAL_ONLY" = false ]; then
    echo "Pulling latest changes..."
    git pull origin main
fi

echo "Rebuilding the catalogs from the current CSV, templates, and images..."
python3 src/build_catalog.py

echo "Running tests..."
python3 -m unittest discover -s tests
for f in tests/*.test.js; do
    [ -e "$f" ] || continue
    node "$f"
done

if [ "$LOCAL_ONLY" = true ]; then
    echo ""
    echo "======================================================="
    echo "  UPDATE COMPLETE (local mode): rebuilt and tested locally."
    echo "======================================================="
    exit 0
fi

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
