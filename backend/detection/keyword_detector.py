import re

from .models import Detection

DEFAULT_KEYWORDS = [
    "confidential",
    "internal use only",
    "do not distribute",
    "proprietary",
    "trade secret",
]


def detect(text: str, keywords: list[str] | None = None) -> list[Detection]:
    keywords = DEFAULT_KEYWORDS if keywords is None else keywords
    found = []
    for kw in keywords:
        pattern = re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
        for m in pattern.finditer(text):
            found.append(
                Detection("keyword", "confidential_keyword", 0.40, m.span(), 1)
            )
    return found
