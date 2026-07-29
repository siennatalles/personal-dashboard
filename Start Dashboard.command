#!/bin/bash
# Double-click this file to start the dashboard and open it in your browser.
# Leave this window open while you're using the dashboard — closing it (or
# pressing Ctrl+C) stops the server.

cd "$(dirname "$0")" || { echo "Could not find the project folder."; read -p "Press Enter to close..."; exit 1; }

echo "Starting your dashboard..."
echo "(Leave this window open. Press Ctrl+C here when you're done for the day.)"
echo ""

# Open the browser tab a couple seconds after the server starts booting.
(sleep 2 && open "http://127.0.0.1:8000") &

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
