#!/usr/bin/env python3
"""
Test script to verify OpenWeatherMap API key is working
Run this to debug weather API issues
"""

import os
import requests
import sys

ZIP_CODE = '10010'
WEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY', '')
WEATHER_API_URL = 'https://api.openweathermap.org/data/2.5/weather'

def test_weather_api():
    print("=" * 60)
    print("OpenWeatherMap API Test")
    print("=" * 60)
    print()
    
    # Check if API key is set
    if not WEATHER_API_KEY:
        print("❌ ERROR: OPENWEATHER_API_KEY environment variable is not set!")
        print()
        print("To set it:")
        print("  export OPENWEATHER_API_KEY='your_api_key_here'")
        print()
        print("Or on Windows:")
        print("  set OPENWEATHER_API_KEY=your_api_key_here")
        print()
        return False
    
    print(f"✓ API Key found (length: {len(WEATHER_API_KEY)} characters)")
    print(f"  Preview: {WEATHER_API_KEY[:8]}...")
    print()
    
    # Test API call
    print(f"Testing API call for zip code: {ZIP_CODE}")
    print(f"API URL: {WEATHER_API_URL}")
    print()
    
    try:
        params = {
            'zip': f'{ZIP_CODE},US',
            'appid': WEATHER_API_KEY,
            'units': 'imperial'
        }
        
        print("Making API request...")
        response = requests.get(WEATHER_API_URL, params=params, timeout=10)
        
        print(f"Response status code: {response.status_code}")
        print()
        
        if response.status_code == 401:
            print("❌ ERROR: Invalid API key!")
            print("   The API key you provided is not valid.")
            print("   Please check:")
            print("   1. You copied the key correctly")
            print("   2. The key is activated (may take a few minutes after creation)")
            print("   3. You're using the correct key from https://home.openweathermap.org/api_keys")
            print()
            print(f"   Response: {response.text}")
            return False
        
        elif response.status_code == 404:
            print(f"❌ ERROR: Location not found for zip {ZIP_CODE}")
            print(f"   Response: {response.text}")
            return False
        
        elif response.status_code != 200:
            print(f"❌ ERROR: Unexpected status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
        # Success!
        data = response.json()
        
        if 'main' not in data or 'temp' not in data['main']:
            print("❌ ERROR: Unexpected response format")
            print(f"   Response: {data}")
            return False
        
        temp = round(data['main']['temp'])
        city = data.get('name', 'Unknown')
        description = data.get('weather', [{}])[0].get('description', 'Unknown')
        
        print("✓ API call successful!")
        print()
        print(f"Location: {city}, {ZIP_CODE}")
        print(f"Temperature: {temp}°F")
        print(f"Conditions: {description}")
        print()
        print("=" * 60)
        print("✓ Weather API is working correctly!")
        print("=" * 60)
        return True
        
    except requests.exceptions.Timeout:
        print("❌ ERROR: Request timed out")
        print("   Check your internet connection")
        return False
    
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Network error: {e}")
        print("   Check your internet connection")
        return False
    
    except Exception as e:
        print(f"❌ ERROR: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_weather_api()
    sys.exit(0 if success else 1)

