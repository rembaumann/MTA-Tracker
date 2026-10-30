#!/bin/bash
# Pull the latest board, install requirements when they changed, and restart.
# The page polls /version and reloads itself after the restart.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

if [ ! -d "$REPO_DIR/.git" ]; then
    echo "This directory is not a git checkout, so there is nothing to pull."
    exit 1
fi

if [ ! -x "$REPO_DIR/venv/bin/python" ]; then
    echo "No virtualenv at $REPO_DIR/venv. Run ./install-pi.sh first."
    exit 1
fi

if [ "$(id -u)" -eq 0 ]; then
    APP_USER="$(stat -c '%U' "$REPO_DIR")"
    run_as_owner() { sudo -u "$APP_USER" -H "$@"; }
    restart_service() { systemctl restart mta-tracker.service; }
else
    run_as_owner() { "$@"; }
    restart_service() { sudo systemctl restart mta-tracker.service; }
fi

old_rev="$(run_as_owner git rev-parse HEAD)"
old_req="$(sha256sum "$REPO_DIR/requirements.txt" | awk '{print $1}')"

if ! run_as_owner git pull --ff-only; then
    echo "git pull failed. The board is still running $(run_as_owner git rev-parse --short HEAD)."
    exit 1
fi

new_rev="$(run_as_owner git rev-parse HEAD)"
new_req="$(sha256sum "$REPO_DIR/requirements.txt" | awk '{print $1}')"

if [ "$old_rev" = "$new_rev" ]; then
    echo "Already up to date ($(run_as_owner git rev-parse --short HEAD))."
    exit 0
fi

if [ "$old_req" != "$new_req" ]; then
    echo "requirements.txt changed; installing."
    run_as_owner "$REPO_DIR/venv/bin/pip" install -r "$REPO_DIR/requirements.txt"
fi

restart_service
echo "Updated to $(run_as_owner git rev-parse --short HEAD). The kiosk reloads when it sees the new version."
