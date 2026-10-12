"""Unit tests for prompt-agnostic Ollama client (Phase 2)."""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.detection.llm_client import LLMClientError, call_ollama


def _mock_response(status_code: int = 200, content_dict: dict | None = None, raw_text: str | None = None):
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status_code
    mock.raise_for_status.return_value = None
    if raw_text is not None:
        mock.json.return_value = {"message": {"content": raw_text}}
    elif content_dict is not None:
        mock.json.return_value = {"message": {"content": json.dumps(content_dict)}}
    else:
        mock.json.return_value = {"message": {"content": "{}"}}
    return mock


def test_call_ollama_success():
    expected_payload = {"is_sensitive": True, "category": "secret", "confidence": 0.9, "reason": "AWS Key found"}
    mock_resp = _mock_response(content_dict=expected_payload)

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        res = call_ollama(
            prompt="Is this key secret?",
            schema={"type": "object"},
            model="test-model",
            url="http://127.0.0.1:11434",
            timeout=2.0,
        )

        assert res == expected_payload
        assert mock_post.call_count == 1
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["model"] == "test-model"
        assert call_kwargs["json"]["format"] == {"type": "object"}
        assert call_kwargs["json"]["options"]["temperature"] == 0.0


def test_call_ollama_retries_once_on_timeout():
    success_payload = {"is_sensitive": False, "category": "benign", "confidence": 0.1, "reason": "Public talk"}
    mock_success = _mock_response(content_dict=success_payload)

    # First call times out, second call succeeds
    with patch("httpx.Client.post", side_effect=[httpx.TimeoutException("Read timed out"), mock_success]) as mock_post:
        res = call_ollama(prompt="hello")
        assert res == success_payload
        assert mock_post.call_count == 2


def test_call_ollama_fails_after_two_attempts():
    with patch("httpx.Client.post", side_effect=httpx.ConnectError("Connection refused")) as mock_post:
        with pytest.raises(LLMClientError) as exc_info:
            call_ollama(prompt="test prompt")

        assert "failed after 2 attempts" in str(exc_info.value)
        assert mock_post.call_count == 2


def test_call_ollama_invalid_json_retries():
    success_payload = {"is_sensitive": True, "category": "secret", "confidence": 0.8, "reason": "ok"}
    mock_bad = _mock_response(raw_text="not valid json")
    mock_good = _mock_response(content_dict=success_payload)

    with patch("httpx.Client.post", side_effect=[mock_bad, mock_good]) as mock_post:
        res = call_ollama(prompt="retry test")
        assert res == success_payload
        assert mock_post.call_count == 2
