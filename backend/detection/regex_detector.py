import re

from .models import Detection

# (detector name, category, confidence, compiled pattern)
_TIER0_PATTERNS = [
    ("aws_access_key", "secret", 0.95, re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    (
        "pem_private_key",
        "secret",
        0.99,
        re.compile(
            r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"
        ),
    ),
    (
        "db_connection_string",
        "secret",
        0.90,
        re.compile(
            r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|mssql)://"
            r"[^\s:/@]+:[^\s@]+@\S+"
        ),
    ),
]

_TIER1_PATTERNS = [
    (
        "email",
        "email",
        0.50,
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
    (
        "phone_in",
        "phone",
        0.40,
        re.compile(r"(?<!\d)(?<!\d[ -])(?:\+91[ -]?)?[6-9]\d{4}[ -]?\d{5}(?![ -]?\d)"),
    ),
]


def _scan(text: str, patterns: list, tier: int) -> list[Detection]:
    found = []
    for name, category, confidence, pattern in patterns:
        for m in pattern.finditer(text):
            found.append(Detection(name, category, confidence, m.span(), tier))
    return found


def detect_tier0(text: str) -> list[Detection]:
    return _scan(text, _TIER0_PATTERNS, tier=0)


def detect_tier1(text: str) -> list[Detection]:
    return _scan(text, _TIER1_PATTERNS, tier=1)
