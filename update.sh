#!/bin/bash
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
./start.sh

echo "======================================================="
echo "  UPDATE COMPLETE!"
echo "======================================================="
