"""בניית משפחות Otzaria Ashurit מקובצי המקור שבמאגר.

כל גליף שבגופן המוגמר מצוי בקובץ המקור כצורתו הסופית; הבנייה מרכיבה אותם
לגופן ומוסיפה את הזהות — שמות, גרסה ורישיון. אין כאן שלב שמשנה צורת אות.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fontTools.ttLib import TTFont

import compile_ufo
import fontinfo
from fontinfo import MASTERS, Master

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources"


def _names(font: TTFont, master: Master) -> None:
    version = fontinfo.VERSION
    names = {
        0: fontinfo.COPYRIGHT,
        1: master.family,
        2: master.style,
        3: f"{master.family} {master.style}; {version}",
        4: master.full_name,
        5: f"Version {version}",
        6: master.ps_name,
        7: fontinfo.TRADEMARK,
        9: fontinfo.DESIGNER,
        11: fontinfo.VENDOR_URL,
        13: fontinfo.LICENSE,
        14: fontinfo.LICENSE_URL,
        16: master.family,
        17: master.style,
    }
    table = font["name"]
    table.names = []
    for nid, value in names.items():
        table.setName(value, nid, 3, 1, 0x409)
    cff = font["CFF "].cff
    cff.fontNames[0] = master.ps_name
    top = cff[master.ps_name]
    top.Copyright = fontinfo.COPYRIGHT
    top.FullName = master.full_name
    top.FamilyName = master.family
    top.Weight = master.style
    top.version = version


def _flags(font: TTFont, master: Master) -> None:
    os2 = font["OS/2"]
    os2.usWeightClass = 700 if master.bold else 400
    os2.fsSelection = (os2.fsSelection & ~0x41) | (0x20 if master.bold else 0x40)
    os2.fsType = fontinfo.FS_TYPE
    os2.usWinAscent = fontinfo.CLIP_ASCENT
    os2.usWinDescent = fontinfo.CLIP_DESCENT
    font["head"].macStyle = 1 if master.bold else 0
    font["head"].fontRevision = float(fontinfo.VERSION)


def build(master: Master, out_dir: Path) -> Path:
    layout = SOURCES / f"{master.source}-layout.ttx"
    font = compile_ufo.build(SOURCES / f"{master.source}.ufo", master.ps_name,
                             layout if layout.exists() else None)
    _names(font, master)
    _flags(font, master)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / master.file_name
    font.save(path)
    return path


def build_all(out_dir: Path) -> list[Path]:
    return [build(master, out_dir) for master in MASTERS]


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "out"
    for path in build_all(target):
        print("נבנה:", path)
