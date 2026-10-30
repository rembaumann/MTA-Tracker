"""Digital Vickers name tablets.

BMT Broadway (N/Q/R/W) is a blue field with cream letters.
IRT Lexington (6) is a terracotta field with white letters.
Union Square is the mezzanine tablet that reads UNION SQUARE: white
letters on a green field. The station record describes that palette
and not the border, so the border reuses the green-and-gold Dual
Contracts frame from the Broadway tablet.
Recolor the field, the letters, and the bands for another station.

Needs Pillow. Run: python3 design/generate_tablets.py
"""

import os
import re
import sys
from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

PITCH = 12
MAIN_H = 16
RD_H = 7
THRESHOLD = 168

BLUES = [
    "#1a4c96", "#1e56a4", "#174484", "#245eae", "#14386e",
    "#1a4c96", "#2868b8", "#163e78", "#1c509c", "#123468",
    "#2058a8", "#1a4c96", "#15407e", "#2a62b0",
]
# Darker and more varied than the ceramic frame, so the gold band still reads.
GREENS = [
    "#0e4e28", "#145c30", "#0a4220", "#186838", "#08381c",
    "#105028", "#1a7040", "#083c1c", "#125830", "#063018",
    "#166434", "#0e4824", "#1c7844", "#0a4020", "#145832",
]
CREAM = ["#f4e6be", "#ead8a2", "#f8efd2", "#e4d09a", "#fbf4de", "#f0e0b0"]
WHITE = ["#f6f3ec", "#ffffff", "#eeeae2", "#fbf9f4", "#e6e0d4"]
GREEN_LARGE = ["#2f9e3e", "#1f8a30", "#3cb34a", "#187a28", "#34a844", "#146e22", "#46be52", "#228a34"]
GOLD = ["#e2b44a", "#d09a2c", "#c88824", "#f0cc68", "#b8801c", "#d8ae4e", "#c47228", "#e8c670", "#d8b45a"]
GREEN_SMALL = ["#2e9840", "#1c7830", "#38a848", "#146824", "#46b050", "#125c20", "#2a8838"]
REDS = [
    "#9a3a28", "#863022", "#a84630", "#76281e", "#b45436",
    "#9a3a28", "#6c241c", "#a44a32", "#822e24", "#c06240", "#7a2c22",
]
ACCENTS = ["#1a2744", "#221c40", "#141820", "#243628", "#1c3058", "#3a2060", "#152038"]
OLIVE = ["#6c7058", "#5e624a", "#7c8068", "#64684e", "#868a70", "#585c44"]
PINSTRIPE = ["#d4b044", "#c49a34", "#5e8440", "#346432", "#e2c864", "#8a7040", "#2a5830", "#c4a050"]
TAN = ["#c6ae78", "#b89c66", "#d2ba86", "#a88e56", "#c8b078", "#d8c294", "#b49660"]
MAROON = ["#7a342c", "#622824", "#8a3c30"]
BROWN = ["#5c4030", "#3e2c22", "#6a4834"]
MOTIF = ["#4e3428", "#3a2820", "#5c4030"]
MOTIF_GREEN = ["#3e6840", "#4a7850"]
WALL = ["#f5f3ee", "#fbfaf7", "#f2efe8", "#f7f5f0"]
CEILING = "#1c212c"

GROUT = {
    "bmt-outer": "#0c3012",
    "bmt-gold": "#6a4814",
    "bmt-inner": "#0e3414",
    "bmt-field": "#0c1c38",
    "union-field": "#0a2414",
    "irt-frame": "#2a2c22",
    "irt-pin": "#3a3018",
    "irt-field": "#2a100c",
    "frieze": "#5c4830",
    "wall": "#d4cfc4",
}


def pick(palette, x, y, salt=0):
    n = (x * 73856093) ^ (y * 19349663) ^ (salt * 83492791)
    n &= 0xFFFFFFFF
    n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
    return palette[n % len(palette)]


_FONT_CACHE = {}


def font_for(tiles_h, sample=8):
    key = tiles_h
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    target = tiles_h * sample
    size = 160
    font = ImageFont.truetype(FONT, size)
    for _ in range(12):
        bb = font.getbbox("H")
        cap = bb[3] - bb[1]
        if abs(cap - target) <= 1:
            break
        size = max(12, round(size * target / max(cap, 1)))
        font = ImageFont.truetype(FONT, size)
    _FONT_CACHE[key] = (font, sample)
    return font, sample


def glyph_mask(char, tiles_h, x_scale=1.0):
    """Tile mask for one character, aligned to the cap height. Rows may
    include a tile of overhang above or below the cap box."""
    font, sample = font_for(tiles_h)
    cap = font.getbbox("H")
    cap_top, baseline = cap[1], cap[3]
    ink = font.getbbox(char)
    left = ink[0] - sample
    right = ink[2] + sample
    top = min(cap_top, ink[1]) - 1
    bot = max(baseline, ink[3]) + 1
    im = Image.new("L", (max(1, right - left), max(1, bot - top)), 0)
    ImageDraw.Draw(im).text((-left, -top), char, font=font, fill=255)
    if x_scale != 1:
        im = im.resize((max(1, round(im.width * x_scale)), im.height), Image.Resampling.LANCZOS)
    cols = im.width // sample
    rows = im.height // sample
    mask = []
    for r in range(rows):
        row = []
        for c in range(cols):
            cell = im.crop((c * sample, r * sample, (c + 1) * sample, (r + 1) * sample))
            avg = sum(cell.getdata()) / (sample * sample)
            row.append(avg >= THRESHOLD)
        mask.append(row)
    keep = [c for c in range(cols) if any(mask[r][c] for r in range(rows))]
    if not keep:
        return [], 0
    trimmed = [[row[c] for c in keep] for row in mask]
    # Row 0 of the mask corresponds to pixel `top`. Cap top is cap_top.
    # After x-scale, vertical pixels are unchanged, so the cap-top row is:
    cap_row = (cap_top - top) // sample
    # Drop empty rows, and shift cap_row with them.
    while trimmed and not any(trimmed[0]):
        trimmed.pop(0)
        cap_row -= 1
    while trimmed and not any(trimmed[-1]):
        trimmed.pop()
    return trimmed, cap_row


class Canvas:
    def __init__(self):
        self.groups = []  # (name, shapes) shapes are (x, y, w, h, fill, opacity)
        self._current = None

    def group(self, name):
        self._current = []
        self.groups.append((name, self._current))

    def rect(self, x, y, w, h, fill, opacity=1):
        if w <= 0 or h <= 0:
            return
        self._current.append((round(x), round(y), round(w), round(h), fill, opacity))

    def cell(self, col, row, fill, span_c=1, span_r=1, inset=1):
        self.rect(
            col * PITCH + inset,
            row * PITCH + inset,
            span_c * PITCH - 2 * inset,
            span_r * PITCH - 2 * inset,
            fill,
        )

    def bounds(self):
        max_x = max_y = 0
        for _, shapes in self.groups:
            for x, y, w, h, _, _ in shapes:
                max_x = max(max_x, x + w)
                max_y = max(max_y, y + h)
        return max_x, max_y


def frame_tiles(x, y, w, h, thick, tile_w, tile_h):
    """Cell rects (col, row, span_c, span_r) forming a picture frame."""
    tiles = []

    def along(length, size):
        pos = 0
        while pos < length:
            tiles_size = min(size, length - pos)
            yield pos, tiles_size
            pos += size

    for pos, span in along(w, tile_w):
        tiles.append((x + pos, y, span, thick))
        tiles.append((x + pos, y + h - thick, span, thick))
    inner_h = h - 2 * thick
    for pos, span in along(inner_h, tile_h):
        tiles.append((x, y + thick + pos, thick, span))
        tiles.append((x + w - thick, y + thick + pos, thick, span))
    return tiles


def diamond_cells(cx, cy, radius, hole=0):
    cells = []
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            dist = abs(dx) + abs(dy)
            if hole <= dist <= radius:
                cells.append((cx + dx, cy + dy))
    return cells


def place_mask(mask, origin_c, origin_r, cap_row, target_row):
    """Return letter cells. target_row is where the cap top should land."""
    cells = []
    shift = target_row - cap_row
    for r, row in enumerate(mask):
        for c, on in enumerate(row):
            if on:
                cells.append((origin_c + c, origin_r + shift + r))
    width = len(mask[0]) if mask else 0
    return cells, width


def word_cells(text, tiles_h, x, cap_row_target, gap, x_scale):
    cells = []
    cursor = x
    for char in text:
        mask, cap_row = glyph_mask(char, tiles_h, x_scale=x_scale)
        placed, width = place_mask(mask, cursor, 0, cap_row, cap_row_target)
        cells.extend(placed)
        cursor += width + gap
    return cells, cursor


def build_union_letters():
    """UNION SQUARE, no ordinal and no diamond. Cap tops share one row."""
    gap = 2
    cells, cursor = word_cells("UNION", MAIN_H, 0, 0, gap, 1.0)
    word_gap = 8
    square_x = cursor - gap + word_gap
    square, _cursor = word_cells("SQUARE", MAIN_H, square_x, 0, gap, 1.0)
    cells.extend(square)
    return _padded(cells, (4, 4, 2, 2))


def _padded(cells, pad):
    cols = [c for c, _ in cells]
    rows = [r for _, r in cells]
    min_c, max_c = min(cols), max(cols)
    min_r, max_r = min(rows), max(rows)
    left, right, top, bottom = pad
    shift_c = left - min_c
    shift_r = top - min_r
    shifted = [(c + shift_c, r + shift_r) for c, r in cells]
    field_w = max_c - min_c + 1 + left + right
    field_h = max_r - min_r + 1 + top + bottom
    return shifted, field_w, field_h


def build_letters(kind):
    """Letter cells in field coordinates, plus the field size (w, h)."""
    gap_num = 1
    gap_word = 3
    cells, cursor = word_cells("23", MAIN_H, 0, 0, gap_num, 1.0)
    cursor += 1
    rd_x = cursor
    rd_cells, cursor = word_cells("RD", RD_H, cursor, 1, 1, 0.95)
    cells.extend(rd_cells)
    rd_right = cursor - 1

    if kind == "bmt":
        # Two square dots under the ordinal, then a diamond pointing at STREET.
        rd_mid = (rd_x + rd_right) // 2
        dot = 2
        dots_x = rd_mid - dot - 1
        dot_y = MAIN_H - 5
        for i in range(2):
            for dy in range(dot):
                for dx in range(dot):
                    cells.append((dots_x + i * (dot + 1) + dx, dot_y + dy))
        dia_r = 3
        dia_cx = rd_right + 2 + dia_r
        dia_cy = MAIN_H // 2
        cells.extend(diamond_cells(dia_cx, dia_cy, dia_r))
        street_x = dia_cx + dia_r + 3
        pad = (3, 5, 2, 2)
    else:
        street_x = rd_right + 10
        pad = (8, 8, 3, 3)

    street, cursor = word_cells("STREET", MAIN_H, street_x, 0, gap_word, 0.92)
    cells.extend(street)
    return _padded(cells, pad)


def paint_frame(canvas, x, y, w, h, thick, tile_w, tile_h, palette, salt, inset):
    for col, row, sw, sh in frame_tiles(x, y, w, h, thick, tile_w, tile_h):
        canvas.cell(col, row, pick(palette, col, row, salt), sw, sh, inset=inset)


def add_wall(canvas, width, height):
    canvas.group("wall")
    size = PITCH * 6
    grout = 4
    col = 0
    x = 0
    while x < width:
        row = 0
        y = 0
        while y < height:
            canvas.rect(x + grout / 2, y + grout / 2, size - grout, size - grout, pick(WALL, col, row))
            y += size
            row += 1
        x += size
        col += 1


def build_bmt():
    letters, fw, fh = build_letters("bmt")
    outer, gold, inner = 3, 2, 1
    band = outer + gold + inner
    total_w = fw + band * 2
    total_h = fh + band * 2
    wall_margin = 8
    canvas = Canvas()
    width_px = (total_w + wall_margin) * PITCH
    height_px = (total_h + wall_margin) * PITCH
    add_wall(canvas, width_px, height_px)

    ox = wall_margin // 2
    oy = wall_margin // 2

    canvas.group("band-outer")
    canvas.rect(ox * PITCH, oy * PITCH, total_w * PITCH, total_h * PITCH, GROUT["bmt-outer"])
    paint_frame(canvas, ox, oy, total_w, total_h, outer, 5, 3, GREEN_LARGE, 1, inset=2)

    gx, gy = ox + outer, oy + outer
    gw, gh = total_w - outer * 2, total_h - outer * 2
    canvas.group("band-gold")
    canvas.rect(gx * PITCH, gy * PITCH, gw * PITCH, gh * PITCH, GROUT["bmt-gold"])
    paint_frame(canvas, gx, gy, gw, gh, gold, 1, 1, GOLD, 2, inset=1)

    ix, iy = gx + gold, gy + gold
    iw, ih = gw - gold * 2, gh - gold * 2
    canvas.group("band-inner")
    canvas.rect(ix * PITCH, iy * PITCH, iw * PITCH, ih * PITCH, GROUT["bmt-inner"])
    paint_frame(canvas, ix, iy, iw, ih, inner, 1, 1, GREEN_SMALL, 3, inset=1)

    fx, fy = ix + inner, iy + inner
    canvas.group("field")
    canvas.rect(fx * PITCH, fy * PITCH, fw * PITCH, fh * PITCH, GROUT["bmt-field"])
    letter_set = set(letters)
    for row in range(fh):
        for col in range(fw):
            if (col, row) in letter_set:
                continue
            canvas.cell(fx + col, fy + row, pick(BLUES, col, row, 4))

    canvas.group("letters")
    for col, row in letters:
        canvas.cell(fx + col, fy + row, pick(CREAM, col, row, 5))

    gloss_large_tiles(canvas, "band-outer")
    return canvas


def build_union():
    """White letters on a green field, Broadway frame, no surrounding wall."""
    letters, fw, fh = build_union_letters()
    outer, gold, inner = 3, 2, 1
    band = outer + gold + inner
    total_w = fw + band * 2
    total_h = fh + band * 2
    canvas = Canvas()

    canvas.group("band-outer")
    canvas.rect(0, 0, total_w * PITCH, total_h * PITCH, GROUT["bmt-outer"])
    paint_frame(canvas, 0, 0, total_w, total_h, outer, 5, 3, GREEN_LARGE, 1, inset=2)

    gx, gy = outer, outer
    gw, gh = total_w - outer * 2, total_h - outer * 2
    canvas.group("band-gold")
    canvas.rect(gx * PITCH, gy * PITCH, gw * PITCH, gh * PITCH, GROUT["bmt-gold"])
    paint_frame(canvas, gx, gy, gw, gh, gold, 1, 1, GOLD, 2, inset=1)

    ix, iy = gx + gold, gy + gold
    iw, ih = gw - gold * 2, gh - gold * 2
    canvas.group("band-inner")
    canvas.rect(ix * PITCH, iy * PITCH, iw * PITCH, ih * PITCH, GROUT["bmt-inner"])
    paint_frame(canvas, ix, iy, iw, ih, inner, 1, 1, GREEN_SMALL, 3, inset=1)

    fx, fy = ix + inner, iy + inner
    canvas.group("field")
    canvas.rect(fx * PITCH, fy * PITCH, fw * PITCH, fh * PITCH, GROUT["union-field"])
    letter_set = set(letters)
    for row in range(fh):
        for col in range(fw):
            if (col, row) in letter_set:
                continue
            canvas.cell(fx + col, fy + row, pick(GREENS, col, row, 4))

    canvas.group("letters")
    for col, row in letters:
        canvas.cell(fx + col, fy + row, pick(WHITE, col, row, 5))

    gloss_large_tiles(canvas, "band-outer")
    return canvas


def build_irt():
    letters, fw, fh = build_letters("irt")
    pin, frame = 1, 2
    band = pin + frame
    tablet_w = fw + band * 2
    tablet_h = fh + band * 2

    frieze_h = 12
    gap = 6  # white-tile gap between frieze and tablet, in cells
    ceiling_h = 7
    wall_below = 8
    side = 6
    total_w = tablet_w + side * 2
    frieze_top = ceiling_h
    tablet_top = frieze_top + frieze_h + gap
    total_h = tablet_top + tablet_h + wall_below

    canvas = Canvas()
    add_wall(canvas, total_w * PITCH, total_h * PITCH)

    canvas.group("ceiling")
    canvas.rect(0, 0, total_w * PITCH, ceiling_h * PITCH, CEILING)

    paint_frieze(canvas, 0, frieze_top, total_w, frieze_h)

    ox = side
    oy = tablet_top
    canvas.group("frame")
    canvas.rect(ox * PITCH, oy * PITCH, tablet_w * PITCH, tablet_h * PITCH, GROUT["irt-frame"])
    paint_frame(canvas, ox, oy, tablet_w, tablet_h, frame, 4, 2, OLIVE, 6, inset=2)

    px, py = ox + frame, oy + frame
    pw, ph = tablet_w - frame * 2, tablet_h - frame * 2
    canvas.group("pinstripe")
    canvas.rect(px * PITCH, py * PITCH, pw * PITCH, ph * PITCH, GROUT["irt-pin"])
    paint_frame(canvas, px, py, pw, ph, pin, 1, 1, PINSTRIPE, 7, inset=1)

    fx, fy = px + pin, py + pin
    canvas.group("field")
    canvas.rect(fx * PITCH, fy * PITCH, fw * PITCH, fh * PITCH, GROUT["irt-field"])
    letter_set = set(letters)
    for row in range(fh):
        for col in range(fw):
            if (col, row) in letter_set:
                continue
            canvas.cell(fx + col, fy + row, pick(REDS, col, row, 8))

    canvas.group("field-accent")
    for row in range(fh):
        for col in range(fw):
            if (col, row) in letter_set:
                continue
            n = (col * 73856093) ^ (row * 19349663) ^ (9 * 83492791)
            n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
            if n % 9 == 0:
                # Repaint this cell in the accent group so the red tile underneath
                # is covered. The red tile is already drawn; draw accent on top.
                canvas.cell(fx + col, fy + row, pick(ACCENTS, col, row, 9))

    canvas.group("letters")
    for col, row in letters:
        canvas.cell(fx + col, fy + row, pick(WHITE, col, row, 10))
    return canvas


def paint_frieze(canvas, x, y, w, h):
    canvas.group("frieze")
    canvas.rect(x * PITCH, y * PITCH, w * PITCH, h * PITCH, GROUT["frieze"])
    for row in range(h):
        if row in (0, h - 1):
            palette = BROWN
        elif row in (2, h - 3):
            palette = MAROON
        else:
            palette = TAN
        for col in range(w):
            canvas.cell(x + col, y + row, pick(palette, col, row, 11))

    canvas.group("frieze-motif")
    cy = y + h // 2
    cx = x + 14
    while cx < x + w - 10:
        for col, row in diamond_cells(cx, cy, 4, hole=2):
            if x <= col < x + w and y <= row < y + h:
                canvas.cell(col, row, pick(MOTIF, col, row, 12))
        for col, row in diamond_cells(cx, cy, 1):
            canvas.cell(col, row, pick(TAN, col, row, 13))
        # The X through the diamond, which reads as the bowtie on the real frieze.
        for d in range(-3, 4):
            for col, row in ((cx + d, cy + d), (cx + d, cy - d)):
                if abs(d) > 1 and y < row < y + h - 1:
                    canvas.cell(col, row, pick(MOTIF, col, row, 14))
        cx += 22


def gloss_large_tiles(canvas, group_name):
    """A pale stripe along the top of each large ceramic tile."""
    shapes = None
    for name, group in canvas.groups:
        if name == group_name:
            shapes = group
            break
    canvas.group(group_name + "-glaze")
    for x, y, w, h, _, _ in shapes:
        # Skip the grout rectangle behind the tiles. Only the ceramic tiles get a glaze stripe.
        if PITCH < h <= PITCH * 4 and PITCH < w <= PITCH * 8:
            canvas.rect(x, y, w, max(2, round(h * 0.28)), "#ffffff", 0.35)


def svg_for(canvas, label, subtitle, prefix):
    width, height = canvas.bounds()
    pad = 28
    label_h = 64
    total_w = width + pad * 2
    total_h = height + pad * 2 + label_h
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{total_h}" '
        f'viewBox="0 0 {total_w} {total_h}">',
        f'<rect id="{prefix}-backdrop" width="100%" height="100%" fill="#efece4"/>',
        f'<g id="{prefix}" transform="translate({pad},{pad})">',
    ]
    for name, shapes in canvas.groups:
        parts.append(f'<g id="{prefix}-{name}">')
        for x, y, w, h, fill, opacity in shapes:
            extra = f' fill-opacity="{opacity:.2f}"' if opacity < 1 else ""
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"{extra}/>')
        parts.append("</g>")
    parts.append("</g>")
    text_y = height + pad + 36
    parts.append(
        f'<text x="{pad}" y="{text_y}" font-family="Arial, Helvetica, sans-serif" '
        f'font-size="22" fill="#1c1c1c">{label}</text>'
    )
    parts.append(
        f'<text x="{pad}" y="{text_y + 26}" font-family="Arial, Helvetica, sans-serif" '
        f'font-size="15" fill="#5c5c5c">{subtitle}</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def png_for(canvas, path):
    width, height = canvas.bounds()
    image = Image.new("RGBA", (width, height), (239, 236, 228, 255))
    for _, shapes in canvas.groups:
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        for x, y, w, h, fill, opacity in shapes:
            color = tuple(int(fill[i:i + 2], 16) for i in (1, 3, 5))
            draw.rectangle(
                [x, y, x + w - 1, y + h - 1],
                fill=color + (round(opacity * 255),),
            )
        image = Image.alpha_composite(image, overlay)
    image.convert("RGB").save(path)
    return image


# Original IRT name tablets. Field and band colors are the 1978 Heins & LaFarge
# inventory (Framberger, nycsubway.org), which records the tablet, the tile
# band, and the cornice separately. The frame uses the band and, when it
# contrasts, the cornice. White cornices are left off so the sign stays the
# colored tablet. Stations marked unrecorded were not in that inventory.
LIGHT_BLUE = ["#6aa8d4", "#5a98c8", "#7eb6dc", "#4e8cbc", "#8ec0e4", "#3e7cac", "#98c8ea"]
BLUE_GREEN = ["#1a6a58", "#146050", "#207868", "#0e5444", "#248070", "#105848", "#1c7464", "#0a4838"]
YELLOW = ["#e2b84a", "#d4a838", "#f0c85e", "#c89830", "#e8c060", "#b88828", "#f2d070"]
PINK = ["#d88890", "#c87880", "#e4989c", "#b86874", "#eca8ac", "#a85868"]
VIOLET = ["#6a5088", "#5a4078", "#7a6098", "#4a3068", "#8a70a8", "#3e2858", "#746090"]
SALMON = ["#d47868", "#c46858", "#e08878", "#b45848", "#e89888", "#a84838", "#dc8070"]
SILVER_BLUE = ["#b7c6d2", "#a8bac8", "#c6d4de", "#98aec0", "#d0dce6", "#8aa4b6"]
MULTI = ["#1a4c96", "#1f6b38", "#8a4030", "#5a4870", "#1a5c6a", "#8a6820", "#6a3038", "#245e3a", "#3a3060", "#1c4068"]
INK = ["#1c140e", "#241810", "#14100c", "#2a1c12", "#181410"]

FIELD_PALETTES = {
    "blue": BLUES,
    "blue-green": BLUE_GREEN,
    "light-blue": LIGHT_BLUE,
    "green": ["#1b6a34", "#146028", "#22783c", "#0e5420", "#288444", "#105828", "#1a6430", "#0c4c1c"],
    "yellow": YELLOW,
    "red": REDS,
    "buff": TAN,
    "violet": VIOLET,
    "salmon": SALMON,
    "silver-blue": SILVER_BLUE,
    "multi": MULTI,
    "olive": OLIVE,
    "pink": PINK,
}
BAND_PALETTES = {
    "blue": BLUES,
    "light-blue": LIGHT_BLUE,
    "green": GREEN_SMALL,
    "buff": TAN,
    "yellow": YELLOW,
    "red": REDS,
    "pink": PINK,
    "violet": VIOLET,
    "blue-green": BLUE_GREEN,
    "multi": MULTI,
    "olive": OLIVE,
    "pinstripe": PINSTRIPE,
}


def darken(hex_color):
    red, green, blue = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return "#{:02x}{:02x}{:02x}".format(int(red * 0.28), int(green * 0.28), int(blue * 0.28))


def inscription_cells(text):
    """ONE LINE of mosaic capitals. 28TH keeps a small top-aligned ordinal."""
    gap = 1
    word_gap = 5
    cells = []
    cursor = 0
    for index, token in enumerate(text.split()):
        if index:
            cursor += word_gap
        match = re.match(r"^(\d+)(ST|ND|RD|TH)$", token)
        if match:
            part, cursor = word_cells(match.group(1), MAIN_H, cursor, 0, gap, 1.0)
            cells.extend(part)
            cursor = cursor - gap + 1
            part, cursor = word_cells(match.group(2), RD_H, cursor, 1, 1, 0.9)
            cells.extend(part)
            cursor -= 1
        else:
            scale = 0.9 if len(token) >= 8 else 1.0
            part, cursor = word_cells(token, MAIN_H, cursor, 0, gap, scale)
            cells.extend(part)
            cursor -= gap
    return _padded(cells, (4, 4, 2, 2))


def build_layered(text, layers, field_colors, ink_colors, gloss_first=False):
    """layers are (palette, thick, tile_w, tile_h, inset, grout) from outside in."""
    if text == "23RD STREET":
        letters, field_w, field_h = build_letters("bmt" if gloss_first else "irt")
    elif text == "UNION SQUARE":
        letters, field_w, field_h = build_union_letters()
    else:
        letters, field_w, field_h = inscription_cells(text)
    band = sum(layer[1] for layer in layers)
    total_w = field_w + band * 2
    total_h = field_h + band * 2
    canvas = Canvas()
    x = y = 0
    width, height = total_w, total_h
    for index, (palette, thick, tile_w, tile_h, inset, grout) in enumerate(layers):
        name = "band-outer" if index == 0 else f"band-{index}"
        canvas.group(name)
        canvas.rect(x * PITCH, y * PITCH, width * PITCH, height * PITCH, grout)
        paint_frame(canvas, x, y, width, height, thick, tile_w, tile_h, palette, 20 + index, inset=inset)
        x += thick
        y += thick
        width -= thick * 2
        height -= thick * 2
    letters_set = set(letters)
    canvas.group("field")
    canvas.rect(x * PITCH, y * PITCH, field_w * PITCH, field_h * PITCH, darken(field_colors[0]))
    for row in range(field_h):
        for col in range(field_w):
            if (col, row) in letters_set:
                continue
            canvas.cell(x + col, y + row, pick(field_colors, col, row, 4))
    canvas.group("letters")
    for col, row in letters:
        canvas.cell(x + col, y + row, pick(ink_colors, col, row, 5))
    if gloss_first:
        gloss_large_tiles(canvas, "band-outer")
    return canvas


def build_original(text, field_name, outer_name, inner_name, ink):
    letters, field_w, field_h = inscription_cells(text)
    bands = [(outer_name, 2)]
    if inner_name:
        bands.append((inner_name, 1))
    band = sum(thick for _, thick in bands)
    total_w = field_w + band * 2
    total_h = field_h + band * 2
    canvas = Canvas()
    x = y = 0
    width, height = total_w, total_h
    for index, (name, thick) in enumerate(bands):
        palette = BAND_PALETTES[name]
        canvas.group(f"band-{index}")
        canvas.rect(x * PITCH, y * PITCH, width * PITCH, height * PITCH, darken(palette[0]))
        paint_frame(canvas, x, y, width, height, thick, 1, 1, palette, 20 + index, inset=1)
        x += thick
        y += thick
        width -= thick * 2
        height -= thick * 2
    field = FIELD_PALETTES[field_name]
    letters_set = set(letters)
    canvas.group("field")
    canvas.rect(x * PITCH, y * PITCH, field_w * PITCH, field_h * PITCH, darken(field[0]))
    for row in range(field_h):
        for col in range(field_w):
            if (col, row) in letters_set:
                continue
            canvas.cell(x + col, y + row, pick(field, col, row, 4))
    ink_palette = INK if ink == "ink" else CREAM
    canvas.group("letters")
    for col, row in letters:
        canvas.cell(x + col, y + row, pick(ink_palette, col, row, 5))
    return canvas


# id, inscription, field, outer band, inner band, letter ink.
# inner "" means one band. 634 and 635 already have tablets.
# Unrecorded colors use a blue field and buff band, the common 1904 pair,
# except the deep stations, which follow 181st Street.
ORIGINAL_IRT = [
    ("640", "BROOKLYN BRIDGE", "salmon", "buff", "", "ink"),
    ("639", "CANAL STREET", "blue-green", "buff", "green", "cream"),
    ("638", "SPRING STREET", "blue", "light-blue", "", "cream"),
    ("637", "BLEECKER STREET", "blue", "light-blue", "", "cream"),
    ("636", "ASTOR PLACE", "blue", "green", "", "cream"),
    ("633", "28TH STREET", "blue", "buff", "", "cream"),
    ("632", "33RD STREET", "blue", "yellow", "buff", "cream"),
    ("631", "GRAND CENTRAL", "blue", "buff", "", "cream"),
    ("127", "TIMES SQUARE", "blue", "buff", "pink", "cream"),
    ("126", "50TH STREET", "green", "blue", "", "cream"),
    ("125", "COLUMBUS CIRCLE", "green", "red", "", "cream"),
    ("124", "66TH STREET", "yellow", "buff", "", "ink"),
    ("123", "72ND STREET", "multi", "buff", "", "cream"),
    ("122", "79TH STREET", "green", "blue", "buff", "cream"),
    ("121", "86TH STREET", "blue", "buff", "", "cream"),
    ("120", "96TH STREET", "red", "buff", "pink", "cream"),
    ("119", "103RD STREET", "green", "yellow", "pink", "cream"),
    ("118", "CATHEDRAL PKWY", "green", "buff", "red", "cream"),
    ("117", "116TH STREET", "blue", "blue-green", "", "cream"),
    ("116", "125TH STREET", "blue", "buff", "", "cream"),
    ("115", "137TH STREET", "silver-blue", "buff", "", "ink"),
    ("114", "145TH STREET", "blue", "light-blue", "", "cream"),
    ("113", "157TH STREET", "blue-green", "green", "buff", "cream"),
    ("112", "168TH STREET", "blue", "multi", "", "cream"),
    ("111", "181ST STREET", "blue", "multi", "", "cream"),
    ("110", "191ST STREET", "blue", "multi", "", "cream"),
    ("109", "DYCKMAN STREET", "blue-green", "buff", "", "cream"),
    ("108", "207TH STREET", "blue-green", "buff", "", "cream"),
    ("107", "215TH STREET", "blue-green", "buff", "", "cream"),
    ("106", "225TH STREET", "blue-green", "buff", "", "cream"),
    ("104", "231ST STREET", "blue-green", "buff", "", "cream"),
    ("103", "238TH STREET", "blue-green", "buff", "", "cream"),
    ("101", "242ND STREET", "blue-green", "buff", "", "cream"),
    ("227", "110TH STREET", "blue-green", "buff", "green", "cream"),
    ("226", "116TH STREET", "blue", "buff", "light-blue", "cream"),
    ("225", "125TH STREET", "blue", "green", "pink", "cream"),
    ("224", "135TH STREET", "blue-green", "violet", "", "cream"),
    ("302", "145TH STREET", "blue-green", "buff", "green", "cream"),
    ("420", "BOWLING GREEN", "blue", "buff", "", "cream"),
    ("419", "WALL STREET", "blue", "buff", "", "cream"),
    ("418", "FULTON STREET", "blue", "buff", "", "cream"),
    ("230", "WALL STREET", "blue", "buff", "", "cream"),
    ("229", "FULTON STREET", "blue", "buff", "", "cream"),
    ("231", "CLARK STREET", "blue", "olive", "pinstripe", "cream"),
    ("232", "BOROUGH HALL", "blue", "buff", "", "cream"),
    ("423", "BOROUGH HALL", "blue", "buff", "", "cream"),
    ("233", "HOYT STREET", "blue", "buff", "", "cream"),
    ("234", "NEVINS STREET", "blue", "buff", "", "cream"),
    ("235", "ATLANTIC AV", "blue", "buff", "", "cream"),
]


def write_original():
    folder = os.path.join(OUT_DIR, "irt-original")
    os.makedirs(folder, exist_ok=True)
    for station_id, text, field, outer, inner, ink in ORIGINAL_IRT:
        canvas = build_original(text, field, outer, inner, ink)
        path = os.path.join(folder, f"{station_id}.png")
        png_for(canvas, path)
        print(station_id, text, canvas.bounds())


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "original":
        write_original()
        return
    bmt = build_bmt()
    irt = build_irt()
    files = {
        "23rd-bmt-broadway.svg": svg_for(
            bmt,
            "23RD STREET",
            "BMT Broadway  ·  N Q R W  ·  blue field, cream letters, green and gold bands",
            "BMT",
        ),
        "23rd-irt-lexington.svg": svg_for(
            irt,
            "23RD STREET",
            "IRT Lexington Avenue  ·  6  ·  terracotta field, white letters, olive frame",
            "IRT",
        ),
    }
    for name, svg in files.items():
        path = os.path.join(OUT_DIR, name)
        with open(path, "w") as handle:
            handle.write(svg)
        print(name, len(svg))
    png_for(bmt, os.path.join(OUT_DIR, "preview-bmt.png"))
    png_for(irt, os.path.join(OUT_DIR, "preview-irt.png"))


if __name__ == "__main__":
    main()
