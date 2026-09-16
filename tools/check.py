"""בדיקות תקינות על הגופנים הבנויים — מה שחייב להתקיים בכל בנייה."""

from __future__ import annotations

import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import fontinfo
from fontinfo import MASTERS


def check(path: Path, master) -> list[str]:
    font = TTFont(path)
    cmap = font.getBestCmap()
    bad = []

    for letter in fontinfo.LETTERS:
        if ord(letter) not in cmap:
            bad.append(f"אות חסרה: {letter}")
    if fontinfo.NUN_HAFUKHA not in cmap:
        bad.append("נו\"ן הפוכה חסרה")

    for letter in fontinfo.WIDE_LETTERS:
        widths = []
        for step in range(len(fontinfo.WIDE_STEPS)):
            code = fontinfo.pua_code(letter, step)
            if code not in cmap:
                bad.append(f"מדרגה חסרה: {letter} {step}")
                break
            widths.append(font["hmtx"][cmap[code]][0])
        else:
            base = font["hmtx"][cmap[ord(letter)]][0]
            if widths != sorted(widths) or widths[0] <= base:
                bad.append(f"מדרגות {letter} אינן עולות: {base} -> {widths}")

    # הניקוד נשאר מחוץ לגופן הסת"ם דווקא, כדי שהחלפת גופן אוטומטית תפעל.
    pointed = any(0x0591 <= code <= 0x05C7 and code != fontinfo.NUN_HAFUKHA for code in cmap)
    if pointed != ("Nikud" in master.family):
        bad.append("כיסוי הניקוד אינו תואם למשפחה")

    os2 = font["OS/2"]
    glyph_set = font.getGlyphSet()
    top, bottom = 0, 0
    for name in font.getGlyphOrder():
        pen = BoundsPen(glyph_set)
        glyph_set[name].draw(pen)
        if pen.bounds:
            top, bottom = max(top, pen.bounds[3]), min(bottom, pen.bounds[1])
    if top > os2.usWinAscent:
        bad.append(f"גליף חורג מתיבת החיתוך למעלה: {top} > {os2.usWinAscent}")
    if -bottom > os2.usWinDescent:
        bad.append(f"גליף חורג מתיבת החיתוך למטה: {bottom} < -{os2.usWinDescent}")

    names = {n.nameID: n.toUnicode() for n in font["name"].names if n.platformID == 3}
    if names.get(5) != f"Version {fontinfo.VERSION}":
        bad.append(f"גרסה בשם אינה תואמת ל-VERSION: {names.get(5)}")
    for nid, label in ((0, "זכויות יוצרים"), (13, "רישיון"), (14, "כתובת הרישיון")):
        if not names.get(nid):
            bad.append(f"חסר {label} בטבלת השמות")
    if names.get(1) != master.family or names.get(6) != master.ps_name:
        bad.append("שמות המשפחה אינם תואמים")
    return bad


def metric_compatibility(paths: dict[str, Path]) -> list[str]:
    """כל ארבעת הקבצים חייבים אותם רוחבי גליף: הטורים בתיקון קוראים מיושרים
    זה מול זה, והחלפת משקל או משפחה אסור שתזיז אף שורה."""
    tables = {name: TTFont(p) for name, p in paths.items()}
    reference = next(iter(tables))
    base = tables[reference]
    bad = []
    for name, font in tables.items():
        if name == reference:
            continue
        shared = set(base.getBestCmap()) & set(font.getBestCmap())
        for code in sorted(shared):
            a = base["hmtx"][base.getBestCmap()[code]][0]
            b = font["hmtx"][font.getBestCmap()[code]][0]
            if a != b:
                bad.append(f"רוחב U+{code:04X} שונה בין {reference} ל-{name}: {a} != {b}")
                break
    return bad


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "out"
    failed = False
    paths = {}
    for master in MASTERS:
        path = out / master.file_name
        if not path.exists():
            print(f"חסר: {path.name}")
            failed = True
            continue
        paths[master.file_name] = path
        bad = check(path, master)
        print(f"{path.name}: " + ("תקין" if not bad else "; ".join(bad)))
        failed |= bool(bad)
    for problem in metric_compatibility(paths):
        print(problem)
        failed = True
    sys.exit(1 if failed else 0)
