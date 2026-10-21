"""MTA subway arrivals board.

Stations, directions, and lines come from config.json (see config.example.json
and the settings screen). Subway GTFS-RT feeds are public and do not need an
API key. Optional secrets live in .env.
"""

import csv
import os
import threading
from collections import Counter
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, render_template, request
from google.transit import gtfs_realtime_pb2

from config_store import (
    VERSION,
    load_config,
    load_dotenv,
    normalize_config,
    save_config,
)
from gtfs_catalog import (
    GTFS_DIR,
    direction_labels,
    feed_urls_for_routes,
    get_stations,
    route_payloads,
    stations_by_id,
)

load_dotenv()

app = Flask(__name__)

latest_data = {
    "groups": [],
    "routes": [],
    "stations": [],
    "last_updated": None,
    "trains_per_page": 5,
    "cycle_seconds": 10,
    "ready": False,
    "error": None,
}
data_lock = threading.Lock()
data_wake = threading.Event()
temp_wake = threading.Event()

current_temperature = None
temperature_lock = threading.Lock()

trips_headsign_by_id = None
trips_headsign_by_route_direction = None
trips_headsign_by_platform = None

WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
MTA_API_KEY = os.environ.get("MTA_API_KEY", "").strip()
WEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "").strip()

if MTA_API_KEY:
    print("MTA API: optional key is set and will be sent as x-api-key.")
else:
    print("MTA API: no key set. Subway GTFS-RT feeds are public.")
if WEATHER_API_KEY:
    print("Weather API: key loaded from the environment.")
else:
    print("Weather API: OPENWEATHER_API_KEY is not set. Temperature stays hidden.")


def load_stops():
    stops = {}
    with open(GTFS_DIR / "stops.txt", newline="") as handle:
        for row in csv.DictReader(handle):
            stops[row["stop_id"]] = row["stop_name"]
    return stops


def load_trips_headsigns():
    """Headsigns by trip id, by route + platform, and by route + direction id.

    Realtime trip ids often do not match this static file. The L feed also
    reports direction_id 0 for both platforms, so the platform suffix (N or S)
    is the reliable fallback.
    """
    by_trip = {}
    trip_meta = {}
    direction_counts = {}
    try:
        with open(GTFS_DIR / "trips.txt", newline="") as handle:
            for row in csv.DictReader(handle):
                trip_id = row.get("trip_id")
                headsign = row.get("trip_headsign") or ""
                route_id = row.get("route_id")
                direction_id = row.get("direction_id")
                if trip_id and headsign:
                    by_trip[trip_id] = headsign
                    trip_meta[trip_id] = (route_id, direction_id, headsign)
                if route_id and direction_id is not None and headsign:
                    bucket = direction_counts.setdefault(f"{route_id}_{direction_id}", Counter())
                    bucket[headsign] += 1
        platform_counts = {}
        with open(GTFS_DIR / "stop_times.txt", newline="") as handle:
            for row in csv.DictReader(handle):
                meta = trip_meta.get(row.get("trip_id"))
                stop_id = row.get("stop_id") or ""
                if not meta or len(stop_id) < 2 or stop_id[-1] not in "NS":
                    continue
                route_id, _direction_id, headsign = meta
                if route_id and headsign:
                    bucket = platform_counts.setdefault(f"{route_id}_{stop_id[-1]}", Counter())
                    bucket[headsign] += 1
    except OSError as exc:
        print(f"Error loading trip headsigns: {exc}")
        platform_counts = {}
    by_route_direction = {
        key: counter.most_common(1)[0][0]
        for key, counter in direction_counts.items()
        if counter
    }
    by_platform = {
        key: counter.most_common(1)[0][0]
        for key, counter in platform_counts.items()
        if counter
    }
    return by_trip, by_route_direction, by_platform


def platforms_for_config(config):
    """Map a platform stop id (635N) to the routes selected for it."""
    platforms = {}
    for station in config["stations"]:
        routes = set(station["routes"])
        for direction in station["directions"]:
            platforms[f"{station['id']}{direction}"] = routes
    return platforms


def _feed_headers():
    headers = {}
    if MTA_API_KEY:
        headers["x-api-key"] = MTA_API_KEY
    return headers


def fetch_feeds(route_ids):
    """Download the GTFS-RT feeds that cover route_ids. Returns (feeds, failures)."""
    feeds = []
    failures = []
    for url in feed_urls_for_routes(route_ids):
        try:
            response = requests.get(url, headers=_feed_headers(), timeout=15)
            response.raise_for_status()
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)
            feeds.append(feed)
        except Exception as exc:
            print(f"Error loading feed {url}: {exc}")
            failures.append(url)
    return feeds, failures


def _direction_id_for(stop_id, trip):
    if trip.HasField("direction_id"):
        return trip.direction_id
    if stop_id.endswith("N"):
        return 0
    if stop_id.endswith("S"):
        return 1
    return None


def _destination_for(trip, stop_id, by_trip, by_route, by_platform):
    destination = by_trip.get(trip.trip_id, "") if by_trip else ""
    if destination:
        return destination
    if by_platform and stop_id:
        destination = by_platform.get(f"{trip.route_id}_{stop_id[-1]}", "")
        if destination:
            return destination
    direction_id = _direction_id_for(stop_id, trip)
    if direction_id is None or not by_route:
        return ""
    return by_route.get(f"{trip.route_id}_{direction_id}", "")


def collect_arrivals(
    feeds,
    config,
    stops,
    now=None,
    headsign_by_trip=None,
    headsign_by_route_direction=None,
    headsign_by_platform=None,
):
    """Group upcoming arrivals for the configured platforms."""
    if now is None:
        now = datetime.now(timezone.utc)
    by_trip = trips_headsign_by_id if headsign_by_trip is None else headsign_by_trip
    by_route = (
        trips_headsign_by_route_direction
        if headsign_by_route_direction is None
        else headsign_by_route_direction
    )
    by_platform = trips_headsign_by_platform if headsign_by_platform is None else headsign_by_platform
    lookahead = config["lookahead_minutes"]
    platforms = platforms_for_config(config)
    grouped = {stop_id: [] for stop_id in platforms}
    seen = set()

    for feed in feeds:
        for entity in feed.entity:
            if not entity.HasField("trip_update"):
                continue
            trip_update = entity.trip_update
            trip = trip_update.trip
            if trip.HasField("schedule_relationship") and trip.schedule_relationship == 3:
                continue
            for update in trip_update.stop_time_update:
                stop_id = update.stop_id
                allowed = platforms.get(stop_id)
                if allowed is None or trip.route_id not in allowed:
                    continue
                if update.HasField("schedule_relationship") and update.schedule_relationship == 1:
                    continue
                event = None
                if update.HasField("arrival") and update.arrival.HasField("time"):
                    event = update.arrival
                elif update.HasField("departure") and update.departure.HasField("time"):
                    event = update.departure
                if event is None:
                    continue
                arrival = datetime.fromtimestamp(event.time, tz=timezone.utc)
                minutes = (arrival - now).total_seconds() / 60
                if minutes < 0 or minutes > lookahead:
                    continue
                dedupe_key = (trip.trip_id, stop_id)
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                grouped[stop_id].append({
                    "route": trip.route_id,
                    "minutes": round(minutes, 2),
                    "destination": _destination_for(trip, stop_id, by_trip, by_route, by_platform),
                })

    order = {station["id"]: index for index, station in enumerate(config["stations"])}
    groups = []
    for stop_id, trains in grouped.items():
        if not trains:
            continue
        trains.sort(key=lambda train: train["minutes"])
        parent_id = stop_id[:-1]
        direction_id = stop_id[-1]
        route_ids = [train["route"] for train in trains]
        north, south = direction_labels(route_ids)
        groups.append({
            "station": stops.get(parent_id) or stops.get(stop_id) or parent_id,
            "station_id": stop_id,
            "parent_id": parent_id,
            "direction": north if direction_id == "N" else south,
            "direction_id": direction_id,
            "trains": trains,
        })
    groups.sort(key=lambda group: (
        order.get(group["parent_id"], 999),
        0 if group["direction_id"] == "N" else 1,
        group["station_id"],
    ))
    return groups


def configured_route_ids(config):
    route_ids = []
    for station in config["stations"]:
        for route_id in station["routes"]:
            if route_id not in route_ids:
                route_ids.append(route_id)
    return route_ids


def board_stations(config):
    """Saved stations in rotation order, with only the lines turned on for each."""
    catalog = stations_by_id()
    stations = []
    for station in config["stations"]:
        known = catalog.get(station["id"], {})
        stations.append({
            "id": station["id"],
            "name": known.get("name", station["id"]),
            "routes": route_payloads(station["routes"]),
        })
    return stations


def fetch_mta_data():
    """Refresh the in-memory board from the configured stations."""
    global latest_data
    global trips_headsign_by_id
    global trips_headsign_by_route_direction
    global trips_headsign_by_platform

    config = load_config()
    stops = load_stops()
    if trips_headsign_by_id is None:
        (
            trips_headsign_by_id,
            trips_headsign_by_route_direction,
            trips_headsign_by_platform,
        ) = load_trips_headsigns()

    route_ids = configured_route_ids(config)
    feeds, failures = fetch_feeds(route_ids)
    groups = collect_arrivals(feeds, config, stops) if feeds else []
    error = None
    if route_ids and not feeds:
        error = "Could not reach the MTA feeds."
    elif failures and not groups:
        error = "Some MTA feeds did not respond."

    payload = {
        "groups": groups,
        "routes": route_payloads(route_ids),
        "stations": board_stations(config),
        "last_updated": datetime.now().strftime("%H:%M:%S"),
        "trains_per_page": config["trains_per_page"],
        "cycle_seconds": config["cycle_seconds"],
        "ready": True,
        "error": error,
        "version": VERSION,
    }
    with data_lock:
        latest_data = payload


def fetch_temperature():
    global current_temperature
    if not WEATHER_API_KEY:
        with temperature_lock:
            current_temperature = None
        return

    zip_code = load_config()["zip_code"]
    try:
        response = requests.get(
            WEATHER_API_URL,
            params={"zip": f"{zip_code},US", "appid": WEATHER_API_KEY, "units": "imperial"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        temp = round(data["main"]["temp"])
        with temperature_lock:
            current_temperature = temp
        print(f"Temperature updated: {temp} F for {zip_code}")
    except Exception as exc:
        print(f"Error fetching temperature: {exc}")
        with temperature_lock:
            current_temperature = None


def data_updater():
    while True:
        try:
            fetch_mta_data()
        except Exception as exc:
            print(f"Error updating data: {exc}")
            with data_lock:
                latest_data["ready"] = True
                latest_data["error"] = "Could not update train data."
        if data_wake.wait(30):
            data_wake.clear()


def temperature_updater():
    while True:
        try:
            fetch_temperature()
        except Exception as exc:
            print(f"Error updating temperature: {exc}")
        if temp_wake.wait(300):
            temp_wake.clear()


def start_background_threads():
    threading.Thread(target=data_updater, daemon=True).start()
    threading.Thread(target=temperature_updater, daemon=True).start()


@app.after_request
def disable_cache(response):
    if request.path == "/" or request.path.startswith(("/settings", "/version", "/api/")):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/")
def index():
    return render_template("index.html", version=VERSION)


@app.route("/settings")
def settings_page():
    return render_template("settings.html", version=VERSION)


@app.route("/version")
def version():
    return jsonify({"version": VERSION})


@app.route("/api/stations")
def api_stations():
    return jsonify({"stations": get_stations()})


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "GET":
        return jsonify(load_config())

    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"ok": False, "errors": ["Expected a JSON body."]}), 400
    config, errors = normalize_config(payload, stations_by_id(), strict=True)
    if errors or not config["stations"]:
        return jsonify({"ok": False, "errors": errors or ["Choose at least one station."]}), 400
    save_config(config)
    data_wake.set()
    temp_wake.set()
    return jsonify({"ok": True, "config": config})


@app.route("/api/data")
def get_data():
    with data_lock:
        data = dict(latest_data)
        data["groups"] = list(latest_data.get("groups", []))
    with temperature_lock:
        data["temperature"] = current_temperature
    data["version"] = VERSION
    return jsonify(data)


@app.route("/api/temperature")
def get_temperature():
    with temperature_lock:
        temp = current_temperature
    return jsonify({
        "temperature": temp,
        "api_key_set": bool(WEATHER_API_KEY),
        "zip_code": load_config()["zip_code"],
    })


@app.route("/api/debug/weather")
def debug_weather():
    """Weather status without revealing the key."""
    with temperature_lock:
        temp = current_temperature
    return jsonify({
        "api_key_set": bool(WEATHER_API_KEY),
        "zip_code": load_config()["zip_code"],
        "current_temperature": temp,
    })


if __name__ == "__main__":
    print(f"MTA Tracker {VERSION}")
    print("Loading the station catalog...")
    station_count = len(get_stations())
    print(f"Loaded {station_count} stations from GTFS.")
    config = load_config()
    chosen = ", ".join(station["id"] for station in config["stations"])
    print(f"Showing stations: {chosen}")
    start_background_threads()
    app.run(debug=False, host="0.0.0.0", port=5001)
