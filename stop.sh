#!/bin/bash
if [ -f server.pid ]; then
    PID=$(cat server.pid)
    kill $PID 2>/dev/null
    rm server.pid
    echo "Stopped server (PID $PID)."
else
    echo "Server is not running (no server.pid found)."
    # Fallback to killing anything on port 8766
    lsof -i:8766 -t | xargs kill -9 2>/dev/null
fi
