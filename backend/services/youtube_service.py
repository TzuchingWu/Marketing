"""
Real YouTube creator discovery via the YouTube Data API v3.

Unlike web_search_service.py (which asks an LLM to interpret generic web
search results and can only report an "approximate" follower count if
one happened to be mentioned somewhere), this hits YouTube's own API
directly -- subscriber count, view count, and video count come back
exact and verified, straight from the platform. What it still can't
give us: engagement rate (would need per-video stats), audience
demographics, local audience percentage, or collaboration cost -- none
of that is public YouTube Data API data, so those fields stay None
(unknown) rather than fabricated, same honesty rule as web_search_service.

Degrades to [] on any failure -- missing key, network error, quota
exceeded, zero results -- so a search never crashes or blocks the rest
of the workflow.
"""

from __future__ import annotations

import os
from typing import Optional

import httpx

_BASE_URL = "https://www.googleapis.com/youtube/v3"
_TIMEOUT = 10.0


def is_configured() -> bool:
    return bool(os.getenv("YOUTUBE_API"))


def _get(path: str, params: dict) -> Optional[dict]:
    api_key = os.getenv("YOUTUBE_API")
    if not api_key:
        return None
    try:
        response = httpx.get(f"{_BASE_URL}/{path}", params={**params, "key": api_key}, timeout=_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError):
        return None


def _search_channel_ids(query: str, max_results: int) -> list[str]:
    result = _get("search", {
        "part": "snippet",
        "q": query,
        "type": "channel",
        "maxResults": min(max_results, 25),
        "regionCode": "US",
    })
    if not result:
        return []
    return [
        item["snippet"]["channelId"]
        for item in result.get("items", [])
        if item.get("snippet", {}).get("channelId")
    ]


def _channel_details(channel_ids: list[str]) -> list[dict]:
    if not channel_ids:
        return []
    result = _get("channels", {
        "part": "snippet,statistics",
        "id": ",".join(channel_ids),
    })
    if not result:
        return []
    return result.get("items", [])


def _to_creator_dict(channel: dict, category: str, location: str) -> Optional[dict]:
    snippet = channel.get("snippet", {})
    stats = channel.get("statistics", {})
    channel_id = channel.get("id")
    title = snippet.get("title")
    if not channel_id or not title:
        return None

    # YouTube auto-generates a "<Artist> - Topic" channel for every
    # artist with music on the platform, aggregating their tracks. These
    # aren't run by a person, have no way to contact or partner with
    # them, and routinely have huge subscriber counts that would
    # otherwise dominate results -- not real creator candidates.
    if title.endswith(" - Topic"):
        return None

    # Channel owners can hide subscriber count -- when hidden, the field
    # is simply absent rather than zero. Don't treat "hidden" as "0 subs".
    followers = None
    if not stats.get("hiddenSubscriberCount") and stats.get("subscriberCount") is not None:
        try:
            followers = int(stats["subscriberCount"])
        except (TypeError, ValueError):
            followers = None

    return {
        "id": f"youtube_{channel_id}",
        "handle": snippet.get("customUrl") or title,
        "name": title,
        "platform": "YouTube",
        "location": location,
        "categories": [category] if category else [],
        "followers": followers,
        "avg_likes": None,
        "avg_comments": None,
        "engagement_rate": None,
        "audience_age_range": None,
        "audience_local_percentage": None,
        "estimated_collaboration_cost": None,
        "bio": (snippet.get("description") or "")[:200],
        "source": "youtube_api",
        "source_url": f"https://www.youtube.com/channel/{channel_id}",
        "verified": True,  # real platform data, not an LLM-interpreted guess
    }


def search_creators(category: str, location: str = "", max_results: int = 5) -> list[dict]:
    """Search YouTube for real channels matching a category (optionally
    narrowed by location text), returning them sorted by real subscriber
    count. Returns [] if unconfigured or the search fails/finds nothing
    -- never raises."""
    if not is_configured():
        return []

    query = f"{category} {location}".strip() or category
    channel_ids = _search_channel_ids(query, max_results * 2)
    if not channel_ids:
        return []

    channels = _channel_details(channel_ids)
    creators = []
    for channel in channels:
        creator = _to_creator_dict(channel, category, location)
        if creator:
            creators.append(creator)

    creators.sort(key=lambda c: c["followers"] or 0, reverse=True)
    return creators[:max_results]
