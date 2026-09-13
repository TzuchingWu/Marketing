"""
Real creator discovery via OpenAI's web search tool.

IMPORTANT HONESTY CONSTRAINT: web search can reliably surface a creator's
platform, handle, name, an approximate follower count (when cited
somewhere on the web), and a bio. It CANNOT reliably surface engagement
rate, audience age range, local audience percentage, or collaboration
cost -- those aren't public web data, they're exactly what the mock
dataset fabricates for demo purposes. This module never asks the model
to guess those fields; they come back as None and the scoring service
treats None as "unknown, apply a neutral default" rather than "confirmed
zero" (see scoring_service.py) so real creators aren't unfairly
penalized for data that simply isn't public.

Every result is tagged `"source": "web_search"` and carries a
`source_url` so the frontend can label it as real-but-partially-verified
data, distinct from the clearly-fictional demo dataset.

Degrades to [] on any failure -- missing key, network error, bad JSON,
zero results -- so a search never crashes or blocks the rest of the
workflow. Real cost per call (an LLM call with live web search), no free
tier -- this is why it's a separate opt-in tool, not folded into the
default search_creators path.
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

_MODEL = os.getenv("OPEN_AI_WEBSEARCH_MODEL", "gpt-4o")
_TIMEOUT = 45.0
_client = None
_client_init_attempted = False


def is_configured() -> bool:
    return bool(os.getenv("OPEN_AI_WEBSEARCH_API_KEY"))


def _get_client():
    global _client, _client_init_attempted
    if _client_init_attempted:
        return _client
    _client_init_attempted = True

    api_key = os.getenv("OPEN_AI_WEBSEARCH_API_KEY")
    if not api_key:
        return None
    try:
        import openai
        _client = openai.OpenAI(api_key=api_key, timeout=_TIMEOUT)
    except Exception:
        _client = None
    return _client


def _split_location(location: str) -> tuple[Optional[str], Optional[str]]:
    parts = [p.strip() for p in (location or "").split(",")]
    city = parts[0] if parts and parts[0] else None
    region = parts[1] if len(parts) > 1 and parts[1] else None
    return city, region


def _extract_json_array(text: str) -> list:
    """The model is asked for a bare JSON array but sometimes wraps it in
    markdown fences or adds a sentence before/after -- pull out just the
    array."""
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        array_match = re.search(r"\[.*\]", text, re.DOTALL)
        if array_match:
            text = array_match.group(0)
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def _to_creator_dict(item: dict, index: int, category: str, location: str) -> Optional[dict]:
    handle = (item.get("handle") or "").strip()
    if not handle:
        return None
    if not handle.startswith("@") and item.get("platform", "").lower() != "youtube":
        handle = f"@{handle}"

    followers = item.get("approximate_followers")
    followers = int(followers) if isinstance(followers, (int, float)) and followers > 0 else None

    return {
        "id": f"web_{index}_{handle.lstrip('@')}",
        "handle": handle,
        "name": item.get("name") or handle,
        "platform": item.get("platform") or "Unknown",
        "location": item.get("location") or location,
        "categories": [category] if category else [],
        "followers": followers,
        "avg_likes": None,
        "avg_comments": None,
        "engagement_rate": None,
        "audience_age_range": None,
        "audience_local_percentage": None,
        "estimated_collaboration_cost": None,
        "bio": item.get("bio") or "",
        "source": "web_search",
        "source_url": item.get("source_url"),
        "verified": bool(item.get("source_url")),
    }


def find_real_creators(category: str, location: str, target_audience: str = "", max_results: int = 5) -> list[dict]:
    """Search the web for real, currently-active creators matching the
    given category/location. Returns [] if unconfigured or the call fails
    -- never raises."""
    client = _get_client()
    if client is None:
        return []

    city, region = _split_location(location)
    user_location: dict = {"type": "approximate"}
    if city:
        user_location["city"] = city
    if region:
        user_location["region"] = region

    prompt = (
        f"Search the web for up to {max_results} REAL, currently active social media content "
        f"creators (Instagram, TikTok, or YouTube) who post about '{category}' content and are "
        f"based in or near {location}."
        + (f" Their audience should appeal to: {target_audience}." if target_audience else "")
        + "\n\nFor each creator you can actually verify via search, report ONLY:\n"
        "- platform (Instagram, TikTok, or YouTube)\n"
        "- handle (their @handle or channel name)\n"
        "- name (display name)\n"
        "- approximate_followers (a number, ONLY if you found one actually cited somewhere -- "
        "null if you didn't find one, do not estimate)\n"
        "- bio (one line, from their actual profile)\n"
        "- source_url (the page where you found this)\n\n"
        "Do NOT invent or estimate engagement rate, audience demographics, or collaboration "
        "pricing -- omit real creators you can't verify rather than guessing. Respond with ONLY "
        "a JSON array, no other text, no markdown fences. Example:\n"
        '[{"platform": "Instagram", "handle": "@example", "name": "Example", '
        '"approximate_followers": 12000, "bio": "...", "source_url": "https://..."}]'
    )

    try:
        response = client.responses.create(
            model=_MODEL,
            tools=[{"type": "web_search", "user_location": user_location}],
            input=prompt,
        )
        text = response.output_text
    except Exception:
        return []

    if not text:
        return []

    items = _extract_json_array(text)
    results = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        creator = _to_creator_dict(item, i, category, location)
        if creator:
            results.append(creator)
    return results[:max_results]
