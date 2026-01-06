from flask import Flask, render_template, jsonify
from google.transit import gtfs_realtime_pb2
import requests
import csv
import os
from datetime import datetime, timezone
import threading
import time

app = Flask(__name__)

# Global variables to store the latest data
latest_data = {}
data_lock = threading.Lock()
trips_headsign_by_id = None
trips_headsign_by_route_direction = None
current_temperature = None
temperature_lock = threading.Lock()

# Weather API configuration
ZIP_CODE = '10010'
WEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY', '')  # Set via environment variable
WEATHER_API_URL = 'https://api.openweathermap.org/data/2.5/weather'

# Debug: Print API key status on startup
if WEATHER_API_KEY:
    print(f"Weather API: Key found (length: {len(WEATHER_API_KEY)})")
else:
    print("Weather API: WARNING - OPENWEATHER_API_KEY not set!")
    print("  Set it with: export OPENWEATHER_API_KEY='your_key_here'")

def load_stops_data():
    """Load stops data into a dictionary for fast lookup"""
    stops = {}
    stops_file = os.path.join(os.path.dirname(__file__), 'gtfs_subway', 'stops.txt')
    
    with open(stops_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stops[row['stop_id']] = row['stop_name']
    
    return stops

def load_trips_headsigns():
    """Load trip headsigns keyed by trip_id from trips.txt (GTFS static)."""
    trips_file = os.path.join(os.path.dirname(__file__), 'gtfs_subway', 'trips.txt')
    headsign_by_trip_id = {}
    headsign_by_route_direction = {}  # New: route_id + direction_id -> headsign
    try:
        with open(trips_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                trip_id = row.get('trip_id')
                headsign = row.get('trip_headsign')
                route_id = row.get('route_id')
                direction_id = row.get('direction_id')
                
                if trip_id and headsign:
                    headsign_by_trip_id[trip_id] = headsign
                
                # Also build route+direction lookup
                if route_id and direction_id is not None and headsign:
                    key = f"{route_id}_{direction_id}"
                    if key not in headsign_by_route_direction:
                        headsign_by_route_direction[key] = set()
                    headsign_by_route_direction[key].add(headsign)
    except Exception as e:
        print(f"Error loading trips headsigns: {e}")
    
    # Convert sets to most common headsign for each route+direction
    for key, headsigns in headsign_by_route_direction.items():
        # Use the first headsign (they should be consistent for a route+direction)
        headsign_by_route_direction[key] = list(headsigns)[0]
    
    return headsign_by_trip_id, headsign_by_route_direction

def fetch_mta_data():
    """Fetch and process MTA data"""
    global latest_data
    global trips_headsign_by_id
    global trips_headsign_by_route_direction
    
    # Load stops data
    stops = load_stops_data()
    # Lazy-load trips headsigns once per process
    if trips_headsign_by_id is None:
        trips_headsign_by_id, trips_headsign_by_route_direction = load_trips_headsigns()
        print(f"Loaded {len(trips_headsign_by_id)} trip headsigns and {len(trips_headsign_by_route_direction)} route+direction headsigns")
    
    # Fetch data from multiple endpoints
    feeds = []
    endpoints = [
        'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw',
        'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',
        'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l'
    ]

    for endpoint in endpoints:
        try:
            response = requests.get(endpoint)
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)
            feeds.append(feed)
        except Exception as e:
            print(f"Error loading feed from {endpoint}: {e}")

    # Combine all entities from all feeds
    all_entities = []
    for feed in feeds:
        all_entities.extend(feed.entity)

    # Get current time
    current_time = datetime.now(timezone.utc)

    # Dictionary to group results by station and direction
    grouped_results = {}

    for entity in all_entities:
        if entity.HasField('trip_update'):
            trip_update = entity.trip_update
            
            # Process stop time updates and filter for my stops
            for stop_time_update in trip_update.stop_time_update:
                stop_id = stop_time_update.stop_id
                stop_name = stops.get(stop_id, f"Unknown stop ({stop_id})")
                
                # Filter for specific stop_ids and check arrival time
                if stop_id in ["634N", "634S", "635N", "635S", "L03N", "L03S", "R19N", "R19S", "R20N", "R20S"] and stop_time_update.HasField('arrival'):
                    arrival_time = datetime.fromtimestamp(stop_time_update.arrival.time, tz=timezone.utc)
                    minutes_from_now = (arrival_time - current_time).total_seconds() / 60
                    
                    # Only include arrivals within the next 10 minutes
                    if 0 <= minutes_from_now <= 10:
                        # Determine direction from stop_id or trip direction
                        direction = "Unknown"
                        if trip_update.trip.HasField('direction_id'):
                            direction = "Northbound" if trip_update.trip.direction_id == 0 else "Southbound"
                        else:
                            # Fallback: determine from stop_id suffix
                            if stop_id.endswith('N'):
                                direction = "Northbound"
                            elif stop_id.endswith('S'):
                                direction = "Southbound"
                        
                        # Convert direction labels for non-L trains
                        if trip_update.trip.route_id != 'L':
                            if direction == "Northbound":
                                direction = "Uptown"
                            elif direction == "Southbound":
                                direction = "Downtown"
                        
                        # Create key for grouping by station ID instead of station name
                        group_key = (stop_id, direction)
                        
                        # Initialize group if it doesn't exist
                        if group_key not in grouped_results:
                            grouped_results[group_key] = []
                        
                        # Try to get destination from trip_id first, then route+direction
                        trip_id = trip_update.trip.trip_id
                        destination = trips_headsign_by_id.get(trip_id, '')
                        
                        # If no destination from trip_id, try route+direction lookup
                        if not destination:
                            direction_id = None
                            if trip_update.trip.HasField('direction_id'):
                                direction_id = trip_update.trip.direction_id
                            else:
                                # Fallback: determine direction from stop_id suffix
                                if stop_id.endswith('N'):
                                    direction_id = 0  # Northbound
                                elif stop_id.endswith('S'):
                                    direction_id = 1  # Southbound
                            
                            if direction_id is not None:
                                route_direction_key = f"{trip_update.trip.route_id}_{direction_id}"
                                destination = trips_headsign_by_route_direction.get(route_direction_key, '')
                                # Destination found or not found - no need to log every lookup
                        
                        # Add train info to the group
                        grouped_results[group_key].append({
                            'route': trip_update.trip.route_id,
                            'minutes': minutes_from_now,
                            'stop_id': stop_id,
                            'destination': destination
                        })

    # Process and organize the data for display with pagination
    processed_data = []
    
    for (stop_id, direction), trains in grouped_results.items():
        # Get station name from stop_id
        stop_name = stops.get(stop_id, f"Unknown stop ({stop_id})")
        
        # Sort trains by arrival time (soonest first)
        trains.sort(key=lambda x: x['minutes'])
        
        # Separate L trains from other trains
        l_trains = [train for train in trains if train['route'] == 'L']
        other_trains = [train for train in trains if train['route'] != 'L']
        
        # Process L trains separately with custom direction names
        if l_trains:
            # Reclassify L train directions
            l_direction = "Manhattan Bound" if direction == "Northbound" else "Brooklyn Bound"
            
            # Paginate L trains - show 5 per page
            trains_per_page = 5
            total_pages = (len(l_trains) + trains_per_page - 1) // trains_per_page  # Ceiling division
            
            for page in range(total_pages):
                start_idx = page * trains_per_page
                end_idx = min(start_idx + trains_per_page, len(l_trains))
                page_trains = l_trains[start_idx:end_idx]
                
                processed_data.append({
                    'station': stop_name,
                    'station_id': stop_id,
                    'direction': l_direction,
                    'trains': page_trains,
                    'page': page + 1,
                    'total_pages': total_pages,
                    'line_type': 'L Train'
                })
        
        # Process other trains with original direction names
        if other_trains:
            # Paginate other trains - show 5 per page
            trains_per_page = 5
            total_pages = (len(other_trains) + trains_per_page - 1) // trains_per_page  # Ceiling division
            
            for page in range(total_pages):
                start_idx = page * trains_per_page
                end_idx = min(start_idx + trains_per_page, len(other_trains))
                page_trains = other_trains[start_idx:end_idx]
                
                processed_data.append({
                    'station': stop_name,
                    'station_id': stop_id,
                    'direction': direction,
                    'trains': page_trains,
                    'page': page + 1,
                    'total_pages': total_pages,
                    'line_type': 'Other Lines'
                })
    
    # Update global data with thread safety
    with data_lock:
        latest_data = {
            'data': processed_data,
            'last_updated': datetime.now().strftime('%H:%M:%S'),
            'total_sections': len(processed_data)
        }

def fetch_temperature():
    """Fetch current temperature from OpenWeatherMap API"""
    global current_temperature
    
    if not WEATHER_API_KEY:
        print("Warning: OPENWEATHER_API_KEY not set. Temperature will not be available.")
        with temperature_lock:
            current_temperature = None
        return
    
    try:
        params = {
            'zip': f'{ZIP_CODE},US',
            'appid': WEATHER_API_KEY,
            'units': 'imperial'  # Get temperature in Fahrenheit
        }
        print(f"Fetching temperature for zip {ZIP_CODE}...")
        response = requests.get(WEATHER_API_URL, params=params, timeout=10)
        
        # Check for API errors
        if response.status_code == 401:
            print("ERROR: Invalid API key. Please check your OPENWEATHER_API_KEY.")
            print(f"  Response: {response.text}")
            with temperature_lock:
                current_temperature = None
            return
        elif response.status_code == 404:
            print(f"ERROR: Location not found for zip {ZIP_CODE}")
            print(f"  Response: {response.text}")
            with temperature_lock:
                current_temperature = None
            return
        
        response.raise_for_status()
        data = response.json()
        
        if 'main' not in data or 'temp' not in data['main']:
            print(f"ERROR: Unexpected API response format: {data}")
            with temperature_lock:
                current_temperature = None
            return
        
        temp = round(data['main']['temp'])
        with temperature_lock:
            current_temperature = temp
        print(f"✓ Temperature updated: {temp}°F for {ZIP_CODE}")
    except requests.exceptions.Timeout:
        print("ERROR: Timeout fetching temperature from OpenWeatherMap API")
        with temperature_lock:
            current_temperature = None
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Network error fetching temperature: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response status: {e.response.status_code}")
            print(f"  Response text: {e.response.text}")
        with temperature_lock:
            current_temperature = None
    except Exception as e:
        print(f"ERROR: Unexpected error fetching temperature: {e}")
        import traceback
        traceback.print_exc()
        with temperature_lock:
            current_temperature = None

def data_updater():
    """Background thread to continuously update MTA data"""
    while True:
        try:
            fetch_mta_data()
            time.sleep(30)  # Update every 30 seconds
        except Exception as e:
            print(f"Error updating data: {e}")
            time.sleep(60)  # Wait longer on error

def temperature_updater():
    """Background thread to continuously update temperature"""
    # Initial fetch
    fetch_temperature()
    
    while True:
        try:
            time.sleep(300)  # Update every 5 minutes (weather doesn't change as frequently)
            fetch_temperature()
        except Exception as e:
            print(f"Error updating temperature: {e}")
            time.sleep(600)  # Wait longer on error

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    with data_lock:
        data = latest_data.copy()
    
    # Add temperature to response
    with temperature_lock:
        data['temperature'] = current_temperature
    
    return jsonify(data)

@app.route('/api/temperature')
def get_temperature():
    with temperature_lock:
        return jsonify({
            'temperature': current_temperature,
            'api_key_set': bool(WEATHER_API_KEY),
            'zip_code': ZIP_CODE
        })

@app.route('/api/debug/weather')
def debug_weather():
    """Debug endpoint to check weather API status"""
    with temperature_lock:
        temp = current_temperature
    
    return jsonify({
        'api_key_set': bool(WEATHER_API_KEY),
        'api_key_length': len(WEATHER_API_KEY) if WEATHER_API_KEY else 0,
        'api_key_preview': WEATHER_API_KEY[:8] + '...' if WEATHER_API_KEY and len(WEATHER_API_KEY) > 8 else 'Not set',
        'zip_code': ZIP_CODE,
        'current_temperature': temp,
        'api_url': WEATHER_API_URL
    })

if __name__ == '__main__':
    # Start background thread for data updates
    updater_thread = threading.Thread(target=data_updater, daemon=True)
    updater_thread.start()
    
    # Start background thread for temperature updates
    temp_thread = threading.Thread(target=temperature_updater, daemon=True)
    temp_thread.start()
    
    # Initial data fetch
    fetch_mta_data()
    
    # Production mode: debug=False for better performance
    # Set debug=True only for development
    app.run(debug=False, host='0.0.0.0', port=5001)
