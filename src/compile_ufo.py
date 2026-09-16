"""הרכבת גופן OTF מקובץ מקור UFO — בלי שום גופן מוכן כקלט.

כאן נבנה שלד הגופן בלבד: מתארים, מידות ושמות. הליטושים והגליפים הנגזרים
נעשים אחר כך ב-[build], על גבי השלד הזה.
"""

from __future__ import annotations

import calendar
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.pointPen import PointToSegmentPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.misc.timeTools import timestampSinceEpoch
from fontTools.ttLib import TTFont
from fontTools.ufoLib import UFOReader

# שדות ה-Private של CFF, כפי שהם שמורים ב-fontinfo של ה-UFO.
PRIVATE = [
    ("BlueValues", "postscriptBlueValues"), ("OtherBlues", "postscriptOtherBlues"),
    ("FamilyBlues", "postscriptFamilyBlues"), ("FamilyOtherBlues", "postscriptFamilyOtherBlues"),
    ("StemSnapH", "postscriptStemSnapH"), ("StemSnapV", "postscriptStemSnapV"),
    ("StdHW", "postscriptStdHW"), ("StdVW", "postscriptStdVW"),
    ("BlueFuzz", "postscriptBlueFuzz"), ("BlueScale", "postscriptBlueScale"),
    ("BlueShift", "postscriptBlueShift"), ("ForceBold", "postscriptForceBold"),
    ("nominalWidthX", "postscriptNominalWidthX"), ("defaultWidthX", "postscriptDefaultWidthX"),
]

OS2 = [
    ("usWidthClass", "openTypeOS2WidthClass"), ("sTypoAscender", "openTypeOS2TypoAscender"),
    ("sTypoDescender", "openTypeOS2TypoDescender"), ("sTypoLineGap", "openTypeOS2TypoLineGap"),
    ("usWinAscent", "openTypeOS2WinAscent"), ("usWinDescent", "openTypeOS2WinDescent"),
    ("ySubscriptXSize", "openTypeOS2SubscriptXSize"), ("ySubscriptYSize", "openTypeOS2SubscriptYSize"),
    ("ySubscriptXOffset", "openTypeOS2SubscriptXOffset"), ("ySubscriptYOffset", "openTypeOS2SubscriptYOffset"),
    ("ySuperscriptXSize", "openTypeOS2SuperscriptXSize"), ("ySuperscriptYSize", "openTypeOS2SuperscriptYSize"),
    ("ySuperscriptXOffset", "openTypeOS2SuperscriptXOffset"),
    ("ySuperscriptYOffset", "openTypeOS2SuperscriptYOffset"),
    ("yStrikeoutSize", "openTypeOS2StrikeoutSize"), ("yStrikeoutPosition", "openTypeOS2StrikeoutPosition"),
    ("sxHeight", "xHeight"), ("sCapHeight", "capHeight"),
]


class _Glyph:
    def __init__(self):
        self.width = 0
        self.unicodes = []


def _bits(values: list[int], count: int) -> list[int]:
    """מחזיר את ארבע/שתי מילות ה-32 ביט של רשימת מספרי הסיביות."""
    mask = 0
    for i in values:
        mask |= 1 << i
    return [(mask >> (32 * i)) & 0xFFFFFFFF for i in range(count)]


def load(ufo: Path):
    """(מידע הגופן, סדר הגליפים, {שם: (מסלול, רוחב, קודים)})."""
    reader = UFOReader(ufo)
    info = SimpleNamespace()
    reader.readInfo(info)
    lib = reader.readLib()
    glyph_set = reader.getGlyphSet()

    glyphs = {}
    for name in glyph_set.keys():
        glyph = _Glyph()
        pen = RecordingPen()
        glyph_set.readGlyph(name, glyph, PointToSegmentPen(pen))
        glyphs[name] = (pen.value, glyph.width, glyph.unicodes)

    order = [n for n in lib.get("public.glyphOrder", []) if n in glyphs]
    order += [n for n in sorted(glyphs) if n not in order]
    return info, order, glyphs


def build(ufo: Path, ps_name: str, layout: Path | None = None) -> TTFont:
    """מרכיב TTFont שלם מן ה-UFO, ומצרף אליו את טבלאות הפריסה אם ישנן."""
    info, order, glyphs = load(ufo)
    fb = FontBuilder(int(info.unitsPerEm), isTTF=False)
    fb.setupGlyphOrder(order)

    cmap = {}
    for name, (_, _, codes) in glyphs.items():
        for code in codes:
            cmap[code] = name
    fb.setupCharacterMap(cmap)

    private = {}
    for key, source in PRIVATE:
        value = getattr(info, source, None)
        if value is not None:
            private[key] = value

    charstrings = {}
    for name in order:
        commands, width, _ = glyphs[name]
        # roundTolerance=0: מתארי המקור נושאים שברים, ועיגול לשלמים היה משנה אותם.
        pen = T2CharStringPen(width, None, roundTolerance=0)
        for verb, points in commands:
            getattr(pen, verb)(*points)
        charstrings[name] = pen.getCharString()

    fb.setupCFF(ps_name, {"FullName": ps_name}, charstrings, private)
    fb.setupHorizontalMetrics({n: (glyphs[n][1], 0) for n in order})
    fb.setupHorizontalHeader(ascent=int(info.openTypeHheaAscender),
                             descent=int(info.openTypeHheaDescender),
                             lineGap=int(info.openTypeHheaLineGap))
    fb.setupNameTable({"familyName": "X", "styleName": "Regular"})
    fb.setupOS2()
    os2 = fb.font["OS/2"]
    for field, source in OS2:
        value = getattr(info, source, None)
        if value is not None:
            setattr(os2, field, int(value))
    os2.achVendID = getattr(info, "openTypeOS2VendorID", "NONE")
    panose = getattr(info, "openTypeOS2Panose", None)
    if panose:
        for field, value in zip(
            ("bFamilyType", "bSerifStyle", "bWeight", "bProportion", "bContrast",
             "bStrokeVariation", "bArmStyle", "bLetterForm", "bMidline", "bXHeight"), panose):
            setattr(os2.panose, field, int(value))
    family = getattr(info, "openTypeOS2FamilyClass", None)
    if family:
        os2.sFamilyClass = (int(family[0]) << 8) | int(family[1])
    unicode_ranges = _bits(getattr(info, "openTypeOS2UnicodeRanges", []), 4)
    for i, value in enumerate(unicode_ranges, start=1):
        setattr(os2, f"ulUnicodeRange{i}", value)
    for i, value in enumerate(_bits(getattr(info, "openTypeOS2CodePageRanges", []), 2), start=1):
        setattr(os2, f"ulCodePageRange{i}", value)

    fb.setupPost(underlineThickness=int(info.postscriptUnderlineThickness),
                 underlinePosition=int(info.postscriptUnderlinePosition),
                 italicAngle=float(info.italicAngle or 0),
                 isFixedPitch=int(bool(getattr(info, "postscriptIsFixedPitch", False))))
    head = fb.font["head"]
    head.lowestRecPPEM = int(getattr(info, "openTypeHeadLowestRecPPEM", 3))
    # חותמת זמן קבועה מן המקור: שתי בניות של אותו קומיט חייבות להוציא
    # קובץ זהה בתים, אחרת אי אפשר לאמת רילייס.
    created = getattr(info, "openTypeHeadCreated", None)
    if created:
        stamp = calendar.timegm(datetime.strptime(created, "%Y/%m/%d %H:%M:%S").timetuple())
        head.created = head.modified = timestampSinceEpoch(stamp)

    if layout is not None:
        fb.font.importXML(str(layout))
    return fb.font
