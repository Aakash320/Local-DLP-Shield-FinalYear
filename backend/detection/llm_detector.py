"""Local LLM Text Sensitivity Classifier (Tier 2).

Uses local Ollama chat model to evaluate ambiguous text that triggered Tier 1
heuristics or requires context-aware validation.
"""

from dataclasses import dataclass
import logging

from backend.config import load_config
from .llm_client import LLMClientError, call_ollama

logger = logging.getLogger(__name__)

DEFAULT_MAX_CHARS = 2000

# JSON schema enforced by Ollama during generation
SENSITIVITY_SCHEMA = {
    "type": "object",
    "properties": {
        "is_sensitive": {
            "type": "boolean",
            "description": "True if the text contains sensitive or confidential information",
        },
        "category": {
            "type": "string",
            "description": "Category of sensitive data (e.g. credentials, confidential_business, pii, benign)",
        },
        "confidence": {
            "type": "number",
            "description": "Confidence score from 0.0 to 1.0",
        },
        "reason": {
            "type": "string",
            "description": "Brief 1-sentence reason for this classification",
        },
    },
    "required": ["is_sensitive", "category", "confidence", "reason"],
}

SYSTEM_INSTRUCTION = (
    "You are an offline Data Loss Prevention (DLP) security classifier.\n"
    "Your sole objective is to classify text into 'sensitive' or 'benign'.\n\n"
    "CLASSIFICATION RULES:\n"
    "1. SENSITIVE (is_sensitive: true):\n"
    "   - Internal revenue forecasts, financial projections, business strategy, executive memos.\n"
    "   - Auth tokens, session cookies, passwords, secret keys, bearer tokens, API credentials.\n"
    "   - Employee compensation, salaries, wages, payroll, bonuses, client PII.\n"
    "2. BENIGN (is_sensitive: false, category: 'benign'):\n"
    "   - General casual chat (e.g. lunch plans, greeting colleagues).\n"
    "   - Standard public algorithms or open-source documentation with no private context.\n\n"
    "Output must follow the JSON schema strictly with is_sensitive, category, confidence, and reason."
)


@dataclass(frozen=True)
class LLMVerdict:
    """Structured classification verdict from Tier 2 LLM."""

    is_sensitive: bool
    category: str
    confidence: float
    reason: str
    needs_review: bool = False


def _get_max_chars() -> int:
    try:
        cfg = load_config()
        return int(
            cfg.get("detection", {}).get("llm", {}).get("max_chars", DEFAULT_MAX_CHARS)
        )
    except Exception:
        return DEFAULT_MAX_CHARS


def classify(
    text: str,
    *,
    model: str | None = None,
    url: str | None = None,
    timeout: float | None = None,
    max_chars: int | None = None,
) -> LLMVerdict:
    """Classify input text using local LLM.

    Always returns a structured LLMVerdict.
    If the LLM call times out or fails, fail-safe returns needs_review=True (never silently passes).
    """
    limit = max_chars if max_chars is not None else _get_max_chars()
    truncated_text = text[:limit] if len(text) > limit else text

    user_prompt = f"Text to inspect:\n\"\"\"\n{truncated_text}\n\"\"\""

    try:
        data = call_ollama(
            prompt=user_prompt,
            system_prompt=SYSTEM_INSTRUCTION,
            schema=SENSITIVITY_SCHEMA,
            model=model,
            url=url,
            timeout=timeout,
            temperature=0.0,
        )

        is_sensitive = bool(data.get("is_sensitive", False))
        category = str(data.get("category", "unknown"))
        try:
            confidence = float(data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            confidence = 0.5
        reason = str(data.get("reason", "No reason provided"))

        return LLMVerdict(
            is_sensitive=is_sensitive,
            category=category,
            confidence=confidence,
            reason=reason,
            needs_review=False,
        )

    except (LLMClientError, Exception) as exc:
        logger.error("LLM text classification failed: %s", exc)
        # Fail safe, never fail open
        return LLMVerdict(
            is_sensitive=True,
            category="needs_review",
            confidence=0.5,
            reason=f"LLM classifier unavailable or timed out: {exc}",
            needs_review=True,
        )
