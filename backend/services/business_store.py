"""
Tiny in-memory store for analyzed businesses.

The hackathon MVP has no database: `analyze_business` produces a
business_id that later tool calls (analyze_creator, rank_creators,
generate_campaign) use to look the business back up within the same
running process. This is intentionally ephemeral -- restarting the
server clears it.
"""

from __future__ import annotations

import itertools
from typing import Optional

_businesses: dict[str, dict] = {}
_id_counter = itertools.count(1)


def save_business(business: dict) -> str:
    business_id = f"business_{next(_id_counter):03d}"
    _businesses[business_id] = business
    return business_id


def get_business(business_id: str) -> Optional[dict]:
    return _businesses.get(business_id)
