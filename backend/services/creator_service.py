"""
Creator search, analysis, and ranking -- the glue between the creator
data provider and the deterministic scoring service.
"""

from __future__ import annotations

from backend.data.creator_provider import get_provider
from . import scoring_service
from .business_store import get_business

# Cities considered "in range" of each other for a location-aware search.
# Kept in sync with scoring_service's adjacency map but used here for
# candidate *filtering*, not scoring.
from .scoring_service import ADJACENT_CITIES, GREATER_LA_CITIES, _city_key


def category_match(business_category: str, creator: dict) -> bool:
    if not business_category:
        return True
    return business_category.lower() in {c.lower() for c in creator.get("categories", [])}


def _candidate_relevance(business_like: dict, creator: dict) -> float:
    """Cheap pre-score used only to order/filter search results -- the
    authoritative fit score is computed later by analyze_creator/rank_creators."""
    score = 0.0
    business_city = _city_key(business_like.get("location", ""))
    creator_city = _city_key(creator.get("location", ""))
    if business_city and creator_city == business_city:
        score += 3
    elif creator_city in ADJACENT_CITIES.get(business_city, set()):
        score += 2
    elif business_city in GREATER_LA_CITIES and creator_city in GREATER_LA_CITIES:
        score += 1

    category = (business_like.get("category") or business_like.get("business_category") or "").lower()
    creator_categories = {c.lower() for c in creator.get("categories", [])}
    if category in creator_categories:
        score += 2

    interests = {i.lower() for i in business_like.get("target_interests", [])}
    score += len(interests & creator_categories) * 0.5

    return score


def search_creators(category: str, location: str, target_audience: str, max_results: int = 10) -> list[dict]:
    """Find candidate creators matching a category/location/audience query.

    Falls back to widening the search (dropping the strict category
    requirement, then location) if too few candidates are found, so the
    demo never returns an empty list for a reasonable query.
    """
    all_creators = get_provider().list_creators()
    query = {"category": category, "location": location, "target_interests": [category] if category else []}

    def rank(pool: list[dict]) -> list[dict]:
        scored = [(c, _candidate_relevance(query, c)) for c in pool]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return [c for c, _ in scored]

    # Tier 1: matches category
    candidates = [c for c in all_creators if category_match(category, c)]
    if len(candidates) < 3:
        # Tier 2: widen to anything in the greater region regardless of category
        candidates = list(all_creators)

    ranked = rank(candidates)
    return ranked[:max_results]


def analyze_creator(creator_id: str, business_id: str) -> dict | None:
    """Score a single creator against a previously-analyzed business."""
    business = get_business(business_id)
    creator = get_provider().get_creator(creator_id)
    if business is None or creator is None:
        return None
    return scoring_service.calculate_creator_fit_score(business, creator)


def get_creators_with_fit(business_id: str, creator_ids: list[str]) -> list[dict]:
    """Return full creator profiles (followers, cost, etc.) merged with
    their computed fit_score -- used by campaign generation, which needs
    both the raw creator data and the score in one place."""
    business = get_business(business_id)
    if business is None:
        return []

    provider = get_provider()
    merged = []
    for creator_id in creator_ids:
        creator = provider.get_creator(creator_id)
        if creator is None:
            continue
        score_result = scoring_service.calculate_creator_fit_score(business, creator)
        merged.append({**creator, "fit_score": score_result["fit_score"]})

    merged.sort(key=lambda c: c["fit_score"], reverse=True)
    return merged


def rank_creators(business_id: str, creator_ids: list[str]) -> list[dict]:
    """Score and order a set of candidate creators, best fit first."""
    business = get_business(business_id)
    if business is None:
        return []

    provider = get_provider()
    results = []
    for creator_id in creator_ids:
        creator = provider.get_creator(creator_id)
        if creator is None:
            continue
        results.append(scoring_service.calculate_creator_fit_score(business, creator))

    results.sort(key=lambda r: r["fit_score"], reverse=True)
    return results
