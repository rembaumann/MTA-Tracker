"""Signs for every catalog station that is not already in design/irt-original.

BMT Dual Contracts stations use the Broadway frame. IRT Dual Contracts
stations use the Lexington frame. Their field color changes from stop to
stop along the line. IND stations use the published band and border colors
when the station name matches that chart, and the line's usual color when
it does not. New stations, the Staten Island Railway, and the Dyre Avenue
line get a white enamel sign.

Run: PYTHONPATH=design/.pydeps python3 design/generate_remaining.py
"""

import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_tablets as tiles
from gtfs_catalog import get_stations

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "design", "tablets")
ORIGINAL = os.path.join(ROOT, "design", "irt-original")
CHART = os.path.join(
    os.path.dirname(ROOT),
    "..",
    ".cursor",
    "projects",
    "Users-pebbles-Documents-Projects-MTA-Tracker",
    "agent-tools",
    "2ae3ef21-6f6b-459f-b55f-d5710b2469c9.txt",
)

# A few names read better as the landmark than as the expanded street.
FORCE = {
    "81 St-Museum of Natural History": "NATURAL HISTORY",
    "42 St-Port Authority Bus Terminal": "PORT AUTHORITY",
    "Sutphin Blvd-Archer Av-JFK Airport": "JFK AIRPORT",
    "Jamaica Center-Parsons/Archer": "JAMAICA CENTER",
    "Brooklyn Bridge-City Hall": "BROOKLYN BRIDGE",
    "Eastern Pkwy-Brooklyn Museum": "BROOKLYN MUSEUM",
    "Franklin Av-Medgar Evers College": "FRANKLIN AVENUE",
    "President St-Medgar Evers College": "PRESIDENT STREET",
    "Van Cortlandt Park-242 St": "VAN CORTLANDT",
    "Wakefield-241 St": "WAKEFIELD",
    "Eastchester-Dyre Av": "DYRE AVENUE",
    "161 St-Yankee Stadium": "YANKEE STADIUM",
    "149 St-Grand Concourse": "GRAND CONCOURSE",
    "138 St-Grand Concourse": "GRAND CONCOURSE",
    "34 St-Hudson Yards": "HUDSON YARDS",
    "34 St-Herald Sq": "HERALD SQUARE",
    "34 St-Penn Station": "PENN STATION",
    "42 St-Bryant Pk": "BRYANT PARK",
    "47-50 Sts-Rockefeller Ctr": "ROCKEFELLER CENTER",
    "59 St-Columbus Circle": "COLUMBUS CIRCLE",
    "66 St-Lincoln Center": "LINCOLN CENTER",
    "Times Sq-42 St": "TIMES SQUARE",
    "Grand Central-42 St": "GRAND CENTRAL",
    "14 St-Union Sq": "UNION SQUARE",
    "W 4 St-Wash Sq": "WEST 4TH STREET",
    "W 8 St-NY Aquarium": "NEW YORK AQUARIUM",
    "Smith-9 Sts": "SMITH STREET",
    "Cathedral Pkwy (110 St)": "CATHEDRAL PARKWAY",
    "110 St-Malcolm X Plaza": "MALCOLM X PLAZA",
    "116 St-Columbia University": "COLUMBIA UNIVERSITY",
    "137 St-City College": "CITY COLLEGE",
    "168 St-Washington Hts": "WASHINGTON HEIGHTS",
    "163 St-Amsterdam Av": "AMSTERDAM AVENUE",
    "103 St-Corona Plaza": "CORONA PLAZA",
    "82 St-Jackson Hts": "JACKSON HEIGHTS",
    "90 St-Elmhurst Av": "ELMHURST AVENUE",
    "74 St-Broadway": "74TH STREET",
    "69 St": "69TH STREET",
    "61 St-Woodside": "WOODSIDE",
    "46 St-Bliss St": "BLISS STREET",
    "40 St-Lowery St": "LOWERY STREET",
    "33 St-Rawson St": "RAWSON STREET",
    "21 St-Queensbridge": "QUEENSBRIDGE",
    "Court Sq-23 St": "COURT SQUARE",
    "Jackson Hts-Roosevelt Av": "ROOSEVELT AVENUE",
    "Forest Hills-71 Av": "FOREST HILLS",
    "Kew Gardens-Union Tpke": "UNION TURNPIKE",
    "Jamaica-179 St": "179TH STREET",
    "Jamaica-Van Wyck": "VAN WYCK",
    "Flushing-Main St": "FLUSHING",
    "Mets-Willets Point": "WILLETS POINT",
    "Astoria-Ditmars Blvd": "DITMARS BOULEVARD",
    "39 Av-Dutch Kills": "DUTCH KILLS",
    "Whitehall St-South Ferry": "WHITEHALL STREET",
    "Coney Island-Stillwell Av": "CONEY ISLAND",
    "Atlantic Av-Barclays Ctr": "ATLANTIC AVENUE",
    "Jay St-MetroTech": "JAY STREET",
    "Flatbush Av-Brooklyn College": "FLATBUSH AVENUE",
    "Canarsie-Rockaway Pkwy": "CANARSIE",
    "Middle Village-Metropolitan Av": "METROPOLITAN AVENUE",
    "Norwood-205 St": "NORWOOD",
    "Bedford Park Blvd-Lehman College": "BEDFORD PARK",
    "Inwood-207 St": "INWOOD",
    "Ozone Park-Lefferts Blvd": "LEFFERTS BOULEVARD",
    "Howard Beach-JFK Airport": "HOWARD BEACH",
    "Rockaway Park-Beach 116 St": "ROCKAWAY PARK",
    "Aqueduct-N Conduit Av": "CONDUIT AVENUE",
    "Aqueduct Racetrack": "AQUEDUCT",
    "Hoyt-Schermerhorn Sts": "SCHERMERHORN",
    "Broadway-Lafayette St": "BROADWAY LAFAYETTE",
    "Delancey St-Essex St": "DELANCEY STREET",
    "Christopher St-Stonewall": "CHRISTOPHER STREET",
    "8 St-NYU": "8TH STREET",
    "World Trade Center": "WORLD TRADE CENTER",
    "WTC Cortlandt": "CORTLANDT STREET",
    "Harlem-148 St": "148TH STREET",
    "Crown Hts-Utica Av": "UTICA AVENUE",
    "Newkirk Av-Little Haiti": "NEWKIRK AVENUE",
    "Westchester Sq-E Tremont Av": "WESTCHESTER SQUARE",
    "West Farms Sq-E Tremont Av": "WEST FARMS",
    "E 143 St-St Mary's St": "EAST 143RD STREET",
    "Morrison Av-Soundview": "SOUNDVIEW",
    "St Lawrence Av": "SAINT LAWRENCE",
    "St George": "SAINT GEORGE",
    "3 Av-149 St": "3RD AVENUE",
    "3 Av-138 St": "3RD AVENUE",
    "Lexington Av/59 St": "LEXINGTON AVENUE",
    "Lexington Av/63 St": "LEXINGTON AVENUE",
    "Lexington Av/53 St": "LEXINGTON AVENUE",
    "5 Av/53 St": "5TH AVENUE",
    "5 Av/59 St": "5TH AVENUE",
    "57 St-7 Av": "57TH STREET",
    "Bay Ridge-95 St": "BAY RIDGE",
    "Pelham Bay Park": "PELHAM BAY",
    "Marble Hill-225 St": "MARBLE HILL",
}

ABBREV = (
    ("Sts", "Streets"),
    ("Ave", "Avenue"),
    ("Avs", "Avenues"),
    ("Av", "Avenue"),
    ("Blvd", "Boulevard"),
    ("Pkwy", "Parkway"),
    ("Tpke", "Turnpike"),
    ("Hwy", "Highway"),
    ("Sq", "Square"),
    ("Rd", "Road"),
    ("Pl", "Place"),
    ("Hts", "Heights"),
    ("Ctr", "Center"),
    ("Jct", "Junction"),
    ("Pk", "Park"),
    ("Dr", "Drive"),
    ("Ln", "Lane"),
    ("Ct", "Court"),
    ("Ter", "Terrace"),
    ("St", "Street"),
)


def ordinal(number):
    if 10 <= number % 100 <= 20:
        suffix = "TH"
    else:
        suffix = {1: "ST", 2: "ND", 3: "RD"}.get(number % 10, "TH")
    return f"{number}{suffix}"


def expand_part(part):
    part = re.sub(
        r"^(E|W|N|S)\b",
        lambda match: {"E": "East", "W": "West", "N": "North", "S": "South"}[match.group(1)],
        part,
    )
    part = re.sub(r"\b(\d+)\b", lambda match: ordinal(int(match.group(1))), part)
    for pattern, replacement in ABBREV:
        part = re.sub(rf"\b{pattern}\b", replacement, part)
    return part.upper()


def tablet_text(name):
    if name in FORCE:
        return FORCE[name]
    cleaned = re.sub(r"\s*\([^)]*\)", "", name).strip()
    cleaned = cleaned.replace("–", "-").replace("—", "-").replace("/", "-")
    parts = [expand_part(part.strip()) for part in re.split(r"(?<=[A-Za-z])-(?=[A-Za-z0-9])", cleaned)]
    parts = [part for part in parts if part]

    def plain(part):
        return re.match(
            r"^(?:[NSEW] )?\d+(?:ST|ND|RD|TH)(?:-\d+(?:ST|ND|RD|TH))? (?:STREET|STREETS|AVENUE|AVENUES|ROAD|PLACE|PARKWAY|BOULEVARD)$",
            part,
        )

    if len(parts) == 1:
        text = parts[0]
    elif plain(parts[0]) and not plain(parts[-1]):
        text = parts[-1]
    elif not plain(parts[0]) and plain(parts[-1]):
        text = parts[0]
    elif all(plain(part) for part in parts) or len(" ".join(parts)) <= 18:
        text = " ".join(parts)
    else:
        trimmed = []
        for part in parts:
            words = part.split()
            if len(words) > 1 and words[-1] in {"AVENUE", "AVENUES", "STREET", "STREETS", "BOULEVARD", "PARKWAY"}:
                trimmed.append(" ".join(words[:-1]))
            else:
                trimmed.append(part)
        text = " ".join(trimmed)
    words = text.split()
    while len(" ".join(words)) > 24 and len(words) > 1:
        words.pop()
    return " ".join(words)


def luminance(hex_color):
    red, green, blue = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.299 * red + 0.587 * green + 0.114 * blue


def shades(hex_color):
    red, green, blue = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    colors = []
    for delta in (-32, -18, -8, 0, 10, 18, -24, 14):
        colors.append("#{:02x}{:02x}{:02x}".format(
            max(0, min(255, red + delta)),
            max(0, min(255, green + delta // 2)),
            max(0, min(255, blue + delta // 3)),
        ))
    return colors


COLOR_HEX = {
    "carmine red": "#9e1c2c",
    "scarlet red": "#d4202a",
    "scarlet lake": "#c44838",
    "dark brown": "#4a3020",
    "crimson": "#8e1830",
    "burgundy": "#6e2030",
    "claret red": "#7a2430",
    "pearl grey": "#c8c4bc",
    "tuscan red": "#8a3030",
    "maroon": "#5c2028",
    "sunshine yellow": "#f0c020",
    "corn yellow": "#e6c040",
    "jasmine": "#e8d070",
    "mustard yellow": "#c4a020",
    "terra cotta brown": "#8a5040",
    "deep yellow": "#e0b000",
    "spanish orange": "#e07020",
    "orange yellow": "#e89020",
    "brown": "#6a4030",
    "maize": "#e8d060",
    "saddle brown": "#6a4428",
    "light green": "#6aaa50",
    "nile green": "#4a9860",
    "medium light green": "#3e9848",
    "true green": "#1e7a32",
    "grass green": "#3a8a30",
    "chrome green": "#1a6830",
    "marine green": "#1a7868",
    "campus green": "#2a8a48",
    "hunter green": "#1a5a30",
    "bottle green": "#1a6840",
    "ice green": "#b8d8c0",
    "lawn green": "#4aaa40",
    "sky blue": "#70b0dc",
    "cerulean blue": "#2a88c0",
    "true blue": "#1a58b0",
    "violet blue": "#4050a0",
    "ultramarine blue": "#2030a0",
    "midnight blue": "#101848",
    "cobalt blue": "#2040b0",
    "royal blue": "#1a3898",
    "cloud blue": "#88c0d8",
    "periwinkle blue": "#7080c0",
    "blueberry": "#3050a0",
    "delft blue": "#204888",
    "cornflower blue": "#5080c8",
    "aquamarine blue": "#3aa0a8",
    "violet": "#6840a0",
    "mauve": "#886088",
    "grape": "#5a3068",
    "black grape": "#3a2048",
    "royal purple": "#582878",
    "orchid": "#b070a0",
    "blue violet": "#4030a0",
    "concord grape": "#4a2858",
    "lilac": "#b090c0",
    "medium violet": "#7040a0",
    "lavender blue": "#6878b0",
    "plum": "#6a3058",
    "blue": "#1a4c96",
    "white": "#f4f1ea",
    "orange": "#e07028",
    "brick red": "#a04030",
    "grey": "#8a8884",
    "gray": "#8a8884",
    "tan": "#c4a878",
    "yellow ochre": "#c49830",
    "black": "#161616",
    "pearl gray": "#c8c4bc",
}


def load_chart():
    path = os.path.normpath(os.path.join(
        os.path.expanduser("~"),
        ".cursor/projects/Users-pebbles-Documents-Projects-MTA-Tracker/agent-tools/2ae3ef21-6f6b-459f-b55f-d5710b2469c9.txt",
    ))
    rows = []
    skip = {"station", "red family", "yellow family", "green family", "blue family", "purple family", "no color", "color only on station plaque", "stations not in the original ind with tiles", "list of ind tile colors by station (underground stations only)"}
    with open(path) as handle:
        for line in handle:
            if not line.startswith("|"):
                continue
            parts = [part.strip() for part in line.strip().strip("|").split("|")]
            if len(parts) < 2:
                continue
            name = parts[0]
            band = re.sub(r"\s*\[[^\]]*\]", "", parts[1] if len(parts) > 1 else "").strip()
            border = re.sub(r"\s*\[[^\]]*\]", "", parts[2] if len(parts) > 2 else "").strip()
            if name.lower() in skip or not band or band.startswith("["):
                continue
            rows.append((name, band, border))
    return rows


WORD_NUM = {
    "first": "1st", "second": "2nd", "third": "3rd", "fourth": "4th",
    "fifth": "5th", "sixth": "6th", "seventh": "7th", "eighth": "8th",
    "ninth": "9th",
}


def tokens(name):
    name = name.lower().replace("–", " ").replace("—", " ").replace("-", " ").replace("/", " ")
    name = re.sub(
        r"(^|\s)([ewns])(?=\s+\d)",
        lambda match: match.group(1) + {"e": "east", "w": "west", "n": "north", "s": "south"}[match.group(2)],
        name,
    )
    name = re.sub(r"\b(\d+)\b", lambda match: ordinal(int(match.group(1))).lower(), name)
    name = re.sub(
        r"\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth)\b",
        lambda match: WORD_NUM[match.group(1)],
        name,
    )
    for pattern, replacement in ABBREV:
        name = re.sub(rf"\b{pattern.lower()}\b", replacement.lower(), name)
    drop = {
        "the", "and", "of", "street", "streets", "avenue", "avenues",
        "boulevard", "road", "place", "parkway",
    }
    return [token for token in re.findall(r"[a-z0-9]+", name) if token not in drop]


# Same chart name, two stations. Keyed by id so the 8th Avenue and 6th Avenue
# stops do not share one band.
IND_OVERRIDE = {
    "A30": ("deep yellow", ""),
    "D18": ("medium light green", "true green"),
    "A31": ("mustard yellow", "terra cotta brown"),
    "D19": ("medium light green", "true green"),
    "A28": ("burgundy", "black"),
    "D17": ("deep yellow", "yellow ochre"),
    "A27": ("orchid", "black"),
    "D16": ("scarlet red", "dark brown"),
    "F24": ("orange yellow", "brown"),
    "D14": ("royal purple", "black"),
    "A38": ("violet", "grape"),
    "G36": ("light green", "true green"),
    "A11": ("orange yellow", ""),
    "A46": ("maize", "saddle brown"),
    "F27": ("burgundy", "maroon"),
    "D22": ("blue", ""),
    "G14": ("violet blue", "black"),
    "A17": ("midnight blue", ""),
}


def colors_from_names(band, border):
    field = COLOR_HEX.get(band.lower())
    edge = COLOR_HEX.get(border.lower()) if border else None
    if not field:
        return None
    if not edge:
        edge = tiles.darken(field)
    return shades(field), shades(edge), luminance(field) > 150


def chart_colors(station_id, name, rows):
    if station_id.startswith("H"):
        return None
    if station_id in IND_OVERRIDE:
        band, border = IND_OVERRIDE[station_id]
        return colors_from_names(band, border)
    wanted_list = tokens(name)
    wanted = set(wanted_list)
    hits = []
    for chart_name, band, border in rows:
        have_list = tokens(chart_name)
        have = set(have_list)
        if not have:
            continue
        if have == wanted:
            hits.append((100 + len(have), chart_name, band, border))
            continue
        chart_numbers = {token for token in have if token[:1].isdigit()}
        station_numbers = {token for token in wanted if token[:1].isdigit()}
        if chart_numbers != station_numbers:
            continue
        if have <= wanted and len(have) >= 2:
            hits.append((len(have), chart_name, band, border))
        elif have <= wanted and wanted_list[:len(have_list)] == have_list:
            hits.append((10, chart_name, band, border))
        elif have <= wanted and len(have) == 1 and next(iter(have))[:1].isdigit():
            hits.append((10, chart_name, band, border))
        elif wanted <= have:
            hits.append((len(wanted), chart_name, band, border))
    if not hits:
        return None
    hits.sort(key=lambda item: item[0], reverse=True)
    best = hits[0][0]
    top = [item for item in hits if item[0] == best]
    _score, _chart, band, border = top[0]
    return colors_from_names(band, border)


BMT_FIELDS = ["blue", "red", "violet", "blue-green", "salmon"]
IRT_FIELDS = ["blue", "red", "green", "violet", "buff", "yellow", "blue-green"]
LIGHT_FIELDS = {"yellow", "buff", "salmon", "silver-blue"}

def trunk_colors(station_id):
    """Line color when the station is missing from the published chart."""
    prefix = station_id[:1]
    value = num(station_id)
    if prefix == "H":
        return "#3aa0a8", "#163848"
    if prefix == "G" and value >= 22:
        return "#1a5a30", "#161616"
    if prefix in {"E", "G"} or (prefix == "F" and value <= 12):
        return "#4a2858", "#161616"
    if prefix == "F" and value >= 20:
        return "#e07020", "#6a4030"
    if prefix == "F":
        return "#6840a0", "#4030a0"
    if prefix == "D" and value <= 13:
        return "#e0b000", "#161616"
    if prefix in {"B", "D"}:
        return "#d4202a", "#4a3020"
    return "#1a3898", "#161616"


def num(station_id):
    return int(station_id) if station_id.isdigit() else int(station_id[1:])


def family_of(station_id):
    if os.path.exists(os.path.join(ORIGINAL, f"{station_id}.png")):
        return "copy-original"
    if station_id == "901":
        return "copy-631"
    if station_id == "902":
        return "copy-127"
    if station_id in {"Q03", "Q04", "Q05", "726", "142", "138", "301"} or station_id.startswith("5"):
        return "enamel"
    if station_id.startswith("S") and station_id not in {"S01", "S03", "S04"}:
        return "enamel"
    if station_id.startswith("R") or station_id == "Q01" or station_id.startswith("N") or station_id.startswith("J") or station_id.startswith("L") or station_id.startswith("M"):
        return "bmt"
    if station_id.startswith("B") and num(station_id) >= 12:
        return "bmt"
    if station_id.startswith("D") and num(station_id) >= 24:
        return "bmt"
    if station_id in {"S01", "S03", "S04"}:
        return "bmt"
    if station_id.isdigit():
        value = int(station_id)
        if 601 <= value <= 619 or 621 <= value <= 630 or 401 <= value <= 416 or 236 <= value <= 257 or 201 <= value <= 222 or 128 <= value <= 139 or value == 228 or station_id.startswith("7"):
            if station_id == "726" or station_id == "138":
                return "enamel"
            return "irt"
    if station_id[:1] in {"A", "B", "D", "E", "F", "G", "H"}:
        return "ind"
    return "enamel"


def ink_for(field_name=None, light=False):
    if light or field_name in LIGHT_FIELDS:
        return tiles.INK
    return tiles.CREAM


def build_bmt(text, field_name):
    field = tiles.FIELD_PALETTES[field_name]
    return tiles.build_layered(
        text,
        [
            (tiles.GREEN_LARGE, 3, 5, 3, 2, tiles.GROUT["bmt-outer"]),
            (tiles.GOLD, 2, 1, 1, 1, tiles.GROUT["bmt-gold"]),
            (tiles.GREEN_SMALL, 1, 1, 1, 1, tiles.GROUT["bmt-inner"]),
        ],
        field,
        ink_for(field_name),
        gloss_first=True,
    )


def build_irt(text, field_name):
    field = tiles.FIELD_PALETTES[field_name]
    return tiles.build_layered(
        text,
        [
            (tiles.OLIVE, 2, 4, 2, 2, tiles.GROUT["irt-frame"]),
            (tiles.PINSTRIPE, 1, 1, 1, 1, tiles.GROUT["irt-pin"]),
        ],
        field,
        tiles.WHITE if field_name == "red" else ink_for(field_name),
    )


def build_ind(text, field_colors, border_colors, light):
    return tiles.build_layered(
        text,
        [(border_colors, 2, 1, 1, 1, tiles.darken(border_colors[0]))],
        field_colors,
        tiles.INK if light else tiles.WHITE,
    )


def build_enamel(text):
    white = ["#f7f4ee", "#fbf9f4", "#f3f0e8", "#fffcf7", "#efece4"]
    black = ["#1a1a1a", "#141414", "#222222"]
    return tiles.build_layered(
        text,
        [(black, 2, 1, 1, 1, "#0e0e0e")],
        white,
        tiles.INK,
    )


def main():
    os.makedirs(OUT, exist_ok=True)
    chart = load_chart()
    stations = get_stations()
    groups = {}
    plan = []
    for station in stations:
        kind = family_of(station["id"])
        groups.setdefault(kind, []).append(station)
        plan.append((station, kind))

    field_index = {}
    for kind in ("bmt", "irt"):
        ordered = sorted(groups.get(kind, []), key=lambda station: station["id"])
        cycle = BMT_FIELDS if kind == "bmt" else IRT_FIELDS
        for index, station in enumerate(ordered):
            field_index[station["id"]] = cycle[index % len(cycle)]

    made = {"copy-original": 0, "copy-631": 0, "copy-127": 0, "bmt": 0, "irt": 0, "ind": 0, "enamel": 0}
    unmatched = []
    for station, kind in plan:
        station_id = station["id"]
        dest = os.path.join(OUT, f"{station_id}.png")
        if kind == "copy-original":
            shutil.copyfile(os.path.join(ORIGINAL, f"{station_id}.png"), dest)
        elif kind == "copy-631":
            shutil.copyfile(os.path.join(ORIGINAL, "631.png"), dest)
        elif kind == "copy-127":
            shutil.copyfile(os.path.join(ORIGINAL, "127.png"), dest)
        else:
            text = tablet_text(station["name"])
            if station_id in {"635", "R20", "L03"}:
                text = "UNION SQUARE"
                canvas = build_bmt(text, "green")
                kind = "bmt"
            elif station_id == "634":
                text = "23RD STREET"
                canvas = build_irt(text, "red")
                kind = "irt"
            elif station_id == "R19":
                text = "23RD STREET"
                canvas = build_bmt(text, "blue")
                kind = "bmt"
            elif kind == "bmt":
                canvas = build_bmt(text, field_index[station_id])
            elif kind == "irt":
                canvas = build_irt(text, field_index[station_id])
            elif kind == "ind":
                colors = chart_colors(station_id, station["name"], chart)
                if colors is None:
                    unmatched.append(f"{station_id} {station['name']}")
                    field_hex, border_hex = trunk_colors(station_id)
                    colors = (shades(field_hex), shades(border_hex), luminance(field_hex) > 150)
                field_colors, border_colors, light = colors
                canvas = build_ind(text, field_colors, border_colors, light)
            else:
                canvas = build_enamel(text)
            tiles.png_for(canvas, dest)
        made[kind] = made.get(kind, 0) + 1
        print(station_id, kind, tablet_text(station["name"]) if kind not in {"copy-original", "copy-631", "copy-127"} else "copied")
    print("COUNTS", made, "unmatched", len(unmatched))
    for line in unmatched:
        print("UNMATCHED", line)


if __name__ == "__main__":
    main()
