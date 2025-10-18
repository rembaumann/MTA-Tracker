from google.transit import gtfs_realtime_pb2
import requests
import csv
import os
from datetime import datetime, timezone

# Load stops data into a dictionary for fast lookup
stops = {}
stops_file = os.path.join(os.path.dirname(__file__), 'gtfs_subway', 'stops.txt')

with open(stops_file, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        stops[row['stop_id']] = row['stop_name']

# Fetch data from both endpoints
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

# Debug counters
total_entities = 0
trip_updates = 0
matching_stops = 0
# print(f"Processing {len(all_entities)} total entities...")

for entity in all_entities:
    total_entities += 1
    if entity.HasField('trip_update'):
        trip_updates += 1
        trip_update = entity.trip_update
        
        # Process stop time updates and filter for my stops
        for stop_time_update in trip_update.stop_time_update:
            stop_id = stop_time_update.stop_id
            stop_name = stops.get(stop_id, f"Unknown stop ({stop_id})")
            
            # Debug: print first few matching stops
            if stop_id in ["634N", "634S", "635N", "635S", "L03N", "L03S"]:
                matching_stops += 1
                # if matching_stops <= 5:  # Print first 5 matches for debugging
                #     print(f"Found stop: {stop_id} ({stop_name}) - Route: {trip_update.trip.route_id}")
            
            # Filter for specific stop_ids and check arrival time
            if stop_id in ["634N", "634S", "635N", "635S", "L03N", "L03S"] and stop_time_update.HasField('arrival'):
                arrival_time = datetime.fromtimestamp(stop_time_update.arrival.time, tz=timezone.utc)
                minutes_from_now = (arrival_time - current_time).total_seconds() / 60
                
                # Only include arrivals within the next 20 minutes
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
                    
                    # Create key for grouping
                    group_key = (stop_name, direction)
                    
                    # Initialize group if it doesn't exist
                    if group_key not in grouped_results:
                        grouped_results[group_key] = []
                    
                    # Add train info to the group
                    grouped_results[group_key].append({
                        'route': trip_update.trip.route_id,
                        'minutes': minutes_from_now,
                        'stop_id': stop_id
                    })

# # Debug summary
# print(f"\nDebug Summary:")
# print(f"Total entities processed: {total_entities}")
# print(f"Trip updates found: {trip_updates}")
# print(f"Matching stops found: {matching_stops}")
# print(f"Results to display: {len(grouped_results)} groups")

# Sort and display results
for (stop_name, direction), trains in grouped_results.items():
    # Sort trains by arrival time (soonest first)
    trains.sort(key=lambda x: x['minutes'])
    
    # Separate L trains from other trains for 14 St-Union Sq
    if stop_name == "14 St-Union Sq":
        l_trains = [train for train in trains if train['route'] == 'L']
        other_trains = [train for train in trains if train['route'] != 'L']
        
        # Display L trains separately
        if l_trains:
            print(f"{stop_name} - L Train - {direction}:")
            for train in l_trains:
                print(f"  {train['route']} Train: {train['minutes']:.1f} min")
            print()
        
        # Display other trains
        if other_trains:
            print(f"{stop_name} - {direction}:")
            for train in other_trains:
                print(f"  {train['route']} Train: {train['minutes']:.1f} min")
            print()
    else:
        # For other stations, display normally
        print(f"{stop_name} - {direction}:")
        for train in trains:
            print(f"  {train['route']} Train: {train['minutes']:.1f} min")
        print()