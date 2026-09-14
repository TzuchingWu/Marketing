"""Tests for the deterministic Creator Fit Score algorithm."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services import scoring_service


def make_business(**overrides):
    business = {
        "business_category": "food",
        "sub_category": "bakery",
        "location": "Arcadia, CA",
        "target_age_min": 18,
        "target_age_max": 30,
        "target_interests": ["food", "local businesses", "desserts"],
        "marketing_goal": "local_customer_acquisition",
        "budget": 300,
    }
    business.update(overrides)
    return business


def make_creator(**overrides):
    creator = {
        "id": "creator_test",
        "handle": "@testcreator",
        "location": "Arcadia, CA",
        "categories": ["food", "local"],
        "followers": 12000,
        "engagement_rate": 8.5,
        "audience_age_range": "18-34",
        "audience_local_percentage": 72,
        "estimated_collaboration_cost": 100,
    }
    creator.update(overrides)
    return creator


def test_score_within_bounds():
    business = make_business()
    creator = make_creator()
    result = scoring_service.calculate_creator_fit_score(business, creator)
    assert 0 <= result["fit_score"] <= 100
    for component in result["score_breakdown"].values():
        assert component >= 0


def test_score_is_deterministic():
    business = make_business()
    creator = make_creator()
    first = scoring_service.calculate_creator_fit_score(business, creator)
    second = scoring_service.calculate_creator_fit_score(business, creator)
    assert first == second


def test_higher_local_relevance_increases_score():
    business = make_business(location="Arcadia, CA")
    local_creator = make_creator(location="Arcadia, CA", audience_local_percentage=90)
    distant_creator = make_creator(location="San Diego, CA", audience_local_percentage=10)

    local_result = scoring_service.calculate_creator_fit_score(business, local_creator)
    distant_result = scoring_service.calculate_creator_fit_score(business, distant_creator)

    assert local_result["score_breakdown"]["locality"] > distant_result["score_breakdown"]["locality"]
    assert local_result["fit_score"] > distant_result["fit_score"]


def test_adjacent_city_scores_between_same_city_and_far_city():
    business = make_business(location="Arcadia, CA")
    same_city = make_creator(location="Arcadia, CA", audience_local_percentage=50)
    adjacent_city = make_creator(location="Monrovia, CA", audience_local_percentage=50)
    far_city = make_creator(location="San Diego, CA", audience_local_percentage=50)

    same_score = scoring_service.locality_score(business, same_city)
    adjacent_score = scoring_service.locality_score(business, adjacent_city)
    far_score = scoring_service.locality_score(business, far_city)

    assert same_score > adjacent_score > far_score


def test_higher_audience_match_increases_score():
    business = make_business(target_age_min=18, target_age_max=30)
    matching_creator = make_creator(audience_age_range="18-30")
    mismatched_creator = make_creator(audience_age_range="50-65")

    matching_result = scoring_service.calculate_creator_fit_score(business, matching_creator)
    mismatched_result = scoring_service.calculate_creator_fit_score(business, mismatched_creator)

    assert (
        matching_result["score_breakdown"]["audience_match"]
        > mismatched_result["score_breakdown"]["audience_match"]
    )


def test_over_budget_creators_are_penalized():
    business = make_business(budget=100)
    affordable = make_creator(estimated_collaboration_cost=30)
    expensive = make_creator(estimated_collaboration_cost=500)

    affordable_result = scoring_service.calculate_creator_fit_score(business, affordable)
    expensive_result = scoring_service.calculate_creator_fit_score(business, expensive)

    assert affordable_result["score_breakdown"]["budget_fit"] > expensive_result["score_breakdown"]["budget_fit"]
    assert affordable_result["fit_score"] > expensive_result["fit_score"]
    assert expensive_result["score_breakdown"]["budget_fit"] == 0


def test_unknown_collaboration_cost_is_neutral_not_affordable():
    """A real creator with no public pricing data (e.g. a global
    superstar found via YouTube search) must not score as a perfect
    budget fit just because we don't know their real cost -- that
    treats "unknown" as "definitely free", the opposite of reality."""
    business = make_business(budget=300)
    unknown_cost = make_creator(estimated_collaboration_cost=None)
    genuinely_free = make_creator(estimated_collaboration_cost=0)
    affordable = make_creator(estimated_collaboration_cost=50)

    assert scoring_service.budget_score(business, unknown_cost) == 5.0
    assert scoring_service.budget_score(business, genuinely_free) == 10.0
    assert scoring_service.budget_score(business, unknown_cost) < scoring_service.budget_score(business, affordable)


def test_no_category_overlap_scores_zero_content_relevance():
    business = make_business(business_category="fitness", target_interests=["fitness", "wellness"])
    unrelated_creator = make_creator(categories=["gaming", "tech"])
    assert scoring_service.content_relevance_score(business, unrelated_creator) == 0.0


def test_recommendation_label_matches_score_tier():
    business = make_business()
    strong = make_creator()  # same city, matching category/age, cheap, engaged
    result = scoring_service.calculate_creator_fit_score(business, strong)
    assert result["recommendation"] in {"Strong match", "Good match", "Moderate match", "Weak match"}
    if result["fit_score"] >= 85:
        assert result["recommendation"] == "Strong match"
