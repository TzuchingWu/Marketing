"""
Thin wrapper around the Anthropic API.

Used only for text generation/explanation (business understanding
narratives, recommendation explanations, outreach messages, campaign
ideas) -- never for scoring or arithmetic, which stays deterministic in
scoring_service.py.

If no API key is configured, or the call fails for any reason, every
function here returns None so callers can fall back to a templated
response. The demo must keep working with zero external dependencies.
"""

from __future__ import annotations

import os

_client = None
_client_init_attempted = False

DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")


def _get_client():
    global _client, _client_init_attempted
    if _client_init_attempted:
        return _client
    _client_init_attempted = True

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
        _client = anthropic.Anthropic(api_key=api_key)
    except Exception:
        _client = None
    return _client


def generate_text(system_prompt: str, user_prompt: str, max_tokens: int = 400) -> str | None:
    """Call the LLM with a system + user prompt, returning plain text or
    None on any failure (missing key, network error, bad response)."""
    client = _get_client()
    if client is None:
        return None

    try:
        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        text = "".join(parts).strip()
        return text or None
    except Exception:
        return None


def is_available() -> bool:
    return _get_client() is not None
