"""רסטר של ``pathops.Path`` והשוואת לפני/אחרי — לדפי ההוכחה של הליטוש."""

from __future__ import annotations

from pathlib import Path

import pathops
from PIL import Image, ImageDraw, ImageFont
from fontTools.pens.recordingPen import RecordingPen

FLATNESS = 16
INK = (20, 20, 20)
BEFORE, AFTER = (205, 60, 60), (30, 110, 190)


def contours(path: pathops.Path) -> list[list[tuple[float, float]]]:
    rec = RecordingPen()
    path.draw(rec)
    polys, cur = [], []
    for verb, pts in rec.value:
        if verb == "moveTo":
            if cur:
                polys.append(cur)
            cur = [pts[0]]
        elif verb == "lineTo":
            cur.append(pts[0])
        elif verb in ("qCurveTo", "curveTo"):
            cur.extend(_flatten(cur[-1], verb, pts))
        elif verb == "closePath" and cur:
            polys.append(cur)
            cur = []
    if cur:
        polys.append(cur)
    return polys


def _flatten(p0, verb, pts):
    out = []
    if verb == "qCurveTo":
        c, p1 = pts[0], pts[-1] if pts[-1] is not None else p0
        for i in range(1, FLATNESS + 1):
            t = i / FLATNESS
            u = 1 - t
            out.append((u * u * p0[0] + 2 * u * t * c[0] + t * t * p1[0],
                        u * u * p0[1] + 2 * u * t * c[1] + t * t * p1[1]))
    else:
        c1, c2, p1 = pts
        for i in range(1, FLATNESS + 1):
            t = i / FLATNESS
            u = 1 - t
            out.append((u**3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t**3 * p1[0],
                        u**3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t**3 * p1[1]))
    return out


def _area(poly) -> float:
    s = 0.0
    for i, (x, y) in enumerate(poly):
        x2, y2 = poly[(i + 1) % len(poly)]
        s += x * y2 - x2 * y
    return s / 2


def draw(path: pathops.Path, img: Image.Image, ox: float, oy: float, scale: float,
         fill=INK, hole=(255, 255, 255)) -> None:
    """מצייר את המסלול; החורים נצבעים ברקע, ולכן הקונטור החיצוני קודם."""
    d = ImageDraw.Draw(img)
    polys = [(p, _area(p)) for p in contours(path) if len(p) > 2]
    for poly, area in sorted(polys, key=lambda t: -abs(t[1])):
        pts = [(ox + x * scale, oy - y * scale) for x, y in poly]
        d.polygon(pts, fill=fill if area > 0 else hole)


def compare(pairs: list[tuple[str, pathops.Path, pathops.Path]], out: Path,
            scale: float = 0.42, zoom: tuple | None = None) -> Path:
    """שלוש עמודות לכל אות: לפני, אחרי, ושתיהן זו על גבי זו.

    [zoom] הוא ``(x0, y0, x1, y1)`` ביחידות em — הפריט מוצג מוגדל לאזור הזה.
    """
    box = zoom or (0, -120, 760, 820)
    w = (box[2] - box[0]) * scale
    h = (box[3] - box[1]) * scale
    pad, head = 18, 34
    img = Image.new("RGB", (int(3 * w + 4 * pad), int(len(pairs) * (h + pad) + head + pad)), "white")
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype("arial.ttf", 16)

    for i, name in enumerate(("לפני", "אחרי", "השוואה")):
        d.text((pad + (2 - i) * (w + pad) + w / 2, 8), name, font=font,
               fill=(BEFORE, AFTER, (90, 90, 90))[i], anchor="mt")

    for row, (label, before, after) in enumerate(pairs):
        top = head + pad + row * (h + pad)
        for col, layers in enumerate((
            [(before, INK)], [(after, INK)],
            [(before, BEFORE), (after, AFTER)],
        )):
            # כל תא מצויר לתמונה משלו, אחרת אות גדולה גולשת אל התא הסמוך.
            cell = Image.new("RGB", (int(w), int(h)), "white")
            for path, color in layers:
                layer = Image.new("RGB", cell.size, "white")
                draw(path, layer, -box[0] * scale, box[3] * scale, scale, fill=color)
                alpha = layer.convert("L").point(
                    lambda v: (255 if col < 2 else 150) if v < 250 else 0)
                cell.paste(layer, (0, 0), alpha)
            x = int(pad + (2 - col) * (w + pad))
            img.paste(cell, (x, int(top)))
            d.rectangle([x, top, x + w, top + h], outline=(232, 232, 232))
        d.text((pad + 3 * (w + pad) - 4, top + 4), label, font=font,
               fill=(150, 150, 150), anchor="rt")

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


def sheet(rows: list[tuple[str, pathops.Path, pathops.Path]], out: Path,
          cols: int = 6, scale: float = 0.19, box=(-30, -440, 830, 1090)) -> Path:
    """רשת של כל האותיות, ה'לפני' באפור מאחורי ה'אחרי' — דף הכרעה אחד."""
    w, h = (box[2] - box[0]) * scale, (box[3] - box[1]) * scale
    pad, head = 10, 40
    img = Image.new("RGB", (int(cols * (w + pad) + pad),
                            int(((len(rows) + cols - 1) // cols) * (h + pad) + head + pad)),
                    "white")
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype("arial.ttf", 15)
    d.text((img.width // 2, 12), "אפור = לפני   ·   שחור = אחרי", font=font,
           fill=(120, 120, 120), anchor="mt", direction="rtl", language="he")

    for i, (label, before, after) in enumerate(rows):
        col, row = i % cols, i // cols
        x = int(pad + (cols - 1 - col) * (w + pad))
        y = int(head + pad + row * (h + pad))
        cell = Image.new("RGB", (int(w), int(h)), "white")
        for path, color in ((before, (192, 192, 192)), (after, INK)):
            layer = Image.new("RGB", cell.size, "white")
            draw(path, layer, -box[0] * scale, box[3] * scale, scale, fill=color)
            cell.paste(layer, (0, 0),
                       layer.convert("L").point(lambda v: 255 if v < 250 else 0))
        img.paste(cell, (x, y))
        d.rectangle([x, y, x + w, y + h], outline=(234, 234, 234))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out
