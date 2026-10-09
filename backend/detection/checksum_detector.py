"""Pattern + checksum detectors. A shape match alone is NOT a detection:
it must also pass its checksum/structure rule, which is what keeps phone
numbers and order IDs from being flagged as cards or Aadhaar numbers."""

import re

from .models import Detection

# ---------- Luhn (payment cards) ----------


def luhn_valid(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if not digits:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


# ---------- Verhoeff (Aadhaar) ----------

_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]
_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def verhoeff_valid(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if not digits:
        return False
    c = 0
    for i, d in enumerate(reversed(digits)):
        c = _D[c][_P[i % 8][d]]
    return c == 0


def verhoeff_check_digit(payload: str) -> str:
    """Used by tests to build valid synthetic Aadhaar-style numbers."""
    c = 0
    for i, ch in enumerate(reversed(payload)):
        c = _D[c][_P[(i + 1) % 8][int(ch)]]
    return str(_INV[c])


# ---------- Patterns ----------

# 13-19 digits, optionally separated by single spaces or dashes
_CARD = re.compile(r"(?<![\d-])\d(?:[ -]?\d){12,18}(?![\d-])")
# 12 digits, first digit 2-9, optionally grouped 4-4-4; must not be part of a longer digit run
_AADHAAR = re.compile(r"(?<!\d)(?<!\d[ -])[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}(?![ -]?\d)")
# 5 letters, 4 digits, 1 letter; 4th letter encodes holder type
_PAN = re.compile(r"\b[A-Z]{3}[ABCFGHLJPT][A-Z]\d{4}[A-Z]\b")


def detect(text: str) -> list[Detection]:
    """All checksum-validated detectors. These are Tier 0 (high certainty)."""
    found: list[Detection] = []

    for m in _CARD.finditer(text):
        digits = re.sub(r"\D", "", m.group())
        # first digit 3-6 covers Amex, Visa, Mastercard, Discover/RuPay
        if 13 <= len(digits) <= 19 and digits[0] in "3456" and luhn_valid(digits):
            found.append(Detection("luhn", "credit_card", 0.95, m.span(), 0))

    for m in _AADHAAR.finditer(text):
        if verhoeff_valid(m.group()):
            found.append(Detection("verhoeff", "aadhaar", 0.95, m.span(), 0))

    for m in _PAN.finditer(text):
        found.append(Detection("pan_structure", "pan", 0.85, m.span(), 0))

    return found
