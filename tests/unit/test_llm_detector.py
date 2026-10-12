"""Unit and integration tests for Tier 2 LLM text classifier (Phase 2)."""

import time
from unittest.mock import patch
import pytest

from backend.detection.llm_client import LLMClientError
from backend.detection.llm_detector import LLMVerdict, classify


def test_classify_sensitive_text_mocked():
    mock_payload = {
        "is_sensitive": True,
        "category": "credentials",
        "confidence": 0.95,
        "reason": "Contains database password and credentials",
    }
    with patch("backend.detection.llm_detector.call_ollama", return_value=mock_payload):
        verdict = classify("DB_PASSWORD=SuperSecretPass123")
        assert isinstance(verdict, LLMVerdict)
        assert verdict.is_sensitive is True
        assert verdict.category == "credentials"
        assert verdict.confidence == 0.95
        assert verdict.needs_review is False


def test_classify_benign_text_mocked():
    mock_payload = {
        "is_sensitive": False,
        "category": "benign",
        "confidence": 0.05,
        "reason": "Standard workplace meeting invite",
    }
    with patch("backend.detection.llm_detector.call_ollama", return_value=mock_payload):
        verdict = classify("Let's meet at 10am tomorrow for coffee.")
        assert verdict.is_sensitive is False
        assert verdict.category == "benign"
        assert verdict.confidence == 0.05
        assert verdict.needs_review is False


def test_classify_text_truncation():
    with patch("backend.detection.llm_detector.call_ollama") as mock_call:
        mock_call.return_value = {
            "is_sensitive": False,
            "category": "benign",
            "confidence": 0.1,
            "reason": "clean",
        }
        long_text = "A" * 5000
        classify(long_text, max_chars=100)
        assert mock_call.call_count == 1
        prompt = mock_call.call_args[1]["prompt"]
        # Make sure only 100 characters of 'A' are included
        assert "A" * 100 in prompt
        assert "A" * 101 not in prompt


def test_classify_fail_safe_on_timeout_or_error():
    # Core principle: Fail safe, never fail open.
    with patch("backend.detection.llm_detector.call_ollama", side_effect=LLMClientError("Timed out")):
        verdict = classify("ambiguous text snippet")
        assert verdict.is_sensitive is True
        assert verdict.category == "needs_review"
        assert verdict.needs_review is True
        assert "timed out" in verdict.reason.lower()


@pytest.mark.llm
def test_classify_live_ollama():
    """Live test requiring Ollama running with chat model."""
    start = time.perf_counter()
    verdict = classify(
        "Quarterly financial projections: Project Falcon will increase revenue by 40%. Strictly confidential."
    )
    elapsed = time.perf_counter() - start

    assert isinstance(verdict, LLMVerdict)
    assert verdict.needs_review is False
    assert verdict.is_sensitive is True
    print(f"\nLive Ollama Latency: {elapsed:.2f}s | Verdict: {verdict}")
