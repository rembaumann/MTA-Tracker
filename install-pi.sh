#!/bin/bash

# MTA Tracker Raspberry Pi Installation Script
# Run this script on your Raspberry Pi to set up the application

set -e  # Exit on error

echo "========================================="
echo "MTA Tracker Raspberry Pi Installation"
echo "========================================="
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "Warning: This script is designed for Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INSTALL_DIR="$HOME/mta-tracker"

echo "Installing to: $INSTALL_DIR"
echo ""

# Create installation directory
mkdir -p "$INSTALL_DIR"

# Copy files
echo "Copying application files..."
cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/" 2>/dev/null || true
cd "$INSTALL_DIR"

# Install system packages
echo "Installing system packages..."
sudo apt update
sudo apt install -y python3-pip python3-venv git chromium-browser xserver-xorg xinit unclutter protobuf-compiler libprotobuf-dev

# Create virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Make scripts executable
chmod +x kiosk.sh

# Set up systemd service
echo "Setting up systemd service..."
sudo cp mta-tracker.service /etc/systemd/system/
sudo sed -i "s|/home/pi/mta-tracker|$INSTALL_DIR|g" /etc/systemd/system/mta-tracker.service
sudo systemctl daemon-reload
sudo systemctl enable mta-tracker.service

# Set up autostart
echo "Setting up autostart..."
mkdir -p ~/.config/autostart
cp autostart-kiosk.desktop ~/.config/autostart/
sed -i "s|/home/pi/mta-tracker|$INSTALL_DIR|g" ~/.config/autostart/autostart-kiosk.desktop

# Start the service
echo "Starting MTA Tracker service..."
sudo systemctl start mta-tracker.service

# Wait a moment for service to start
sleep 3

# Check service status
if sudo systemctl is-active --quiet mta-tracker.service; then
    echo "✓ MTA Tracker service is running"
else
    echo "✗ MTA Tracker service failed to start"
    echo "Check logs with: sudo journalctl -u mta-tracker.service -f"
fi

echo ""
echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Configure auto-login: sudo raspi-config"
echo "   Navigate to: System Options > Boot / Auto Login > Desktop Autologin"
echo ""
echo "2. Disable screen blanking:"
echo "   sudo nano /etc/lightdm/lightdm.conf"
echo "   Add under [Seat:*]: xserver-command=X -s 0 -dpms"
echo ""
echo "3. Reboot to test: sudo reboot"
echo ""
echo "To check service status: sudo systemctl status mta-tracker.service"
echo "To view logs: sudo journalctl -u mta-tracker.service -f"
echo ""

