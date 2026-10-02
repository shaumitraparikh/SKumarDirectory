#!/bin/bash
echo "Starting SKumar Local Server..."
if lsof -i:8766 -t >/dev/null; then
    echo "Server is already running on port 8766!"
else
    python3 src/seller/local_seller.py > server.log 2>&1 &
    echo $! > server.pid
    echo "Server started (PID $(cat server.pid))."
fi
open "http://127.0.0.1:8766/?edit=true"
