"""Prompt-agnostic client for local Ollama chat models.

Provides call_ollama() with timeout, single retry, and JSON schema constraints.
Reused by Phase 2 (text sensitivity) and Phase 5 (vector match verification).
"""

import json
import logging
from typing import Any

import httpx

from backend.config import load_config

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_CHAT_MODEL = "llama3.2:3b"
DEFAULT_TIMEOUT = 30.0


class LLMClientError(Exception):
    """Raised when Ollama request fails after retry or returns invalid output."""


def _get_defaults() -> tuple[str, str, float]:
    try:
        cfg = load_config()
        models = cfg.get("models", {})
        url = models.get("ollama_url") or DEFAULT_OLLAMA_URL
        model = models.get("chat_model") or DEFAULT_CHAT_MODEL
        det_llm = cfg.get("detection", {}).get("llm", {})
        timeout = float(det_llm.get("timeout_seconds", DEFAULT_TIMEOUT))
        return url, model, timeout
    except Exception:
        return DEFAULT_OLLAMA_URL, DEFAULT_CHAT_MODEL, DEFAULT_TIMEOUT


def call_ollama(
    prompt: str,
    schema: dict[str, Any] | None = None,
    *,
    system_prompt: str | None = None,
    model: str | None = None,
    url: str | None = None,
    timeout: float | None = None,
    temperature: float = 0.0,
) -> dict[str, Any]:
    """Call Ollama's chat endpoint with JSON schema constraint, timeout, and 1 retry.

    Returns the parsed JSON response object.
    Raises LLMClientError on persistent timeout, connection error, or parse failure.
    """
    default_url, default_model, default_timeout = _get_defaults()
    base_url = (url or default_url).rstrip("/")
    target_model = model or default_model
    req_timeout = timeout if timeout is not None else default_timeout

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload: dict[str, Any] = {
        "model": target_model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if schema is not None:
        payload["format"] = schema

    chat_endpoint = f"{base_url}/api/chat"
    last_err: Exception | None = None

    # Timeout + one retry (total of 2 attempts)
    for attempt in range(1, 3):
        try:
            with httpx.Client(timeout=req_timeout) as client:
                resp = client.post(chat_endpoint, json=payload)
                resp.raise_for_status()
                data = resp.json()
                raw_content = data.get("message", {}).get("content", "")
                if not raw_content:
                    raise LLMClientError("Ollama returned empty message content")
                parsed = json.loads(raw_content)
                if not isinstance(parsed, dict):
                    raise LLMClientError(f"Expected JSON object, got {type(parsed).__name__}")
                return parsed
        except (httpx.TimeoutException, httpx.RequestError, json.JSONDecodeError, LLMClientError) as exc:
            last_err = exc
            logger.warning(
                "Ollama call attempt %d failed (%s): %s",
                attempt,
                exc.__class__.__name__,
                exc,
            )

    raise LLMClientError(
        f"Ollama call to {target_model} failed after 2 attempts: {last_err}"
    ) from last_err
