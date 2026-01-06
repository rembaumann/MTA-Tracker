# Weather API Setup

The MTA Tracker now displays the current temperature in the top right corner. To enable this feature, you need to set up a free OpenWeatherMap API key.

## Getting an API Key

1. **Sign up for a free account:**
   - Visit [OpenWeatherMap](https://openweathermap.org/api)
   - Click "Sign Up" or "Sign In" if you already have an account
   - Create a free account (no credit card required)

2. **Get your API key:**
   - After signing up, go to the [API keys page](https://home.openweathermap.org/api_keys)
   - You'll see your default API key, or you can create a new one
   - Copy the API key

## Setting Up the API Key

### Option 1: Environment Variable (Recommended)

**On your development machine:**
```bash
export OPENWEATHER_API_KEY='your_api_key_here'
```

**On Raspberry Pi:**
Add to your systemd service file or set it in your shell:
```bash
export OPENWEATHER_API_KEY='your_api_key_here'
```

Or add it to your `~/.bashrc` or `~/.profile`:
```bash
echo 'export OPENWEATHER_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

### Option 2: Update systemd Service

Edit `/etc/systemd/system/mta-tracker.service`:
```ini
[Service]
Environment="OPENWEATHER_API_KEY=your_api_key_here"
```

Then reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart mta-tracker.service
```

## Verification

After setting up the API key:
1. Restart the Flask application
2. Check the browser console or Flask logs for any errors
3. The temperature should appear in the top right corner within a few minutes

## Free Tier Limits

The free tier includes:
- 60 calls/minute
- 1,000,000 calls/month
- Current weather data
- 5-day/3-hour forecast

This is more than sufficient for the MTA Tracker, which updates temperature every 5 minutes.

## Troubleshooting

**Temperature not showing:**
- Check that the API key is set correctly: `echo $OPENWEATHER_API_KEY`
- Check Flask logs for error messages
- Verify your internet connection
- The API key may take a few minutes to activate after creation

**Error messages:**
- "Invalid API key" - Check that you copied the key correctly
- "API key not set" - Make sure the environment variable is set
- Network errors - Check your internet connection

## Current Configuration

- **Zip Code:** 10010 (New York, NY)
- **Update Frequency:** Every 5 minutes
- **Temperature Unit:** Fahrenheit (°F)

To change the zip code, edit `ZIP_CODE` in `app.py`.

