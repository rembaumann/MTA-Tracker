# Raspberry Pi setup

This turns a Raspberry Pi into a full-screen subway board. It was checked against a Pi 4 running Raspberry Pi OS 13 (trixie, 64-bit) with the labwc Wayland desktop. The desktop user on that machine is `rem`, and the repo lives at `/home/rem/mta-tracker`. The installer does not hardcode either of those. It uses whoever runs it, and the directory the script is in.

## Hardware

A Raspberry Pi 4 (4 GB or 8 GB) is the one this kiosk runs on. A Pi 3B+ can work and will be slower. A Pi Zero is too small for the browser.

Display options:

- Official 7-inch touchscreen. The controls are sized for that panel.
- Any HDMI monitor. Touch is optional. Previous and Next still work with a mouse, and the board cycles on its own.
- A small HDMI panel, 5 to 7 inches.

Also needed: a 32 GB or larger microSD card, a proper power supply, and an HDMI cable if the display is not the DSI panel.

## Install

Flash **Raspberry Pi OS (64-bit)** with Raspberry Pi Imager. Trixie uses Wayland and labwc by default. Create the desktop user in the imager (it is not `pi` anymore), enable SSH if you want it, and boot.

On the Pi:

```bash
sudo apt update && sudo apt upgrade -y
git clone <your-repo-url> ~/mta-tracker
cd ~/mta-tracker
./install-pi.sh
sudo reboot
```

`./install-pi.sh` is safe to run again. It will:

1. Detect the user, home directory, and repo path. `sudo ./install-pi.sh` uses `SUDO_USER`. Do not run it from a root shell.
2. Install Python, git, curl, and Chromium. On trixie the package and the command are `chromium`. Older images still have `chromium-browser`, and the script accepts either.
3. Create `venv` in the repo and install `requirements.txt`.
4. Copy `config.example.json` to `config.json`, and `.env.example` to `.env`, only if those files are missing.
5. Write and enable `/etc/systemd/system/mta-tracker.service` with the real user and paths, then start it.
6. Enable a timer that runs `update.sh` about every six hours.
7. Add a kiosk launch to `~/.config/labwc/autostart` and remove the `swayidle` line that blanks the screen.
8. Set desktop autologin when `raspi-config` is available.

After reboot the Pi should log into the desktop and open the board full screen. Chromium is started with `--ozone-platform=wayland` so the touchscreen lines up. `xset` is only used if the session is actually X11.

Put an OpenWeatherMap key in `.env` if you want the temperature, then `sudo systemctl restart mta-tracker.service`. The subway feeds do not need a key.

### Why the old unit failed

The previous `mta-tracker.service` said `User=pi` and `WorkingDirectory=/home/pi/mta-tracker`. On this Pi the account is `rem` and the clone is `/home/rem/mta-tracker`, so systemd exited with `status=217/USER` before the app started. `kiosk.sh` also called `xset` and `chromium-browser`, which belong to X11 and to older OS releases. The installer writes a unit for the user it detects, and the kiosk script targets labwc.

## Update

```bash
cd ~/mta-tracker
./update.sh
```

That fast-forwards `git pull`, runs `pip install -r requirements.txt` only when `requirements.txt` changed, and restarts `mta-tracker.service` only when the commit changed. The page polls `/version` every 20 seconds and reloads when the short commit changes, so the kiosk picks up the new code without a reboot.

The timer `mta-tracker-update.timer` runs the same script in the background. Turn it off with:

```bash
sudo systemctl disable --now mta-tracker-update.timer
```

`config.json` and `.env` are gitignored, so an update does not replace the stations or the weather key.

## What the installer writes

| File | Purpose |
| --- | --- |
| `/etc/systemd/system/mta-tracker.service` | Flask app, from `mta-tracker.service.in` |
| `/etc/systemd/system/mta-tracker-update.service` | oneshot `update.sh` |
| `/etc/systemd/system/mta-tracker-update.timer` | about every 6 hours, and 15 minutes after boot |
| `/etc/sudoers.d/mta-tracker` | lets that user restart the service without a password |
| `~/.config/labwc/autostart` | launches `kiosk.sh` and drops `swayidle` |
| `~/.local/state/mta-tracker/kiosk.log` | Chromium log |

On an image that is not running labwc, the installer falls back to `~/.config/autostart/mta-tracker-kiosk.desktop` and an Xorg config that disables DPMS. Pi OS merges labwc autostart with the system one, so the installer does not also leave an XDG autostart entry on a labwc machine. Two entries would open two browsers. `kiosk.sh` holds a lock so a second launch exits.

The kiosk stops `wf-panel-pi` so the taskbar does not sit on top of the board. Log out and back in, or reboot, if you want the normal desktop after you stop using the kiosk script.

Screen blanking on labwc is a `swayidle` line in `~/.config/labwc/autostart`, which is what `raspi-config` adds when blanking is enabled. The installer deletes those lines. `kiosk.sh` also kills `swayidle` for a few seconds at startup, because a line in the system autostart can start it after the user file runs. `xset s off` does nothing under Wayland.

## Useful commands

```bash
sudo systemctl status mta-tracker.service
sudo journalctl -u mta-tracker.service -f
systemctl list-timers mta-tracker-update.timer
curl -s http://127.0.0.1:5001/version
```

The board is also reachable from another device at `http://<pi-ip>:5001`. Anyone who can open that address can change the stations. Keep it on the home network.

## If it does not come up

**Service status 217/USER.** The unit on disk still has the wrong user. Run `./install-pi.sh` again and check `systemctl cat mta-tracker.service`. `User=` should be the desktop user, not `pi`.

**Browser never opens.** Confirm the service answers: `curl -I http://127.0.0.1:5001/version`. Then read `~/.local/state/mta-tracker/kiosk.log`. The command must be `chromium` on trixie. Autostart belongs in `~/.config/labwc/autostart`, not only in `~/.config/autostart`.

**Touch hits the wrong place.** Chromium is going through Xwayland. `kiosk.sh` should be passing `--ozone-platform=wayland`, and `WAYLAND_DISPLAY` should be set in the labwc session.

**The screen still goes black.** Look for `swayidle` in `ps aux`. Delete any `swayidle` line in `~/.config/labwc/autostart` outside the managed block, then reboot. From a desktop session, `sudo raspi-config` → Display → Screen Blanking → No does the same thing, but only when labwc is already running. Over SSH, before the desktop is up, raspi-config can miss labwc and edit the X11 config instead. The installer edits the labwc file itself for that reason.

**git pull failed in the timer.** The board keeps running the old commit. `journalctl -u mta-tracker-update.service` shows whether the Pi was offline or the branch diverged. `update.sh` only fast-forwards.

## Power

Use the official power supply. A UPS is worth it if the display should survive a short outage. Give the Pi some airflow if it is on all day.
