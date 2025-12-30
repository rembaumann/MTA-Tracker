# Raspberry Pi Setup Guide for MTA Tracker

This guide will help you set up the MTA Tracker as an always-on display application on a Raspberry Pi.

## Hardware Recommendations

### Raspberry Pi Model
**Recommended: Raspberry Pi 4 (4GB or 8GB RAM)**
- **Why**: Better performance for web rendering, more reliable for 24/7 operation
- **Alternative**: Raspberry Pi 3B+ (works but may be slower)
- **Not recommended**: Raspberry Pi Zero (too slow for web browser)

### Display Options

#### Option 1: Official Raspberry Pi Touchscreen (7-inch)
- **Model**: Official Raspberry Pi 7" Touchscreen Display
- **Pros**: Official support, touch capability, good size for home display
- **Cons**: More expensive (~$60-70)
- **Best for**: Wall-mounted displays, interactive use

#### Option 2: HDMI Monitor/TV
- **Size**: 10-24 inches recommended
- **Pros**: Cheaper, larger display options, can use existing TV
- **Cons**: No touch, requires separate power
- **Best for**: Desktop displays, using existing monitors

#### Option 3: Small HDMI Display (5-7 inch)
- **Models**: Various 5-7" HDMI displays from Amazon/eBay
- **Pros**: Compact, affordable (~$30-50)
- **Cons**: Quality varies, may need custom mounting
- **Best for**: Compact wall displays

### Additional Hardware Needed
- MicroSD card (32GB+ recommended, Class 10 or better)
- Power supply (official Raspberry Pi power supply recommended)
- HDMI cable (if using external display)
- Case for Raspberry Pi (optional but recommended)
- MicroSD card reader (for initial setup)

## Software Setup

### Step 1: Install Raspberry Pi OS

1. Download **Raspberry Pi OS (32-bit)** from [raspberrypi.org](https://www.raspberrypi.org/software/)
2. Use Raspberry Pi Imager to write the OS to your microSD card
3. Enable SSH during setup (for headless setup)
4. Boot your Raspberry Pi

### Step 2: Initial System Configuration

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3-pip python3-venv git chromium-browser xserver-xorg xinit unclutter

# Install system dependencies for protobuf
sudo apt install -y protobuf-compiler libprotobuf-dev
```

### Step 3: Clone and Set Up the Application

```bash
# Navigate to home directory
cd ~

# Clone your repository (or copy files)
# If using git:
git clone <your-repo-url> mta-tracker
cd mta-tracker

# OR if copying files manually:
mkdir mta-tracker
cd mta-tracker
# Copy all files from your development machine here
```

### Step 4: Set Up Python Virtual Environment

```bash
cd ~/mta-tracker

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Configure the Application

Edit `app.py` to ensure it's configured for production:

```python
# Change the last line from:
app.run(debug=True, host='0.0.0.0', port=5001)

# To:
app.run(debug=False, host='0.0.0.0', port=5001)
```

### Step 6: Set Up Systemd Service (Auto-start Flask App)

```bash
# Copy the service file
sudo cp mta-tracker.service /etc/systemd/system/

# Edit the service file if needed (adjust paths)
sudo nano /etc/systemd/system/mta-tracker.service

# Reload systemd
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable mta-tracker.service

# Start the service
sudo systemctl start mta-tracker.service

# Check status
sudo systemctl status mta-tracker.service
```

### Step 7: Set Up Kiosk Mode (Auto-start Browser)

#### Option A: Using autostart (Desktop Environment)

```bash
# Create autostart directory if it doesn't exist
mkdir -p ~/.config/autostart

# Copy the desktop file
cp autostart-kiosk.desktop ~/.config/autostart/

# Make kiosk script executable
chmod +x kiosk.sh

# Edit the desktop file to ensure correct paths
nano ~/.config/autostart/autostart-kiosk.desktop
```

#### Option B: Using .xinitrc (Lightweight, No Desktop)

```bash
# Edit .xinitrc
nano ~/.xinitrc

# Add this line:
exec /home/pi/mta-tracker/kiosk.sh

# Make kiosk script executable
chmod +x kiosk.sh
```

### Step 8: Configure Auto-Login and Auto-Start X

```bash
# Enable auto-login
sudo raspi-config
# Navigate to: System Options > Boot / Auto Login > Desktop Autologin

# OR for headless/lightweight setup:
sudo raspi-config
# Navigate to: System Options > Boot / Auto Login > Console Autologin
# Then add to ~/.bashrc:
# if [ -z "$DISPLAY" ] && [ -n "$XDG_VTNR" ] && [ "$XDG_VTNR" -eq 1 ]; then
#   exec startx
# fi
```

### Step 9: Disable Screen Blanking

```bash
# Edit lightdm config (if using desktop)
sudo nano /etc/lightdm/lightdm.conf

# Under [Seat:*] section, add:
xserver-command=X -s 0 -dpms
```

### Step 10: Test the Setup

```bash
# Test Flask app manually
cd ~/mta-tracker
source venv/bin/activate
python app.py

# In another terminal, test the browser
chromium-browser --kiosk http://localhost:5001
```

## Troubleshooting

### Flask App Not Starting
```bash
# Check service logs
sudo journalctl -u mta-tracker.service -f

# Check if port is in use
sudo netstat -tulpn | grep 5001

# Restart service
sudo systemctl restart mta-tracker.service
```

### Browser Not Loading
- Check if Flask app is running: `curl http://localhost:5001`
- Check browser logs: Look for errors in the terminal
- Try accessing from another device: `http://<raspberry-pi-ip>:5001`

### Display Issues
- If display is blank, try: `sudo reboot`
- Check HDMI connection
- Try different HDMI port on Pi 4
- Adjust display settings: `sudo raspi-config` > Display Options

### Network Issues
- Ensure WiFi/Ethernet is connected
- Check internet connectivity: `ping 8.8.8.8`
- Verify MTA API is accessible

### Performance Issues
- Close unnecessary applications
- Consider overclocking (with proper cooling): `sudo raspi-config` > Performance Options
- Use a faster microSD card (Class 10 or better)

## Maintenance

### Updating the Application
```bash
cd ~/mta-tracker
git pull  # If using git
# OR manually copy updated files

# Restart service
sudo systemctl restart mta-tracker.service
```

### Viewing Logs
```bash
# Flask app logs
sudo journalctl -u mta-tracker.service -f

# System logs
journalctl -f
```

### Manual Restart
```bash
# Restart Flask service
sudo systemctl restart mta-tracker.service

# Restart entire system
sudo reboot
```

## Power Management

For 24/7 operation:
- Use official Raspberry Pi power supply (adequate amperage)
- Consider a UPS (Uninterruptible Power Supply) for power outages
- Ensure proper ventilation (use a case with cooling)

## Security Considerations

- Change default password: `passwd`
- Keep system updated: `sudo apt update && sudo apt upgrade`
- Consider firewall: `sudo ufw enable`
- If exposing to network, use proper authentication

## Cost Estimate

- Raspberry Pi 4 (4GB): ~$55
- Official 7" Touchscreen: ~$60
- MicroSD Card (32GB): ~$10
- Power Supply: ~$10
- Case: ~$10
- **Total: ~$145**

Or with HDMI display:
- Raspberry Pi 4 (4GB): ~$55
- 10" HDMI Display: ~$40
- MicroSD Card: ~$10
- Power Supply: ~$10
- **Total: ~$115**

