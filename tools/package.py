"""הרכבת חבילת ה-Flutter שבתיקיית package/.

קובצי הגופן מקומטים לגיט תחת ``package/lib/``, שכן תלות git מושכת את
המאגר ולא את נכסי הרילייס. ``VERSION`` נשאר מקור הגרסה היחיד, וגרסת
החבילה נגזרת ממנו.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fontinfo
from fontinfo import MASTERS

PACKAGE = ROOT / "package"
NAME = "otzaria_ashurit"

PUBSPEC = """# נוצר על ידי tools/package.py — אין לערוך ביד. מקור הגרסה הוא VERSION.
name: {name}
description: >-
  Otzaria Ashurit — גופן כתב אשורית לטור הסת"ם ולטור הניקוד של תיקון
  הקוראים באוצריא, בשתי משפחות ובשני משקלים.
version: {version}
homepage: {homepage}
publish_to: "none"

environment:
  sdk: ">=3.0.0 <4.0.0"

dependencies:
  flutter:
    sdk: flutter
"""

LIBRARY = '''/// שמות המשפחות של Otzaria Ashurit.
///
/// האפליקציה הצורכת מכריזה על הגופנים ב-pubspec שלה בנתיב
/// `packages/{name}/<שם הקובץ>`, ומשתמשת בקבועים שכאן כדי שלא
/// ייכתבו שמות המשפחות כמחרוזות חופשיות.
library;

/// משפחת טור הסת"ם — בלי ניקוד, כדי שנפילת גופן תפעל על תו מנוקד.
const String ashuritFamily = '{stam}';

/// משפחת טור הניקוד — עם ניקוד, טעמים וטבלאות המיקום שלהם.
const String ashuritNikudFamily = '{nikud}';
'''


def dart_version(version: str) -> str:
    """1.002 -> 1.0.2. שלוש הספרות שאחרי הנקודה הן המשנֶה של הגופן."""
    major, _, minor = version.partition(".")
    return f"{int(major)}.0.{int(minor)}"


def build(built: Path) -> list[Path]:
    lib = PACKAGE / "lib"
    lib.mkdir(parents=True, exist_ok=True)
    written = []

    for master in MASTERS:
        source = built / master.file_name
        if not source.exists():
            raise SystemExit(f"חסר קובץ בנוי: {source}")
        target = lib / master.file_name
        shutil.copyfile(source, target)
        written.append(target)

    families = {m.family for m in MASTERS}
    stam = min(families, key=len)
    nikud = max(families, key=len)
    (lib / f"{NAME}.dart").write_text(
        LIBRARY.format(name=NAME, stam=stam, nikud=nikud), encoding="utf-8")
    written.append(lib / f"{NAME}.dart")

    (PACKAGE / "pubspec.yaml").write_text(
        PUBSPEC.format(name=NAME, version=dart_version(fontinfo.VERSION),
                       homepage=fontinfo.VENDOR_URL), encoding="utf-8")
    written.append(PACKAGE / "pubspec.yaml")

    shutil.copyfile(ROOT / "LICENSE", PACKAGE / "LICENSE")
    written.append(PACKAGE / "LICENSE")
    return written


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "out"
    for path in build(out):
        print(path.relative_to(ROOT))
