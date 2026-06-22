#!/usr/bin/env bash
set -e

APP_DIR="/home/raspi1/sinergi-client"
cd "$APP_DIR"

pkill -f "python3 ui.py" 2>/dev/null || true
sleep 1

# XWayland socket tersedia di :0 (labwc compositor)
export DISPLAY=:0
export SDL_VIDEODRIVER=x11
export PYTHONPATH="$APP_DIR"

python3 ui.py
