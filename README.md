# MTA Tracker

A real-time subway arrival tracker for New York City MTA stations, built with Flask and styled to mimic the classic subway board aesthetic.

## Features

- **Real-time Data**: Fetches live train arrival times from MTA's GTFS Realtime API
- **Subway Board Style**: Clean, dark interface inspired by actual MTA subway displays
- **Multiple Stations**: Monitors 14 St-Union Sq and 23 St stations
- **All Subway Lines**: Supports 4, 5, 6, L, N, Q, R, and W trains
- **Platform-Specific**: Separates trains by actual platform/station ID for accuracy
- **L Train Special Handling**: Uses geographic direction names (Manhattan Bound/Brooklyn Bound)
- **Pagination**: Shows 5 trains per page with manual navigation controls
- **Auto-Cycling**: Automatically cycles through all station/direction combinations
- **Destination Display**: Shows final destination for each train

## Screenshots

The app displays train arrivals in a subway board style with:
- Station name and direction badges
- Train route icons with MTA colors
- Arrival times (NOW, 1 MIN, X MIN format)
- Final destinations
- Manual navigation arrows
- Progress indicator

## Installation

### Prerequisites

- Python 3.7+
- MTA API key (free from [MTA Developer Resources](https://api.mta.info/))

### Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd MTA-Tracker
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Get MTA API Key**
   - Visit [MTA Developer Resources](https://api.mta.info/)
   - Sign up for a free API key
   - Replace `YOUR_API_KEY_HERE` in `app.py` with your actual key

4. **Download GTFS Static Data**
   - The app includes GTFS static data files in the `gtfs_subway/` directory
   - These files are used for station names and trip destinations

5. **Run the application**
   ```bash
   python3 app.py
   ```

6. **Access the app**
   - Open your browser to `http://localhost:5001`

## Configuration

### Monitored Stations

The app currently monitors these station IDs:
- **14 St-Union Sq**: 635N/635S (4/5/6 trains), R20N/R20S (N/Q/R/W trains), L03N/L03S (L trains)
- **23 St**: 634N/634S (4/5/6 trains), R19N/R19S (N/Q/R/W trains)

### API Endpoints

The app fetches data from these MTA feeds:
- `gtfs-456` - 4, 5, 6 trains
- `gtfs-nqrw` - N, Q, R, W trains  
- `gtfs-l` - L trains

## Project Structure

```
MTA Tracker/
├── app.py                 # Main Flask application
├── main.py               # Original script (legacy)
├── requirements.txt      # Python dependencies
├── templates/
│   └── index.html       # Web interface template
├── static/
│   └── css/
│       ├── style.css    # Main stylesheet
│       └── subway-icons.css  # Subway line icons
└── gtfs_subway/         # GTFS static data files
    ├── stops.txt        # Station information
    ├── trips.txt        # Trip headsigns
    └── ...              # Other GTFS files
```

## Key Features Explained

### Station ID Grouping
Trains are grouped by their actual station ID rather than station name, ensuring that different subway lines at the same physical station are displayed separately. This provides more accurate platform-specific information.

### L Train Direction Mapping
L trains use geographic direction names:
- Northbound → "Manhattan Bound" 
- Southbound → "Brooklyn Bound"

### Destination Lookup
The app uses a two-tier lookup system for train destinations:
1. **Trip ID lookup**: Matches real-time trip IDs to static trip headsigns
2. **Route + Direction fallback**: Uses route ID and direction ID when trip ID doesn't match

### Pagination System
- Shows 5 trains per page
- Manual navigation with left/right arrows
- Auto-cycling through all pages every 10 seconds
- Manual navigation pauses auto-cycling for 3 seconds

## API Response Format

The `/api/data` endpoint returns:
```json
{
  "data": [
    {
      "station": "14 St-Union Sq",
      "station_id": "635N", 
      "direction": "Northbound",
      "line_type": "Other Lines",
      "page": 1,
      "total_pages": 2,
      "trains": [
        {
          "route": "6",
          "minutes": 2.5,
          "destination": "Pelham Bay Park"
        }
      ]
    }
  ],
  "last_updated": "2025-01-16T20:30:45Z"
}
```

## Development

### Adding New Stations

To monitor additional stations:

1. Find the station IDs in `gtfs_subway/stops.txt`
2. Add the station IDs to the filter in `app.py`:
   ```python
   if stop_id in ["634N", "634S", "635N", "635S", "L03N", "L03S", "R19N", "R19S", "R20N", "R20S", "NEW_STATION_ID"]:
   ```

### Customizing Display

- **Colors**: Modify CSS classes in `static/css/style.css`
- **Layout**: Update HTML structure in `templates/index.html`
- **Timing**: Adjust `CYCLE_DURATION` and pagination settings in the JavaScript

## Troubleshooting

### Common Issues

1. **No trains showing**: Check your MTA API key and internet connection
2. **Missing destinations**: Some trains may not have destination data in the static feed
3. **Port already in use**: Change the port in `app.py` or kill existing processes

### Debug Mode

The app includes debug logging for troubleshooting:
- Trip ID lookups
- Route + direction fallbacks
- Data loading statistics

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Acknowledgments

- MTA for providing the GTFS Realtime API
- NYC Subway for the inspiration and data
- Flask and Python community for excellent tools

## Future Enhancements

- [ ] Add more stations
- [ ] Service alerts integration
- [ ] Mobile-responsive design improvements
- [ ] Historical data tracking
- [ ] Push notifications
- [ ] Multi-language support
