"""Catalog, config, and arrival filtering. No network."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.transit import gtfs_realtime_pb2

import config_store
from app import app, board_stations, collect_arrivals, load_trips_headsigns, platforms_for_config
from config_store import normalize_config
from gtfs_catalog import direction_labels, feed_urls_for_routes, get_stations, stations_by_id


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stations = stations_by_id()

    def test_union_square_lines(self):
        lex = self.stations["635"]
        self.assertEqual(lex["name"], "14 St-Union Sq")
        self.assertEqual([route["id"] for route in lex["routes"]], ["4", "5", "6", "6X"])
        broadway = self.stations["R20"]
        self.assertEqual([route["id"] for route in broadway["routes"]], ["N", "Q", "R", "W"])
        self.assertEqual([route["id"] for route in self.stations["L03"]["routes"]], ["L"])

    def test_twenty_third_street_is_not_the_express_5(self):
        routes = [route["id"] for route in self.stations["634"]["routes"]]
        self.assertIn("6", routes)
        self.assertNotIn("5", routes)

    def test_every_parent_station_is_listed(self):
        self.assertGreater(len(get_stations()), 400)
        names = {station["name"] for station in get_stations()}
        self.assertIn("Times Sq-42 St", names)

    def test_direction_labels(self):
        self.assertEqual(direction_labels(["L"]), ("Manhattan", "Brooklyn"))
        self.assertEqual(direction_labels(["4", "5", "6"]), ("Uptown", "Downtown"))
        self.assertEqual(
            [item["label"] for item in self.stations["L03"]["directions"]],
            ["Manhattan", "Brooklyn"],
        )

    def test_feed_urls_keep_the_encoded_slash(self):
        urls = feed_urls_for_routes(["L", "4", "A"])
        self.assertEqual(len(urls), 3)
        joined = " ".join(urls)
        self.assertIn("nyct%2Fgtfs-l", joined)
        self.assertIn("nyct%2Fgtfs-ace", joined)
        self.assertNotIn("nyct/gtfs", joined)


class ConfigTests(unittest.TestCase):
    def test_example_matches_the_old_kiosk(self):
        example = json.loads(Path("config.example.json").read_text())
        config, errors = normalize_config(example, stations_by_id(), strict=True)
        self.assertEqual(errors, [])
        self.assertEqual(
            [station["id"] for station in config["stations"]],
            ["635", "R20", "L03", "634", "R19"],
        )

    def test_save_rejects_an_unknown_station_and_a_line_that_does_not_stop_there(self):
        payload = {
            "zip_code": "10010",
            "lookahead_minutes": 20,
            "trains_per_page": 5,
            "cycle_seconds": 10,
            "stations": [
                {"id": "NOPE", "directions": ["N"], "routes": ["6"]},
                {"id": "634", "directions": ["N"], "routes": ["5"]},
            ],
        }
        config, errors = normalize_config(payload, stations_by_id(), strict=True)
        self.assertTrue(any("Unknown station" in error for error in errors))
        self.assertTrue(any("not served" in error for error in errors))
        self.assertEqual(config["stations"], [])

    def test_round_trip_through_a_temp_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            example = Path("config.example.json")
            original_config = config_store.CONFIG_PATH
            original_example = config_store.EXAMPLE_PATH
            config_store.CONFIG_PATH = path
            config_store.EXAMPLE_PATH = example
            try:
                loaded = config_store.load_config()
                self.assertEqual(loaded["stations"][0]["id"], "635")
                loaded["zip_code"] = "11215"
                loaded["stations"] = loaded["stations"][:1]
                config_store.save_config(loaded)
                again = config_store.load_config()
                self.assertEqual(again["zip_code"], "11215")
                self.assertEqual(len(again["stations"]), 1)
            finally:
                config_store.CONFIG_PATH = original_config
                config_store.EXAMPLE_PATH = original_example


class ArrivalTests(unittest.TestCase):
    def test_platforms_follow_the_selection(self):
        config, errors = normalize_config({
            "stations": [{
                "id": "635",
                "directions": ["S"],
                "routes": ["6"],
            }]
        }, stations_by_id(), strict=True)
        self.assertEqual(errors, [])
        platforms = platforms_for_config(config)
        self.assertEqual(set(platforms), {"635S"})
        self.assertEqual(platforms["635S"], {"6"})

    def test_collect_arrivals_filters_line_direction_and_window(self):
        now = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
        feed = gtfs_realtime_pb2.FeedMessage()

        def add(route, stop_id, minutes, trip_id):
            entity = feed.entity.add()
            entity.id = trip_id
            trip = entity.trip_update.trip
            trip.trip_id = trip_id
            trip.route_id = route
            trip.direction_id = 0 if stop_id.endswith("N") else 1
            update = entity.trip_update.stop_time_update.add()
            update.stop_id = stop_id
            update.arrival.time = int((now + timedelta(minutes=minutes)).timestamp())

        add("6", "635N", 3, "up-6")
        add("4", "635N", 4, "up-4")
        add("6", "635S", 5, "down-6")
        add("6", "635N", 40, "later")
        add("L", "L03N", 2, "the-l")

        config, errors = normalize_config({
            "lookahead_minutes": 20,
            "stations": [{
                "id": "635",
                "directions": ["N"],
                "routes": ["6"],
            }],
        }, stations_by_id(), strict=True)
        self.assertEqual(errors, [])
        groups = collect_arrivals(
            [feed],
            config,
            {"635": "14 St-Union Sq"},
            now=now,
            headsign_by_trip={"up-6": "Pelham Bay Park"},
            headsign_by_route_direction={},
        )
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["station_id"], "635N")
        self.assertEqual(groups[0]["direction"], "Uptown")
        self.assertEqual(len(groups[0]["trains"]), 1)
        self.assertEqual(groups[0]["trains"][0]["route"], "6")
        self.assertEqual(groups[0]["trains"][0]["destination"], "Pelham Bay Park")

    def test_board_stations_keep_only_enabled_lines(self):
        stations = board_stations({
            "stations": [
                {"id": "634", "directions": ["N"], "routes": ["4", "6"]},
                {"id": "L03", "directions": ["N", "S"], "routes": ["L"]},
            ]
        })
        self.assertEqual([station["id"] for station in stations], ["634", "L03"])
        self.assertEqual(stations[0]["name"], "23 St")
        self.assertEqual([route["id"] for route in stations[0]["routes"]], ["4", "6"])
        self.assertEqual(stations[1]["name"], "14 St-Union Sq")
        self.assertEqual([route["id"] for route in stations[1]["routes"]], ["L"])

    def test_platform_fallback_does_not_trust_the_l_direction_bit(self):
        _by_trip, _by_route, by_platform = load_trips_headsigns()
        self.assertIn("Canarsie", by_platform["L_S"])
        self.assertIn("8 Av", by_platform["L_N"])


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "config.json"
        self.original = config_store.CONFIG_PATH
        config_store.CONFIG_PATH = self.path

    def tearDown(self):
        config_store.CONFIG_PATH = self.original
        self.tmp.cleanup()

    def test_version_and_pages(self):
        version = self.client.get("/version")
        self.assertEqual(version.status_code, 200)
        self.assertIn("version", version.get_json())
        board = self.client.get("/")
        self.assertEqual(board.status_code, 200)
        self.assertIn(b"edge-button", board.data)
        self.assertIn(b"station-menu", board.data)
        self.assertNotIn(b"line-picker", board.data)
        self.assertNotIn(b"pause-cycle", board.data)
        settings = self.client.get("/settings")
        self.assertEqual(settings.status_code, 200)
        self.assertIn(b"Add a station", settings.data)

    def test_settings_round_trip(self):
        payload = {
            "lookahead_minutes": 15,
            "trains_per_page": 4,
            "cycle_seconds": 12,
            "zip_code": "10003",
            "stations": [{
                "id": "L03",
                "directions": ["N", "S"],
                "routes": ["L"],
            }],
        }
        saved = self.client.post("/api/config", json=payload)
        self.assertEqual(saved.status_code, 200, saved.get_json())
        loaded = self.client.get("/api/config")
        self.assertEqual(loaded.get_json()["stations"][0]["id"], "L03")
        self.assertEqual(loaded.get_json()["zip_code"], "10003")
        stations = self.client.get("/api/stations")
        self.assertGreater(len(stations.get_json()["stations"]), 400)


if __name__ == "__main__":
    unittest.main()
