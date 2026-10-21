#!/bin/bash
# Full-screen board for Raspberry Pi OS with labwc (Wayland).
# Falls back to X11 commands only when this session is not Wayland.

set -u

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/mta-tracker"
mkdir -p "$LOG_DIR"

exec 9>"$LOG_DIR/kiosk.lock"
if ! flock -n 9; then
    echo "Kiosk already running" >>"$LOG_DIR/kiosk.log"
    exit 0
fi

exec >>"$LOG_DIR/kiosk.log" 2>&1
echo "---- kiosk start $(date -Is) ----"

URL="http://127.0.0.1:5001/"

if command -v chromium >/dev/null 2>&1; then
    BROWSER="$(command -v chromium)"
elif command -v chromium-browser >/dev/null 2>&1; then
    BROWSER="$(command -v chromium-browser)"
else
    echo "chromium is not installed"
    exit 1
fi

if command -v curl >/dev/null 2>&1; then
    for _ in $(seq 1 90); do
        if curl -fsS --max-time 2 "http://127.0.0.1:5001/version" >/dev/null 2>&1; then
            break
        fi
        sleep 1
    done
else
    sleep 8
fi

wayland=0
if [ -n "${WAYLAND_DISPLAY:-}" ] || [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
    wayland=1
elif pgrep -x labwc >/dev/null 2>&1; then
    wayland=1
fi

if [ "$wayland" -eq 1 ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
    runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
    if [ -S "$runtime_dir/wayland-0" ]; then
        export WAYLAND_DISPLAY=wayland-0
    fi
fi

if [ "$wayland" -eq 1 ]; then
    # labwc blanking is a swayidle process. The panel uses layer-shell and
    # would sit on top of the board, and lwrespawn would bring it back.
    (
        for _ in $(seq 1 12); do
            pkill -x swayidle >/dev/null 2>&1 || true
            pkill -f "lwrespawn.*/wf-panel-pi" >/dev/null 2>&1 || true
            pkill -x wf-panel-pi >/dev/null 2>&1 || true
            if command -v wlopm >/dev/null 2>&1; then
                wlopm --on '*' >/dev/null 2>&1 || true
            fi
            sleep 1
        done
    ) &
elif command -v xset >/dev/null 2>&1; then
    xset s off || true
    xset -dpms || true
    xset s noblank || true
fi

PROFILE="${XDG_CONFIG_HOME:-$HOME/.config}/mta-tracker/chromium"
mkdir -p "$PROFILE"

ARGS=(
    --kiosk
    --noerrdialogs
    --disable-infobars
    --no-first-run
    --disable-session-crashed-bubble
    --disable-restore-session-state
    --disable-translate
    --disable-features=TranslateUI
    --check-for-update-interval=31536000
    --autoplay-policy=no-user-gesture-required
    --password-store=basic
    --user-data-dir="$PROFILE"
    --start-maximized
)

if [ "$wayland" -eq 1 ]; then
    # Without this, Chromium goes through Xwayland and the touchscreen misses.
    ARGS+=(--ozone-platform=wayland)
fi

while true; do
    echo "Launching $BROWSER"
    "$BROWSER" "${ARGS[@]}" "$URL" || true
    sleep 2
done
