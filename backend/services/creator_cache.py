"""
Session-scoped cache for externally-discovered creators (YouTube, web
search) so they can be looked up by id later in the same way mock-
dataset creators can via CreatorProvider.get_creator().

Why this exists: generate_campaign and other tools resolve creator_ids
back to full creator records. The mock dataset supports that natively
(CreatorProvider is a fixed, always-available catalog), but a real
creator found via search_youtube_creators or search_real_creators only
exists for the duration of that one search -- there's no persistent
catalog to look it up in afterward. This cache bridges that gap: any
tool that discovers real creators stores them here, and anything that
needs to resolve a creator_id checks here first, falling back to the
mock provider for ids it doesn't recognize.

In-memory and process-lifetime only, exactly like business_store.py --
no database, cleared on restart. That's fine for a single demo session.
"""

from __future__ import annotations

from typing import Optional

_cache: dict[str, dict] = {}


def cache_creators(creators: list[dict]) -> None:
    for creator in creators:
        creator_id = creator.get("id") or creator.get("creator_id")
        if creator_id:
            _cache[creator_id] = creator


def get_cached_creator(creator_id: str) -> Optional[dict]:
    return _cache.get(creator_id)
