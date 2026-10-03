#!/bin/bash
set -e

# Usage:
#   ./update.sh                       pull, rebuild, test, restart local server
#   ./update.sh --local               rebuild + test only (no git pull / server)
#   ./update.sh --export-gst YYYY-MM  export one month of bills → Tally/GST files
#   ./update.sh --export-gst all      export every saved month → Tally/GST files

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

# ── Find python executable ──────────────────────────────────────────────────
if [ -f "$REPO_DIR/.venv/bin/python" ]; then
    PYTHON_EXE="$REPO_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_EXE="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_EXE="python"
else
    echo "ERROR: Python 3 not found in PATH or .venv."
    exit 1
fi

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
        "$PYTHON_EXE" src/seller/prepare_tally_files.py --all
    else
        echo "Exporting $MONTH → Tally DayBook → GST JSON..."
        "$PYTHON_EXE" src/seller/prepare_tally_files.py --month "$MONTH"
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
    # Revert local diffs in generated HTML files so git pull does not conflict
    git restore index.html photo_catalog.html print_catalog.html 2>/dev/null || true
    if ! git pull origin main; then
        echo "⚠️  WARNING: Git pull encountered an issue. Proceeding with local rebuild..."
    fi
fi

echo "Rebuilding the catalogs from the current data (XLSX/CSV), templates, and images..."
"$PYTHON_EXE" src/build_catalog.py

echo "Running tests..."
"$PYTHON_EXE" -m unittest discover -s tests

if command -v node >/dev/null 2>&1; then
    for f in tests/*.test.js; do
        [ -e "$f" ] || continue
        node "$f"
    done
else
    echo "Note: Node.js not detected; skipping front-end test assertions."
fi

if [ "$LOCAL_ONLY" = true ]; then
    echo ""
    echo "======================================================="
    echo "  UPDATE COMPLETE (local mode): rebuilt and tested locally."
    echo "======================================================="
    exit 0
fi

echo "Restarting local seller server..."
# Kill old server if running via server.pid
if [ -f server.pid ]; then
    OLD_PID=$(cat server.pid 2>/dev/null || true)
    if [ -n "$OLD_PID" ]; then
        kill "$OLD_PID" 2>/dev/null || true
    fi
    rm -f server.pid
fi

# Kill any process listening on port 8766 safely
if command -v lsof >/dev/null 2>&1; then
    OLD_PIDS=$(lsof -i:8766 -t 2>/dev/null || true)
    if [ -n "$OLD_PIDS" ]; then
        kill -9 $OLD_PIDS 2>/dev/null || true
    fi
fi

# Start new server
"$PYTHON_EXE" src/seller/local_seller.py > server.log 2>&1 &
echo $! > server.pid
echo "Server started (PID $(cat server.pid))."

echo ""
echo "======================================================="
echo "  UPDATE COMPLETE!"
echo "  The app is running at: http://127.0.0.1:8766/?edit=true"
echo "======================================================="
