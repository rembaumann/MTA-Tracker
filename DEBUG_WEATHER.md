# Debugging Weather API Issues

If the temperature is not showing up, follow these steps to debug:

## Step 1: Verify Environment Variable is Set

**Check if the variable is set:**
```bash
echo $OPENWEATHER_API_KEY
```

**If it's empty, set it:**
```bash
export OPENWEATHER_API_KEY='your_api_key_here'
```

**For permanent setup, add to your shell profile:**
```bash
# For bash
echo 'export OPENWEATHER_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc

# For zsh
echo 'export OPENWEATHER_API_KEY="your_api_key_here"' >> ~/.zshrc
source ~/.zshrc
```

## Step 2: Test the API Key

Run the test script:
```bash
cd /path/to/MTA-Tracker
python3 test_weather_api.py
```

This will tell you:
- ✅ If the API key is set correctly
- ✅ If the API key is valid
- ✅ If the API call works
- ❌ Any specific errors

## Step 3: Check Flask Application Logs

When you start the Flask app, you should see:
```
Weather API: Key found (length: 32)
```

If you see:
```
Weather API: WARNING - OPENWEATHER_API_KEY not set!
```

Then the environment variable is not being read by the Flask app.

## Step 4: Check Browser Console

1. Open the app in your browser
2. Open Developer Tools (F12 or Cmd+Option+I)
3. Go to the Console tab
4. Look for messages like:
   - `Weather API Debug Info: {...}`
   - `Temperature API response: {...}`
   - Any error messages

## Step 5: Test the Debug Endpoint

Visit in your browser:
```
http://localhost:5001/api/debug/weather
```

This will show you:
- Whether the API key is set
- The current temperature value
- Any configuration issues

## Step 6: Check Flask Logs for Errors

Look for error messages in your Flask console output:
- `ERROR: Invalid API key` - Your API key is wrong
- `ERROR: Timeout` - Network issue
- `ERROR: Location not found` - Zip code issue

## Common Issues

### Issue: "API key not set" but you set it
**Solution:**
- Make sure you set it in the same terminal session where Flask is running
- Or restart Flask after setting the variable
- If using systemd, add it to the service file (see WEATHER_SETUP.md)

### Issue: "Invalid API key"
**Solution:**
- Double-check you copied the entire key
- API keys may take a few minutes to activate after creation
- Make sure you're using the key from https://home.openweathermap.org/api_keys

### Issue: Temperature shows "--" but API key is set
**Solution:**
- Check Flask logs for error messages
- Wait a few minutes (temperature updates every 5 minutes)
- Check browser console for JavaScript errors
- Try visiting `/api/temperature` directly in your browser

### Issue: Works in test script but not in Flask
**Solution:**
- Flask may be running in a different environment
- If using systemd, add the environment variable to the service file
- Restart the Flask application after setting the variable

## Systemd Service Setup

If using systemd, edit `/etc/systemd/system/mta-tracker.service`:

```ini
[Service]
Environment="OPENWEATHER_API_KEY=your_api_key_here"
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl restart mta-tracker.service
sudo systemctl status mta-tracker.service
```

## Manual Testing

You can also test the API directly:

```bash
# Replace YOUR_API_KEY with your actual key
curl "https://api.openweathermap.org/data/2.5/weather?zip=10010,US&appid=YOUR_API_KEY&units=imperial"
```

This should return JSON with temperature data.

## Still Not Working?

1. Run the test script and share the output
2. Check Flask logs and share any error messages
3. Check browser console and share any JavaScript errors
4. Verify your API key is active at https://home.openweathermap.org/api_keys

