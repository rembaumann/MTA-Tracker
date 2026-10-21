"""Station and route catalog built from the bundled GTFS static files."""

import csv
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
GTFS_DIR = BASE_DIR / "gtfs_subway"

# Confirmed against the live feeds on 2026-10-21. Z travels with J, FX with F,
# and 5X with 5 even when those trips are not in the feed at the moment.
ROUTE_FEED = {
    "1": "gtfs",
    "2": "gtfs",
    "3": "gtfs",
    "4": "gtfs",
    "5": "gtfs",
    "5X": "gtfs",
    "6": "gtfs",
    "6X": "gtfs",
    "7": "gtfs",
    "7X": "gtfs",
    "GS": "gtfs",
    "A": "ace",
    "C": "ace",
    "E": "ace",
    "H": "ace",
    "B": "bdfm",
    "D": "bdfm",
    "F": "bdfm",
    "FX": "bdfm",
    "FS": "bdfm",
    "M": "bdfm",
    "G": "g",
    "J": "jz",
    "Z": "jz",
    "L": "l",
    "N": "nqrw",
    "Q": "nqrw",
    "R": "nqrw",
    "W": "nqrw",
    "SI": "si",
}

# The slash inside the path must stay percent-encoded. A decoded slash is rejected.
FEED_URLS = {
    "gtfs": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
    "ace": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",
    "bdfm": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",
    "g": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g",
    "jz": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz",
    "l": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l",
    "nqrw": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",
    "si": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si",
}

# North label, south label. Routes that are not listed use Uptown / Downtown.
# Labels follow the GTFS headsign on each platform (N suffix vs S suffix).
SPECIAL_DIRECTIONS = {
    "L": ("Manhattan", "Brooklyn"),
    "7": ("Queens", "Manhattan"),
    "7X": ("Queens", "Manhattan"),
    "G": ("Queens", "Brooklyn"),
    "GS": ("Times Sq", "Grand Central"),
    "FS": ("Franklin Av", "Prospect Park"),
    "H": ("Broad Channel", "Rockaway"),
    "SI": ("St George", "Tottenville"),
}

ROUTE_ORDER = [
    "1", "2", "3", "4", "5", "5X", "6", "6X", "7", "7X",
    "A", "C", "E", "H", "B", "D", "F", "FX", "FS", "M",
    "G", "J", "Z", "L", "N", "Q", "R", "W", "GS", "SI",
]
_ORDER_INDEX = {route_id: index for index, route_id in enumerate(ROUTE_ORDER)}

_cache = None
_cache_lock = threading.Lock()


def route_sort_key(route_id):
    return (_ORDER_INDEX.get(route_id, len(ROUTE_ORDER)), route_id)


def direction_labels(route_ids):
    """Short platform labels for a set of routes that share a station."""
    specials = []
    has_regular = False
    for route_id in route_ids:
        labels = SPECIAL_DIRECTIONS.get(route_id)
        if labels:
            specials.append(labels)
        else:
            has_regular = True
    if has_regular or not specials:
        return ("Uptown", "Downtown")
    unique = set(specials)
    if len(unique) == 1:
        return specials[0]
    return ("Uptown", "Downtown")


def feed_urls_for_routes(route_ids):
    """Feed URLs needed for these route ids, in a stable order."""
    keys = []
    seen = set()
    for route_id in sorted(route_ids, key=route_sort_key):
        key = ROUTE_FEED.get(route_id)
        if key and key not in seen:
            seen.add(key)
            keys.append(key)
    return [FEED_URLS[key] for key in keys]


def _load_routes():
    routes = {}
    with open(GTFS_DIR / "routes.txt", newline="") as handle:
        for row in csv.DictReader(handle):
            routes[row["route_id"]] = row
    return routes


def _route_payload(route_id, routes):
    row = routes.get(route_id, {})
    short = (row.get("route_short_name") or route_id).strip() or route_id
    color = (row.get("route_color") or "").strip() or "808183"
    text = (row.get("route_text_color") or "").strip()
    if not text:
        text = "000000" if color.upper() in {"FCCC0A", "FFD100"} else "FFFFFF"
    return {
        "id": route_id,
        "short": short,
        "name": (row.get("route_long_name") or short).strip(),
        "color": f"#{color}",
        "text_color": f"#{text}",
        "express": route_id.endswith("X"),
    }


def _build_stations():
    routes = _load_routes()
    trip_route = {}
    with open(GTFS_DIR / "trips.txt", newline="") as handle:
        for row in csv.DictReader(handle):
            trip_route[row["trip_id"]] = row["route_id"]

    parents = {}
    with open(GTFS_DIR / "stops.txt", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("location_type") == "1":
                parents[row["stop_id"]] = row["stop_name"]

    routes_at = {parent_id: set() for parent_id in parents}
    with open(GTFS_DIR / "stop_times.txt", newline="") as handle:
        for row in csv.DictReader(handle):
            stop_id = row["stop_id"]
            if len(stop_id) < 2 or stop_id[-1] not in "NS":
                continue
            parent_id = stop_id[:-1]
            bucket = routes_at.get(parent_id)
            if bucket is None:
                continue
            route_id = trip_route.get(row["trip_id"])
            if route_id:
                bucket.add(route_id)

    stations = []
    for parent_id, name in parents.items():
        route_ids = sorted(routes_at.get(parent_id, ()), key=route_sort_key)
        if not route_ids:
            continue
        north, south = direction_labels(route_ids)
        stations.append({
            "id": parent_id,
            "name": name,
            "routes": [_route_payload(route_id, routes) for route_id in route_ids],
            "directions": [
                {"id": "N", "label": north},
                {"id": "S", "label": south},
            ],
        })
    stations.sort(key=lambda station: (station["name"].lower(), station["id"]))
    return stations


def get_stations():
    """Every subway station that has scheduled service, with its lines."""
    global _cache
    if _cache is None:
        with _cache_lock:
            if _cache is None:
                _cache = _build_stations()
    return _cache


def stations_by_id():
    return {station["id"]: station for station in get_stations()}


def route_payloads(route_ids, stations=None):
    """Color and label info for route ids, in display order."""
    if stations is None:
        stations = get_stations()
    known = {}
    for station in stations:
        for route in station["routes"]:
            known.setdefault(route["id"], route)
    payloads = []
    seen = set()
    for route_id in sorted(route_ids, key=route_sort_key):
        if route_id in seen:
            continue
        seen.add(route_id)
        payloads.append(known.get(route_id) or {
            "id": route_id,
            "short": route_id,
            "name": route_id,
            "color": "#808183",
            "text_color": "#FFFFFF",
            "express": route_id.endswith("X"),
        })
    return payloads
