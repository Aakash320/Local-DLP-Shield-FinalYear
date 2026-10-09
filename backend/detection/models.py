from dataclasses import dataclass


@dataclass(frozen=True)
class Detection:
    """One fired detector. Stores WHERE it matched, never the matched text."""

    detector: str  # e.g. "luhn", "aws_access_key"
    category: str  # e.g. "credit_card", "aadhaar", "secret"
    confidence: float  # 0.0-1.0
    span: tuple[int, int]  # (start, end) character offsets in the input text
    tier: int  # 0 or 1
