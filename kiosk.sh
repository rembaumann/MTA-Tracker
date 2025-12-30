#!/bin/bash

# MTA Tracker Kiosk Mode Script
# This script launches Chromium in kiosk mode to display the MTA Tracker

# Wait for network to be available
while ! ping -c 1 -W 1 8.8.8.8 > /dev/null 2>&1; do
    sleep 1
done

# Wait a bit more for Flask app to be ready
sleep 5

# Disable screen blanking
xset s off
xset -dpms
xset s noblank

# Launch Chromium in kiosk mode
chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-restore-session-state \
    --disable-features=TranslateUI \
    --disable-ipc-flooding-protection \
    --autoplay-policy=no-user-gesture-required \
    --check-for-update-interval=31536000 \
    http://localhost:5001

