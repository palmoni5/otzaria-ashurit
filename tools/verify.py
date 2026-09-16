"""אימות: הגופן הבנוי מול קובץ ייחוס — מתאר, מידות, מיפוי ופריסה.

השוואה גליף-גליף ולא השוואת בתים: סדר הסֶבְּרוּטינים ב-CFF תלוי בסביבה,
ואילו הצורה עצמה חייבת לצאת זהה בכל מכונה.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

METRICS = [
    ("head", ["unitsPerEm"]),
    ("hhea", ["ascent", "descent", "lineGap"]),
    ("OS/2", ["usWinAscent", "usWinDescent", "sTypoAscender", "sTypoDescender",
              "sTypoLineGap", "usWeightClass", "fsSelection"]),
]


def _outline(font: TTFont, name: str):
    """המתאר, בלי קו הסגירה המפורש — ``closePath`` מכיל אותו ממילא, ויש
    גופנים שכותבים אותו ויש שאינם."""
    pen = RecordingPen()
    font.getGlyphSet()[name].draw(pen)
    out, start = [], None
    for verb, points in pen.value:
        if verb == "moveTo":
            start = points[0]
        elif verb == "closePath" and out and out[-1] == ("lineTo", (start,)):
            out.pop()
        out.append((verb, points))
    return out


def compare(built: Path, reference: Path) -> list[str]:
    a, b = TTFont(reference), TTFont(built)
    bad = []
    if a.getGlyphOrder() != b.getGlyphOrder():
        bad.append("סדר הגליפים")
    if a.getBestCmap() != b.getBestCmap():
        bad.append("מיפוי התווים")
    for name in a.getGlyphOrder():
        if name not in b.getGlyphOrder():
            bad.append(f"גליף חסר: {name}")
        elif a["hmtx"][name][0] != b["hmtx"][name][0]:
            bad.append(f"רוחב {name}: {a['hmtx'][name][0]} != {b['hmtx'][name][0]}")
        elif _outline(a, name) != _outline(b, name):
            bad.append(f"מתאר {name}")
    for table, fields in METRICS:
        for field in fields:
            if getattr(a[table], field) != getattr(b[table], field):
                bad.append(f"{table}.{field}: {getattr(a[table], field)} != {getattr(b[table], field)}")
    for table in ("GSUB", "GPOS", "GDEF"):
        if (table in a) != (table in b):
            bad.append(f"טבלת {table}")
        elif table in a and a[table].compile(a) != b[table].compile(b):
            bad.append(f"{table} שונה")
    return bad


if __name__ == "__main__":
    built_dir, reference_dir = Path(sys.argv[1]), Path(sys.argv[2])
    failed = False
    for reference in sorted(reference_dir.glob("*.otf")):
        built = built_dir / reference.name
        if not built.exists():
            print(f"חסר: {built.name}")
            failed = True
            continue
        bad = compare(built, reference)
        print(f"{reference.name}: " + ("תקין" if not bad else "; ".join(bad[:10])))
        failed |= bool(bad)
    sys.exit(1 if failed else 0)
