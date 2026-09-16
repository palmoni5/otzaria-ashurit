"""ייצור טבלת הרוחבים הצפויים לבדיקת המנוע.

הערכים נקראים מ-hmtx של הגופן הבנוי, ולכן הבדיקה ב-Flutter אינה מצהירה
על מספרים קבועים אלא שואלת שאלה אחת: האם Skia מודדת כמו שהגופן מצהיר.
זו בדיקה שאין לה תחליף בצד פייתון — באג ה-575 ב-CFF חמק מכל קריאה
דרך fontTools, שכן hmtx היה תקין.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fontinfo
from fontinfo import MASTERS

OUT = ROOT / "test_consumer" / "test" / "expected.g.dart"

HEADER = """// נוצר על ידי tools/expected_widths.py — אין לערוך ביד.
// הרוחבים נקראים מ-hmtx של הגופן הבנוי, ביחידות em של 1000.

const Map<String, Map<int, double>> expectedWidths = {
"""


def codepoints() -> list[int]:
    out = [ord(c) for c in fontinfo.LETTERS] + [fontinfo.NUN_HAFUKHA]
    out += [fontinfo.pua_code(letter, step)
            for letter in fontinfo.WIDE_LETTERS
            for step in range(len(fontinfo.WIDE_STEPS))]
    return out


def build(built: Path) -> Path:
    lines = [HEADER]
    for master in MASTERS:
        if master.bold:
            continue
        font = TTFont(built / master.file_name)
        cmap = font.getBestCmap()
        lines.append(f"  '{master.family}': {{\n")
        for code in codepoints():
            if code in cmap:
                lines.append(f"    0x{code:04X}: {font['hmtx'][cmap[code]][0]}.0,\n")
        lines.append("  },\n")
    lines.append("};\n")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(lines), encoding="utf-8")
    return OUT


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "out"
    print(build(out).relative_to(ROOT))
