"""Tests for creator search, ranking, and empty-result handling."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services import business_store, creator_service


def test_search_returns_results_for_known_category():
    results = creator_service.search_creators("food", "Arcadia, CA", "18-30", max_results=5)
    assert len(results) > 0
    assert len(results) <= 5


def test_search_never_returns_empty_for_unknown_category():
    """Spec requirement: a search that matches nothing should widen rather
    than returning an empty list, so the demo never dead-ends."""
    results = creator_service.search_creators("underwater basket weaving", "Nowhere, ZZ", "", max_results=5)
    assert len(results) > 0


def test_search_respects_max_results():
    results = creator_service.search_creators("food", "Arcadia, CA", "", max_results=3)
    assert len(results) == 3


def test_search_prioritizes_matching_category_and_location():
    results = creator_service.search_creators("food", "Arcadia, CA", "", max_results=10)
    top_handles = {c["handle"] for c in results[:3]}
    # Arcadia-based food creators should surface above unrelated-category
    # or far-away creators.
    assert any("arcadia" in h.lower() for h in top_handles)


def test_rank_creators_is_deterministic_and_sorted():
    business = {
        "business_category": "food",
        "sub_category": "bakery",
        "location": "Arcadia, CA",
        "target_age_min": 18,
        "target_age_max": 30,
        "target_interests": ["food", "desserts"],
        "marketing_goal": "local_customer_acquisition",
        "budget": 300,
    }
    business_id = business_store.save_business(business)

    candidates = creator_service.search_creators("food", "Arcadia, CA", "18-30", max_results=10)
    creator_ids = [c["id"] for c in candidates]

    ranked_first = creator_service.rank_creators(business_id, creator_ids)
    ranked_second = creator_service.rank_creators(business_id, creator_ids)

    assert ranked_first == ranked_second

    scores = [r["fit_score"] for r in ranked_first]
    assert scores == sorted(scores, reverse=True)


def test_rank_creators_returns_empty_for_unknown_business():
    result = creator_service.rank_creators("business_does_not_exist", ["creator_001"])
    assert result == []


def test_analyze_creator_returns_none_for_unknown_ids():
    business_id = business_store.save_business({
        "business_category": "food", "location": "Arcadia, CA",
        "target_age_min": 18, "target_age_max": 30,
        "target_interests": ["food"], "budget": 100,
    })
    assert creator_service.analyze_creator("creator_does_not_exist", business_id) is None
    assert creator_service.analyze_creator("creator_001", "business_does_not_exist") is None
