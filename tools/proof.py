"""דף הוכחה: כל הגליפים של כל אחד מן הקבצים הבנויים, לעין אנושית."""

from __future__ import annotations

import sys
from pathlib import Path

import pathops
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import fontinfo
import raster
from fontinfo import MASTERS

BOX = (-40, -460, 840, 1110)
SCALE = 0.13
COLS = 12


def _path(font: TTFont, name: str) -> pathops.Path:
    path = pathops.Path()
    font.getGlyphSet()[name].draw(path.getPen())
    return path


def sheet(font_path: Path, out: Path) -> Path:
    font = TTFont(font_path)
    cmap = font.getBestCmap()
    codes = [ord(c) for c in fontinfo.LETTERS] + [fontinfo.NUN_HAFUKHA]
    codes += [fontinfo.pua_code(c, s) for c in fontinfo.WIDE_LETTERS
              for s in range(len(fontinfo.WIDE_STEPS))]
    names = [cmap[c] for c in codes if c in cmap]

    w, h = (BOX[2] - BOX[0]) * SCALE, (BOX[3] - BOX[1]) * SCALE
    pad, head = 6, 34
    rows = (len(names) + COLS - 1) // COLS
    img = Image.new("RGB", (int(COLS * (w + pad) + pad), int(rows * (h + pad) + head + pad)), "white")
    draw = ImageDraw.Draw(img)
    label = ImageFont.truetype("arial.ttf", 15)
    draw.text((img.width // 2, 10), f"{font_path.stem} · {fontinfo.VERSION}",
              font=label, fill=(90, 90, 90), anchor="mt")

    for i, name in enumerate(names):
        col, row = i % COLS, i // COLS
        x = int(pad + (COLS - 1 - col) * (w + pad))
        y = int(head + pad + row * (h + pad))
        cell = Image.new("RGB", (int(w), int(h)), "white")
        raster.draw(_path(font, name), cell, -BOX[0] * SCALE, BOX[3] * SCALE, SCALE)
        img.paste(cell, (x, y))
        draw.rectangle([x, y, x + w, y + h], outline=(235, 235, 235))

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    built = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "out"
    target = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "qa"
    for master in MASTERS:
        print(sheet(built / master.file_name, target / f"{master.source}.png"))
