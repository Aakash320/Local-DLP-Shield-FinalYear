import time

from backend.detection.tiers import run_tier0, run_tier1, tier1_options

SAMPLE = (
    "Hi team, CONFIDENTIAL. Card 4111 1111 1111 1111, aadhaar 2345 6789 0124, "
    "key AKIAIOSFODNN7EXAMPLE, mail priya@example.com, call 9876543210, "
    "secret wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
)


def test_tier0_only_returns_tier0():
    results = run_tier0(SAMPLE)
    assert results and all(d.tier == 0 for d in results)
    assert {d.category for d in results} == {"credit_card", "aadhaar", "secret"}


def test_tier1_only_returns_tier1():
    results = run_tier1(SAMPLE)
    assert results and all(d.tier == 1 for d in results)
    assert {d.category for d in results} == {
        "email",
        "phone",
        "secret",
        "confidential_keyword",
    }


def test_tiers_are_isolated():
    only_tier1_text = "CONFIDENTIAL mail priya@example.com"
    assert run_tier0(only_tier1_text) == []
    assert run_tier1("AKIAIOSFODNN7EXAMPLE 4111111111111111") == []


def test_clean_text_fires_nothing():
    text = "Lunch at 1pm? The quarterly meeting moved to Thursday."
    assert run_tier0(text) == []
    assert run_tier1(text) == []


def test_pure_and_deterministic():
    assert run_tier0(SAMPLE) == run_tier0(SAMPLE)
    assert run_tier1(SAMPLE) == run_tier1(SAMPLE)


def test_fast_on_large_input():
    text = SAMPLE * 200  # ~50 KB
    start = time.perf_counter()
    run_tier0(text)
    run_tier1(text)
    assert time.perf_counter() - start < 0.5


def test_tier1_options_from_config():
    cfg = {
        "detection": {
            "keywords": ["project falcon"],
            "entropy": {"threshold": 3.2, "min_length": 16},
        }
    }
    assert tier1_options(cfg) == {
        "keywords": ["project falcon"],
        "entropy_threshold": 3.2,
        "entropy_min_length": 16,
    }
    assert tier1_options({}) == {}
