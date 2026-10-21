#!/bin/bash
# Idempotent installer for the MTA Tracker kiosk.
# Detects the desktop user and the repo directory. Safe to run again.

set -euo pipefail

FORCE=0
DRY_RUN=0
PRINT_TARGET=0

usage() {
    cat <<'EOF'
Usage: ./install-pi.sh [--dry-run] [--print-target] [--force]

Run this on the Raspberry Pi, from the cloned repo, as the desktop user
(or with sudo from that user). It creates a virtualenv, installs the
systemd service, and turns on the labwc kiosk at login.

  --dry-run       Print the user, paths, and unit files. Change nothing.
  --print-target  Print the detected user, home, and repo directory.
  --force         Run on a machine that is not a Raspberry Pi.
EOF
}

for arg in "$@"; do
    case "$arg" in
        --force) FORCE=1 ;;
        --dry-run) DRY_RUN=1 ;;
        --print-target) PRINT_TARGET=1 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $arg" >&2; usage >&2; exit 2 ;;
    esac
done

if [ "$(id -u)" -eq 0 ]; then
    if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
        APP_USER="$SUDO_USER"
    else
        echo "Run ./install-pi.sh as the desktop user, for example rem." >&2
        echo "sudo ./install-pi.sh is fine. Running it from a root shell is not." >&2
        exit 1
    fi
else
    APP_USER="$(id -un)"
fi

APP_HOME="$(getent passwd "$APP_USER" | cut -d: -f6)"
APP_GROUP="$(id -gn "$APP_USER")"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$APP_HOME" ] || [ ! -d "$APP_HOME" ]; then
    echo "Could not find a home directory for $APP_USER." >&2
    exit 1
fi

if [ "$PRINT_TARGET" -eq 1 ]; then
    printf 'user=%s\nhome=%s\ngroup=%s\nrepo=%s\n' "$APP_USER" "$APP_HOME" "$APP_GROUP" "$APP_DIR"
    exit 0
fi

render_template() {
    local src="$1"
    sed -e "s|@APP_USER@|${APP_USER}|g" \
        -e "s|@APP_GROUP@|${APP_GROUP}|g" \
        -e "s|@APP_DIR@|${APP_DIR}|g" \
        "$src"
}

if [ "$DRY_RUN" -eq 1 ]; then
    echo "Would install for ${APP_USER} (${APP_HOME}) from ${APP_DIR}"
    echo "----- /etc/systemd/system/mta-tracker.service -----"
    render_template "$APP_DIR/mta-tracker.service.in"
    echo "----- /etc/systemd/system/mta-tracker-update.service -----"
    render_template "$APP_DIR/mta-tracker-update.service.in"
    echo "----- ${APP_HOME}/.config/labwc/autostart (managed block) -----"
    echo "${APP_DIR}/kiosk.sh &"
    exit 0
fi

is_raspberry_pi() {
    [ -r /proc/device-tree/model ] && grep -q "Raspberry Pi" /proc/device-tree/model
}

if ! is_raspberry_pi && [ "$FORCE" -ne 1 ]; then
    echo "This installer is for Raspberry Pi OS."
    if [ -t 0 ]; then
        read -r -p "Continue anyway? [y/N] " reply
        case "$reply" in
            y|Y) ;;
            *) exit 1 ;;
        esac
    else
        echo "Pass --force to run it on this machine anyway." >&2
        exit 1
    fi
fi

as_user() {
    if [ "$(id -un)" = "$APP_USER" ]; then
        "$@"
    else
        sudo -u "$APP_USER" -H -- "$@"
    fi
}

uses_labwc() {
    if command -v labwc >/dev/null 2>&1; then
        return 0
    fi
    [ -d /etc/xdg/labwc ] || [ -d /etc/xdg/labwc-pi ]
}

echo "Installing MTA Tracker for ${APP_USER} in ${APP_DIR}"

export DEBIAN_FRONTEND=noninteractive
sudo apt-get update
packages=(python3 python3-venv python3-pip git curl ca-certificates)
if apt-cache show chromium >/dev/null 2>&1; then
    packages+=(chromium)
elif apt-cache show chromium-browser >/dev/null 2>&1; then
    packages+=(chromium-browser)
else
    echo "Neither the chromium nor the chromium-browser package is available." >&2
    exit 1
fi
sudo apt-get install -y "${packages[@]}"

if [ ! -x "$APP_DIR/venv/bin/python" ]; then
    as_user python3 -m venv "$APP_DIR/venv"
fi
as_user "$APP_DIR/venv/bin/pip" install --upgrade pip
as_user "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

if [ ! -f "$APP_DIR/config.json" ]; then
    as_user cp "$APP_DIR/config.example.json" "$APP_DIR/config.json"
fi
if [ ! -f "$APP_DIR/.env" ]; then
    as_user cp "$APP_DIR/.env.example" "$APP_DIR/.env"
fi
as_user chmod +x "$APP_DIR/kiosk.sh" "$APP_DIR/update.sh" "$APP_DIR/install-pi.sh"

tmp_unit="$(mktemp)"
render_template "$APP_DIR/mta-tracker.service.in" >"$tmp_unit"
sudo cp "$tmp_unit" /etc/systemd/system/mta-tracker.service
render_template "$APP_DIR/mta-tracker-update.service.in" >"$tmp_unit"
sudo cp "$tmp_unit" /etc/systemd/system/mta-tracker-update.service
rm -f "$tmp_unit"
sudo cp "$APP_DIR/mta-tracker-update.timer" /etc/systemd/system/mta-tracker-update.timer
sudo chmod 644 /etc/systemd/system/mta-tracker.service \
    /etc/systemd/system/mta-tracker-update.service \
    /etc/systemd/system/mta-tracker-update.timer

systemctl_path="$(command -v systemctl || true)"
if [ -n "$systemctl_path" ]; then
    sudo tee /etc/sudoers.d/mta-tracker >/dev/null <<EOF
# Let the desktop user restart the board from update.sh without a password.
${APP_USER} ALL=(root) NOPASSWD: ${systemctl_path} restart mta-tracker.service
EOF
    sudo chmod 440 /etc/sudoers.d/mta-tracker
    if ! sudo visudo -cf /etc/sudoers.d/mta-tracker; then
        sudo rm -f /etc/sudoers.d/mta-tracker
        echo "Refusing to install an invalid sudoers rule." >&2
        exit 1
    fi
fi

sudo systemctl daemon-reload
sudo systemctl enable mta-tracker.service
sudo systemctl restart mta-tracker.service
sudo systemctl enable --now mta-tracker-update.timer

# Screen blanking. On labwc, raspi-config turns it on by appending swayidle
# to the user autostart. Remove those lines even if raspi-config cannot see
# the session (it only notices labwc when the process is already running).
autostart="$APP_HOME/.config/labwc/autostart"
as_user mkdir -p "$APP_HOME/.config/labwc"
as_user python3 - "$autostart" "$APP_DIR" <<'PY'
import pathlib, sys
path, app_dir = sys.argv[1:]
start = "# --- mta-tracker kiosk start ---"
end = "# --- mta-tracker kiosk end ---"
existing = pathlib.Path(path)
text = existing.read_text() if existing.exists() else ""
kept = []
skip = False
for line in text.splitlines():
    stripped = line.strip()
    if stripped == start:
        skip = True
        continue
    if stripped == end:
        skip = False
        continue
    if skip or "swayidle" in line:
        continue
    kept.append(line)
block = "\n".join([
    start,
    "# Installed by install-pi.sh. Re-running the installer replaces this block.",
    "pkill -x swayidle >/dev/null 2>&1 || true",
    f"{app_dir}/kiosk.sh &",
    end,
])
body = "\n".join(kept).rstrip()
if body:
    body += "\n"
existing.write_text(body + block + "\n")
PY

if [ -f /etc/xdg/labwc-greeter/autostart ]; then
    sudo sed -i '/swayidle/d' /etc/xdg/labwc-greeter/autostart || true
fi

# Older images blank the screen from Xorg. Harmless when the session is Wayland.
if ! uses_labwc || [ -d /etc/X11/xorg.conf.d ]; then
    sudo mkdir -p /etc/X11/xorg.conf.d
    sudo tee /etc/X11/xorg.conf.d/10-blanking.conf >/dev/null <<'EOF'
Section "Extensions"
    Option "DPMS" "Disable"
EndSection
Section "ServerFlags"
    Option "BlankTime" "0"
    Option "StandbyTime" "0"
    Option "SuspendTime" "0"
    Option "OffTime" "0"
EndSection
EOF
fi

if command -v raspi-config >/dev/null 2>&1 && pgrep -x labwc >/dev/null 2>&1; then
    sudo env USER="$APP_USER" raspi-config nonint do_blanking 1 || true
fi

# A second copy of the kiosk in the XDG autostart dir would open two browsers
# on Pi OS, because labwc merges that directory in as well.
as_user rm -f "$APP_HOME/.config/autostart/autostart-kiosk.desktop" \
    "$APP_HOME/.config/autostart/mta-tracker-kiosk.desktop" || true

if ! uses_labwc; then
    as_user mkdir -p "$APP_HOME/.config/autostart"
    cat <<EOF | as_user tee "$APP_HOME/.config/autostart/mta-tracker-kiosk.desktop" >/dev/null
[Desktop Entry]
Type=Application
Name=MTA Tracker Kiosk
Exec=${APP_DIR}/kiosk.sh
X-GNOME-Autostart-enabled=true
EOF
fi

if command -v raspi-config >/dev/null 2>&1; then
    if ! sudo env USER="$APP_USER" raspi-config nonint do_boot_behaviour B4; then
        echo "Could not set desktop autologin through raspi-config."
        sudo systemctl set-default graphical.target || true
        if [ -f /etc/lightdm/lightdm.conf ]; then
            sudo sed -i "s/^\\(#\\|\\)autologin-user=.*/autologin-user=${APP_USER}/" /etc/lightdm/lightdm.conf
        fi
    fi
else
    sudo systemctl set-default graphical.target || true
fi

echo
echo "MTA Tracker is installed for ${APP_USER}."
echo "Service:  sudo systemctl status mta-tracker.service"
echo "Updates:  ${APP_DIR}/update.sh   (also on a 6-hour timer)"
echo "Log in to the desktop, or reboot, and the board opens full screen."
echo "Put an OpenWeather key in ${APP_DIR}/.env if you want the temperature."
