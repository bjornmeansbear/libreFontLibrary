"""Which licenses let this repo redistribute a font, and how to recognise one from its text.

Shared by verify.py (reading a license upstream) and fetch.py (reading the
license that ships inside a download).
"""

REDISTRIBUTABLE = {"OFL-1.1", "Apache-2.0", "UFL-1.0", "Bitstream-Vera", "LAL-1.3",
                   "MIT", "CC-BY-SA-4.0", "CC0-1.0", "GPL-2.0", "GPL-3.0",
                   "BSD-2-Clause", "BSD-3-Clause"}


def classify(text):
    t = text.upper()
    if "SIL OPEN FONT LICENSE" in t and "1.1" in t: return "OFL-1.1"
    if "APACHE LICENSE" in t and "2.0" in t: return "Apache-2.0"
    if "UBUNTU FONT LICENCE" in t: return "UFL-1.0"
    if "BITSTREAM VERA" in t: return "Bitstream-Vera"
    if "LICENCE ART LIBRE" in t or "FREE ART LICENSE" in t: return "LAL-1.3"
    if "GNU GENERAL PUBLIC LICENSE" in t: return "GPL-3.0" if "VERSION 3" in t else "GPL-2.0"
    if "PERMISSION IS HEREBY GRANTED, FREE OF CHARGE" in t: return "MIT"
    if "REDISTRIBUTION AND USE IN SOURCE AND BINARY FORMS" in t:
        return "BSD-3-Clause" if "NEITHER THE NAME" in t else "BSD-2-Clause"
    return None
