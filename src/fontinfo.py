"""שמות הגופנים, גרסה ורישיון — כל מה שנכתב לטבלאות ואינו צורת אות."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

COPYRIGHT = "Copyright (c) 2026 Otzaria Project. All rights reserved."
TRADEMARK = "Otzaria Ashurit is a trademark of the Otzaria Project."
LICENSE = (
    "Personal Use License. Free for an individual's private, personal and "
    "non-commercial use. Any public, shared or commercial use — including "
    "bundling in or distribution with any product, service, website or "
    "application — requires prior written permission from the copyright "
    "holder. The Otzaria application (otzaria.org) is excepted and may "
    "bundle and embed these fonts. See the LICENSE file in the source "
    "repository."
)
LICENSE_URL = "https://github.com/palmoni5/otzaria-ashurit/blob/main/LICENSE"
DESIGNER = "Otzaria Project"
VENDOR_URL = "https://github.com/palmoni5/otzaria-ashurit"

# 8 = Editable embedding. הגופן נארז בתוך אוצריא ומוטמע בקובצי PDF שהיא
# מייצרת, ולכן הגבלת הטמעה הייתה שוברת את ההדפסה.
FS_TYPE = 8

# תיבת החיתוך. ל' ו-ך' חורגות מן השורה, ובלבד שלא ייחתכו; ריווח השורות
# (hhea) קטן מזה במתכוון, כדי שהחריגה לא תדחק את השורות זו מזו.
CLIP_ASCENT, CLIP_DESCENT = 1090, 450


class Master:
    """קובץ מקור אחד והשמות שהוא מקבל."""

    def __init__(self, source: str, family: str, style: str):
        self.source, self.family, self.style = source, family, style

    @property
    def bold(self) -> bool:
        return self.style == "Bold"

    @property
    def ps_name(self) -> str:
        return f"{self.family.replace(' ', '')}-{self.style}"

    @property
    def full_name(self) -> str:
        return f"{self.family} {self.style}" if self.bold else self.family

    @property
    def file_name(self) -> str:
        return f"{self.source}.otf"


MASTERS = [
    Master("OtzariaAshurit-Regular", "Otzaria Ashurit", "Regular"),
    Master("OtzariaAshurit-Bold", "Otzaria Ashurit", "Bold"),
    Master("OtzariaAshuritNikud-Regular", "Otzaria Ashurit Nikud", "Regular"),
    Master("OtzariaAshuritNikud-Bold", "Otzaria Ashurit Nikud", "Bold"),
]


# --- מפת התווים שהגופן מכסה --------------------------------------------

LETTERS = [chr(c) for c in range(0x05D0, 0x05EB)]
NUN_HAFUKHA = 0x05C6

# האותיות שסופר מרחיב כדי ליישר את הטור. א' אינה בהן: אין בה גזע אנכי אלא
# אלכסון, ומתיחה אופקית משטחת את זוויתו.
WIDE_LETTERS = "הלםרתד"

# מדרגות הרוחב, כשיעור מרוחב הדיו. המנוע בוחר מדרגה לפי השארית בשורה.
WIDE_STEPS = (1.15, 1.3, 1.5, 1.75, 2.0, 2.5)

# כל סימני הניקוד והטעמים שמשפחת הניקוד חייבת לכסות. נו"ן הפוכה יושבת
# בתוך הטווח הזה ואינה סימן, ולכן היא מוצאת ממנו.
MARKS = [c for c in range(0x0591, 0x05C8) if c != NUN_HAFUKHA]

# בלוק PUA לכל אות מתרחבת: E100 + סדר האות * 8 + מספר המדרגה.
PUA_BASE = 0xE100
PUA_STRIDE = 8


def pua_code(letter: str, step: int) -> int:
    return PUA_BASE + WIDE_LETTERS.index(letter) * PUA_STRIDE + step


def wide_name(letter: str, step: int) -> str:
    return f"uni{ord(letter):04X}.w{step}"
