#!/bin/bash
set -e

# Usage:
#   ./update.sh                       pull, rebuild, test, restart local server
#   ./update.sh --local               rebuild + test only (no git pull / server)
#   ./update.sh --export-gst YYYY-MM  export one month of bills → Tally/GST files
#   ./update.sh --export-gst all      export every saved month → Tally/GST files

# ── GST export shortcut ────────────────────────────────────────────────────────
if [ "${1:-}" = "--export-gst" ]; then
    MONTH="${2:-}"
    if [ -z "$MONTH" ]; then
        echo "Usage: ./update.sh --export-gst YYYY-MM   (or 'all' for every month)"
        exit 1
    fi
    echo "======================================================="
    echo "  S. KUMAR & BROS - GST EXPORT"
    echo "======================================================="
    if [ "$MONTH" = "all" ]; then
        echo "Exporting ALL saved months → Tally DayBook → GST JSON..."
        python3 src/seller/prepare_tally_files.py --all
    else
        echo "Exporting $MONTH → Tally DayBook → GST JSON..."
        python3 src/seller/prepare_tally_files.py --month "$MONTH"
    fi
    echo ""
    echo "======================================================="
    echo "  EXPORT COMPLETE!"
    echo "  GST files: TallyToOutputsForGST/output/"
    echo "  Upload the .json to https://gst.gov.in (GSTR-1)"
    echo "======================================================="
    exit 0
fi

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

echo "Rebuilding the catalogs from the current Excel data, templates, and images..."
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
