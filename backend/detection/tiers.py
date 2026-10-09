from . import checksum_detector, entropy_detector, keyword_detector, regex_detector
from .models import Detection


def run_tier0(text: str) -> list[Detection]:
    """High-certainty detectors only. Pure function: string in, detections out."""
    results = regex_detector.detect_tier0(text) + checksum_detector.detect(text)
    return sorted(results, key=lambda d: d.span)


def run_tier1(
    text: str,
    *,
    keywords: list[str] | None = None,
    entropy_min_length: int = entropy_detector.DEFAULT_MIN_LENGTH,
    entropy_threshold: float = entropy_detector.DEFAULT_THRESHOLD,
) -> list[Detection]:
    """Heuristic detectors only. Pure function: string in, detections out."""
    results = (
        regex_detector.detect_tier1(text)
        + entropy_detector.detect(text, entropy_min_length, entropy_threshold)
        + keyword_detector.detect(text, keywords)
    )
    return sorted(results, key=lambda d: d.span)


def tier1_options(cfg: dict) -> dict:
    """Turn the `detection:` section of config.yaml into run_tier1 keyword args."""
    det = cfg.get("detection", {})
    ent = det.get("entropy", {})
    opts: dict = {}
    if det.get("keywords") is not None:
        opts["keywords"] = det["keywords"]
    if "min_length" in ent:
        opts["entropy_min_length"] = ent["min_length"]
    if "threshold" in ent:
        opts["entropy_threshold"] = ent["threshold"]
    return opts
