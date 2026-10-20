"""One-time: erase the sample numbers/date/time from the template so the bot can write new ones.

Each zone is refilled by interpolating, row by row, between the background just left and just
right of it, so the vertical gradient/gloss of the panels is kept.

  python tools/make_clean_bg.py          -> bot/assets/template-clean.png (+ out/clean-check.png)
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "bot" / "assets" / "template-original.jpg"
DST = ROOT / "bot" / "assets" / "template-clean.png"

# (name, x0, x1, approx_y_center, half_search_height, sample_left_x, sample_right_x)
PRICE_X = (230, 564, 226, 568)
ZONES = [
    ("p0", *PRICE_X[:2], 550, 36, *PRICE_X[2:]),
    ("p1", *PRICE_X[:2], 661, 36, *PRICE_X[2:]),
    ("p2", *PRICE_X[:2], 775, 36, *PRICE_X[2:]),
    ("p3", *PRICE_X[:2], 888, 36, *PRICE_X[2:]),
    ("p4", *PRICE_X[:2], 1002, 36, *PRICE_X[2:]),
    ("p5", *PRICE_X[:2], 1118, 36, *PRICE_X[2:]),
    ("p6", *PRICE_X[:2], 1233, 36, *PRICE_X[2:]),
    ("date", 538, 724, 436, 22, 520, 728),
    ("time", 186, 270, 436, 22, 178, 276),
]
PAD = 9  # extra rows above/below the detected glyphs (glow)


def glyph_rows(im, x0, x1, yc, half):
    """Rows (y) inside the search band that contain bright gold glyph pixels."""
    rows = []
    for y in range(yc - half, yc + half + 1):
        bright = 0
        for x in range(x0, x1, 2):
            r, g, b = im.getpixel((x, y))
            if r > 150 and g > 110:
                bright += 1
        if bright >= 2:
            rows.append(y)
    return rows


def main():
    im = Image.open(SRC).convert("RGB")
    out = im.copy()
    px = im.load()
    po = out.load()
    boxes = {}
    for name, x0, x1, yc, half, sl, sr in ZONES:
        rows = glyph_rows(im, x0, x1, yc, half)
        if not rows:
            raise SystemExit(f"zone {name}: no glyph found")
        y0, y1 = min(rows) - PAD, max(rows) + PAD
        boxes[name] = (x0, y0, x1, y1)
        for y in range(y0, y1 + 1):
            # average a few pixels at each side to avoid JPEG noise
            def side(x):
                pts = [px[x + dx, y + dy] for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
                return [sum(p[i] for p in pts) / len(pts) for i in range(3)]

            L, R = side(sl), side(sr)
            for x in range(x0, x1 + 1):
                t = (x - sl) / (sr - sl)
                po[x, y] = tuple(int(L[i] + (R[i] - L[i]) * t) for i in range(3))
    out.save(DST)

    check = out.copy()
    d = ImageDraw.Draw(check)
    for b in boxes.values():
        d.rectangle(b, outline=(255, 0, 0))
    (ROOT / "out").mkdir(exist_ok=True)
    check.save(ROOT / "out" / "clean-check.png")
    for k, v in boxes.items():
        print(k, v)


if __name__ == "__main__":
    main()
