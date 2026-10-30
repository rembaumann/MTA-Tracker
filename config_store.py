"""Local board settings and environment secrets.

config.json is the live file and is gitignored. config.example.json is the
default that ships with the repo. A missing config.json uses the example, so
the board runs without a setup step.
"""

import json
import os
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
EXAMPLE_PATH = BASE_DIR / "config.example.json"
ENV_PATH = BASE_DIR / ".env"

DEFAULT_CONFIG = {
    "trains_ahead": 5,
    "trains_per_page": 5,
    "cycle_seconds": 10,
    "zip_code": "10010",
    "stations": [
        {"id": "635", "directions": ["N", "S"], "routes": ["4", "5", "6", "6X"]},
        {"id": "R20", "directions": ["N", "S"], "routes": ["N", "Q", "R", "W"]},
        {"id": "L03", "directions": ["N", "S"], "routes": ["L"]},
        {"id": "634", "directions": ["N", "S"], "routes": ["4", "6", "6X"]},
        {"id": "R19", "directions": ["N", "S"], "routes": ["N", "Q", "R", "W"]},
    ],
}


def load_dotenv(path=None):
    """Load KEY=value lines into the environment without overriding real vars."""
    env_path = Path(path) if path else ENV_PATH
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key and value:
            os.environ.setdefault(key, value)


def _read_json(path):
    with open(path, "r") as handle:
        return json.load(handle)


def _as_int(value, default, low, high):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default, f"expected a number, got {value!r}"
    if number < low or number > high:
        return default, f"{number} is outside {low}-{high}"
    return number, None


def normalize_config(payload, stations_by_id=None, strict=False):
    """Return (config, errors).

    When stations_by_id is provided (a save), station ids and routes are
    checked against the GTFS catalog. When it is None (a load), unknown
    stations are kept so a GTFS refresh cannot take the board down.

    strict=True reports out-of-range numbers and ZIP codes. A load clamps
    those instead, so a typo in one field does not discard the stations.
    """
    errors = []
    if not isinstance(payload, dict):
        return None, ["Config must be a JSON object."]

    trains_ahead, problem = _as_int(payload.get("trains_ahead", 5), 5, 1, 20)
    if problem and strict and "trains_ahead" in payload:
        errors.append(f"trains_ahead: {problem}")
    per_page, problem = _as_int(payload.get("trains_per_page", 5), 5, 3, 8)
    if problem and strict and "trains_per_page" in payload:
        errors.append(f"trains_per_page: {problem}")
    cycle, problem = _as_int(payload.get("cycle_seconds", 10), 10, 5, 120)
    if problem and strict and "cycle_seconds" in payload:
        errors.append(f"cycle_seconds: {problem}")

    zip_code = str(payload.get("zip_code", "10010")).strip()
    if not (len(zip_code) == 5 and zip_code.isdigit()):
        if strict:
            errors.append("zip_code must be a 5-digit US ZIP code.")
        zip_code = "10010"

    raw_stations = payload.get("stations", [])
    if not isinstance(raw_stations, list) or not raw_stations:
        errors.append("Choose at least one station.")
        raw_stations = []

    stations = []
    seen = set()
    for index, raw in enumerate(raw_stations):
        label = f"stations[{index}]"
        if not isinstance(raw, dict):
            errors.append(f"{label} must be an object.")
            continue
        station_id = str(raw.get("id", "")).strip()
        if not station_id:
            errors.append(f"{label} is missing an id.")
            continue
        if station_id in seen:
            errors.append(f"{station_id} is listed more than once.")
            continue
        seen.add(station_id)

        catalog_station = None
        if stations_by_id is not None:
            catalog_station = stations_by_id.get(station_id)
            if catalog_station is None:
                errors.append(f"Unknown station {station_id}.")
                continue

        directions = raw.get("directions", ["N", "S"])
        if not isinstance(directions, list):
            errors.append(f"{label} directions must be a list.")
            directions = []
        directions = [item for item in directions if item in ("N", "S")]
        # Preserve N then S regardless of the order the client sent.
        directions = [item for item in ("N", "S") if item in directions]
        if not directions:
            errors.append(f"{station_id} needs at least one direction.")
            continue

        routes = raw.get("routes", [])
        if not isinstance(routes, list):
            errors.append(f"{label} routes must be a list.")
            routes = []
        routes = [str(route_id) for route_id in routes if str(route_id).strip()]
        if catalog_station is not None:
            allowed = [route["id"] for route in catalog_station["routes"]]
            unknown = [route_id for route_id in routes if route_id not in allowed]
            if unknown:
                errors.append(
                    f"{station_id} is not served by {', '.join(unknown)}."
                )
                continue
            if not routes:
                routes = allowed
            routes = [route_id for route_id in allowed if route_id in routes]
        if not routes:
            errors.append(f"{station_id} needs at least one line.")
            continue

        stations.append({
            "id": station_id,
            "directions": directions,
            "routes": routes,
        })

    if raw_stations and not stations and not errors:
        errors.append("Choose at least one station.")

    config = {
        "trains_ahead": trains_ahead,
        "trains_per_page": per_page,
        "cycle_seconds": cycle,
        "zip_code": zip_code,
        "stations": stations,
    }
    return config, errors


def load_config():
    """Live config, falling back to the example and then the built-in default."""
    candidates = []
    if CONFIG_PATH.is_file():
        candidates.append(CONFIG_PATH)
    if EXAMPLE_PATH.is_file():
        candidates.append(EXAMPLE_PATH)

    for path in candidates:
        try:
            config, errors = normalize_config(_read_json(path), stations_by_id=None, strict=False)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Could not read {path.name}: {exc}")
            continue
        if errors or not config or not config["stations"]:
            print(f"Ignoring {path.name}: {errors or 'no stations'}")
            continue
        return config

    config, _ = normalize_config(DEFAULT_CONFIG, stations_by_id=None, strict=False)
    return config


def save_config(config):
    """Atomically write config.json."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(config, indent=2) + "\n")
    temporary.replace(CONFIG_PATH)


def get_version():
    """Short git commit for the running process. Stable until restart."""
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=BASE_DIR,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return output.decode().strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


VERSION = get_version()
