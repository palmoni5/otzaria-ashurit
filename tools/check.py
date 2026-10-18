"""בדיקות תקינות על הגופנים הבנויים — מה שחייב להתקיים בכל בנייה."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

from fontTools.misc.psCharStrings import T2WidthExtractor
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

    vav = cmap[0x05D5]
    for code in fontinfo.VAV_KETIA_CODES:
        if code not in cmap:
            bad.append(f"חלופת וי״ו קטיעא חסרה: U+{code:04X}")
            continue
        name = cmap[code]
        pen = BoundsPen(font.getGlyphSet())
        font.getGlyphSet()[name].draw(pen)
        if not pen.bounds:
            bad.append(f"חלופת וי״ו קטיעא ריקה: U+{code:04X}")
        if font["hmtx"][name][0] != font["hmtx"][vav][0]:
            bad.append(f"חלופת וי״ו קטיעא משנה את רוחב התיבה: U+{code:04X}")
        if "GDEF" in font and font["GDEF"].table.GlyphClassDef.classDefs.get(name) != 1:
            bad.append(f"חלופת וי״ו קטיעא אינה מסווגת כאות בסיס: U+{code:04X}")

    bad += _ketia_positioning(font)

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

    # הניקוד נשאר מחוץ לגופן הסת"ם דווקא, כדי שהחלפת גופן אוטומטית תפעל;
    # ובמשפחת הניקוד הכיסוי חייב להיות מלא, שאם ייפול תו אחד הוא יילקח
    # מגופן אחר ויבלוט באמצע המילה.
    pointed = {code for code in cmap if 0x0591 <= code <= 0x05C7
               and code != fontinfo.NUN_HAFUKHA}
    if "Nikud" in master.family:
        missing = set(fontinfo.MARKS) - pointed
        if missing:
            bad.append("תווי ניקוד חסרים: "
                       + ", ".join(f"U+{code:04X}" for code in sorted(missing)))
    elif pointed:
        bad.append("גופן הסת\"ם ממפה ניקוד, ולכן נפילת גופן לא תפעל")

    bad += _charstring_widths(font)

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


def _ketia_positioning(font: TTFont) -> list[str]:
    if "GPOS" not in font:
        return []
    cmap = font.getBestCmap()
    vav = cmap[0x05D5]
    alternates = {cmap[c] for c in fontinfo.VAV_KETIA_CODES if c in cmap}
    for lookup in font["GPOS"].table.LookupList.Lookup:
        for table in lookup.SubTable:
            coverage = getattr(table, "BaseCoverage", None)
            if coverage and vav in coverage.glyphs:
                records = dict(zip(coverage.glyphs, table.BaseArray.BaseRecord))
                if not alternates <= records.keys() or any(records[n] != records[vav] for n in alternates):
                    return ["עוגני הניקוד של חלופת וי״ו קטיעא שונים מעוגני וי״ו"]
            if lookup.LookupType in (7, 8) and table.Format == 3:
                for key in ("Coverage", "BacktrackCoverage", "InputCoverage", "LookAheadCoverage"):
                    for context in getattr(table, key, []):
                        if vav in context.glyphs and not alternates <= set(context.glyphs):
                            return ["חלופת וי״ו קטיעא חסרה בכלל מיקום הקשרי"]
    return []


def _charstring_widths(font: TTFont) -> list[str]:
    """הרוחב שבראש ה-charstring מול hmtx.

    ב-CFF הרוחב נכתב כהפרש מ-``nominalWidthX``, ואילו fontTools ו-hmtx
    מחזירים את הרוחב המוחלט. אי-התאמה כאן אינה נראית בשום קריאה רגילה,
    אבל Skia קוראת את הרוחב מן ה-CFF והטקסט יוצא מרוח.
    """
    cff = font["CFF "].cff
    top = cff[cff.fontNames[0]]
    private = top.Private
    nominal = getattr(private, "nominalWidthX", 0)
    default = getattr(private, "defaultWidthX", 0)
    bad = []
    for name in font.getGlyphOrder():
        charstring = top.CharStrings[name]
        extractor = T2WidthExtractor([], charstring.globalSubrs, nominal, default)
        extractor.execute(charstring)
        if extractor.width != font["hmtx"][name][0]:
            bad.append(f"רוחב ב-CFF של {name}: {extractor.width} != {font['hmtx'][name][0]}")
    return bad[:5]


def package_contract(built: Path) -> list[str]:
    """חוזה חבילת ה-Flutter. שם החבילה, נתיב ה-path ושמות הקבצים הם ממשק
    שאוצריא נשענת עליו; שינוי בהם שובר את הבנייה שלה בלי שום אזהרה."""
    import package as packaging

    root = Path(__file__).resolve().parents[1]
    pubspec = root / "package" / "pubspec.yaml"
    lib = root / "package" / "lib"
    bad = []
    if not pubspec.exists():
        return ["package/pubspec.yaml חסר"]

    text = pubspec.read_text(encoding="utf-8")
    name = re.search(r"^name:\s*(\S+)$", text, re.M)
    version = re.search(r"^version:\s*(\S+)$", text, re.M)
    if not name or name.group(1) != packaging.NAME:
        bad.append(f"שם החבילה אינו {packaging.NAME}")
    expected = packaging.dart_version(fontinfo.VERSION)
    if not version or version.group(1) != expected:
        bad.append(f"גרסת החבילה אינה נגזרת מ-VERSION: ציפינו ל-{expected}")
    if not (root / "package" / "LICENSE").exists():
        bad.append("package/LICENSE חסר")

    for master in MASTERS:
        shipped = lib / master.file_name
        if not shipped.exists():
            bad.append(f"חסר בחבילה: lib/{master.file_name}")
        elif hashlib.sha256(shipped.read_bytes()).digest() !=                 hashlib.sha256((built / master.file_name).read_bytes()).digest():
            bad.append(f"הקובץ שבחבילה אינו הבנייה הנוכחית: {master.file_name}")
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
    for problem in package_contract(out):
        print(problem)
        failed = True
    for problem in metric_compatibility(paths):
        print(problem)
        failed = True
    sys.exit(1 if failed else 0)
