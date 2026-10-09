import math
import re
from collections import Counter

from .models import Detection

# Placeholders only. Tune these on YOUR data (see step 8).
DEFAULT_MIN_LENGTH = 20
DEFAULT_THRESHOLD = 4.5

_TOKEN = re.compile(r"[A-Za-z0-9+/=_\-]+")


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in Counter(s).values())


def detect(
    text: str,
    min_length: int = DEFAULT_MIN_LENGTH,
    threshold: float = DEFAULT_THRESHOLD,
) -> list[Detection]:
    found = []
    for m in _TOKEN.finditer(text):
        token = m.group()
        if len(token) < min_length:
            continue
        ent = shannon_entropy(token)
        if ent >= threshold:
            confidence = min(0.9, 0.5 + 0.2 * (ent - threshold))
            found.append(
                Detection("entropy", "secret", round(confidence, 2), m.span(), 1)
            )
    return found
