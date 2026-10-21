# MTA Tracker

A real-time New York City subway board for a wall display. It runs as a Flask app, reads the public MTA GTFS-RT feeds, and is meant to boot full screen on a Raspberry Pi.

Out of the box it shows 14 St-Union Sq and 23 St, the same stations the original kiosk used. Any other station, direction, and line can be chosen from the settings screen. Choices are stored in `config.json`, which is gitignored.

## Features

- Live arrivals from the MTA GTFS-RT feeds
- Every subway station in the bundled GTFS static data, with search
- Per-station choice of directions and lines
- Touch-friendly line filter on the board, alongside auto-cycling
- Large previous, next, and pause controls
- Optional temperature from OpenWeatherMap
- The running git commit in the corner. The page reloads itself when an update changes it

## Run it locally

Python 3.9 or newer.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5001. Settings are at http://localhost:5001/settings.

No MTA API key is required. The subway GTFS-RT feeds are public. A keyless GET to `https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs` returns the protobuf feed (checked 2026-10-21). The slash in that path has to stay percent-encoded (`%2F`). A decoded slash is rejected with 403.

The temperature is optional. Copy `.env.example` to `.env` and set `OPENWEATHER_API_KEY`. `.env` is gitignored. If `MTA_API_KEY` is set there, it is sent as the `x-api-key` header, but the feeds work without it.

## Choose stations

Use the gear on the board, or open `/settings`.

1. Search by station name, or by a line such as `Q` or `6`.
2. Add a station. It starts with both directions and every line that stops there.
3. Turn directions and line bullets on or off. Reorder with the arrows.
4. Save. The board picks up the change on the next refresh.

The same choices live in `config.json`. `config.example.json` is the default used when `config.json` does not exist yet, so a fresh clone still shows trains. `install-pi.sh` copies the example to `config.json` once and will not overwrite it later.

```json
{
  "lookahead_minutes": 20,
  "trains_per_page": 5,
  "cycle_seconds": 10,
  "zip_code": "10010",
  "stations": [
    {"id": "635", "directions": ["N", "S"], "routes": ["4", "5", "6", "6X"]}
  ]
}
```

`id` is the parent stop id from `gtfs_subway/stops.txt` (`635`, not `635N`). Directions are `N` and `S`. Routes are GTFS route ids, so the express `6X` is separate from the `6`.

The default stations are:

| Stop id | Station | Lines |
| --- | --- | --- |
| 635 | 14 St-Union Sq | 4, 5, 6, 6X |
| R20 | 14 St-Union Sq | N, Q, R, W |
| L03 | 14 St-Union Sq | L |
| 634 | 23 St | 4, 6, 6X |
| R19 | 23 St | N, Q, R, W |

Stations that share a name are separate stops. The line bullets are how you tell the Lexington 23 St from the Broadway 23 St.

## The board

The bullets under the header filter the rotation. **All** cycles every configured line. Tap a bullet to keep that line, and tap more to add them. Previous and Next move by hand and hold the page for 20 seconds before cycling resumes. Pause keeps the current page until you resume.

Arrivals are grouped by platform. The L says Manhattan or Brooklyn. The 7 says Queens or Manhattan. Most other lines say Uptown or Downtown.

## Raspberry Pi

The Pi steps are in [RASPBERRY_PI_SETUP.md](RASPBERRY_PI_SETUP.md). On the Pi, from the clone:

```bash
cd /home/rem/mta-tracker
./install-pi.sh
sudo reboot
```

`install-pi.sh` detects the user and the repo path. It does not assume `pi` or `/home/pi`. That assumption is why an older unit failed with `status=217/USER`.

Update later with:

```bash
cd /home/rem/mta-tracker
./update.sh
```

`update.sh` fast-forwards git, reinstalls requirements when that file changed, and restarts the service. The browser polls `/version` (the short git commit) and reloads when it changes. A systemd timer runs the same script about every six hours. Disable it with `sudo systemctl disable --now mta-tracker-update.timer`.

## API

- `GET /api/data` — groups of arrivals, the configured lines, and the running version
- `GET /api/stations` — every station, with lines and direction labels
- `GET /api/config` and `POST /api/config` — read or replace the settings
- `GET /version` — `{"version": "<short sha>"}`
- `GET /api/temperature` — temperature, or null when no weather key is set

## Project layout

```
app.py                     Flask app and feed parser
config_store.py            config.json, .env, running version
gtfs_catalog.py            stations and lines from gtfs_subway/
config.example.json        default stations
.env.example               optional API keys
templates/                 board and settings
static/                    CSS and JavaScript
install-pi.sh              venv, systemd, labwc kiosk
update.sh                  pull, restart, let the browser reload
kiosk.sh                   Chromium on Wayland, X11 fallback
mta-tracker.service.in    service template, filled in by the installer
tests/test_board.py
gtfs_subway/               static GTFS
```

## Development

```bash
python -m unittest tests.test_board
```

The tests use the bundled GTFS and a fake realtime message. They do not call the MTA.

Feeds used, one per group of lines:

| Feed | Lines |
| --- | --- |
| `nyct%2Fgtfs` | 1–7, 6X, 7X, 42 St Shuttle |
| `nyct%2Fgtfs-ace` | A, C, E, Rockaway Shuttle |
| `nyct%2Fgtfs-bdfm` | B, D, F, M, Franklin Shuttle |
| `nyct%2Fgtfs-g` | G |
| `nyct%2Fgtfs-jz` | J, Z |
| `nyct%2Fgtfs-l` | L |
| `nyct%2Fgtfs-nqrw` | N, Q, R, W |
| `nyct%2Fgtfs-si` | Staten Island Railway |

Only the feeds for the lines you selected are downloaded.

## Troubleshooting

- **No trains:** the station may be quiet inside the lookahead window. Raise "Minutes ahead" in settings, or confirm the Pi can reach `api-endpoint.mta.info`.
- **Temperature missing:** set `OPENWEATHER_API_KEY` in `.env` and restart. See [WEATHER_SETUP.md](WEATHER_SETUP.md).
- **Port in use:** the app listens on `5001`.
- **Pi service failed with 217/USER:** the unit still says `User=pi`. Run `./install-pi.sh` again so it writes the real username.

## License

MIT.
