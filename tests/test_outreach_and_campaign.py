"""Tests for outreach generation fallback and campaign generation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services import marketing_service


def test_outreach_fallback_is_personalized_not_generic():
    """No ANTHROPIC_API_KEY is set in the test environment, so this
    exercises the template fallback path directly."""
    business = {
        "name": "Sakura Bakery",
        "description": "Korean bakery in Arcadia",
        "goal": "increase local customers",
        "location": "Arcadia, CA",
    }
    creator = {
        "handle": "@arcadiaeats",
        "name": "Arcadia Eats",
        "category": ["food", "local"],
        "location": "Arcadia, CA",
    }
    message = marketing_service.generate_outreach(business, creator, "Free tasting + $100 sponsored post")

    assert "@arcadiaeats" in message
    assert "Sakura Bakery" in message
    assert "Free tasting" in message
    # No accidental duplicate location mentions from string concatenation.
    assert message.count("Arcadia, CA") <= 1


def test_outreach_handles_missing_optional_fields():
    business = {"name": "Test Biz"}
    creator = {"handle": "@testcreator"}
    message = marketing_service.generate_outreach(business, creator, "A free sample")
    assert "@testcreator" in message
    assert isinstance(message, str) and len(message) > 0


def test_analyze_business_extracts_bakery_category():
    result = marketing_service.analyze_business({
        "business_name": "Sakura Bakery",
        "business_type": "Korean bakery",
        "location": "Arcadia, CA",
        "description": "Small Korean bakery selling pastries, coffee, and fresh bread.",
        "target_audience": "18-30 year olds",
        "goal": "Get more local customers",
        "budget": 300,
    })
    assert result["business_category"] == "food"
    assert result["sub_category"] == "bakery"
    assert result["target_age_min"] == 18
    assert result["target_age_max"] == 30
    assert result["marketing_goal"] == "local_customer_acquisition"
    assert "food" in result["target_interests"]


def test_analyze_business_handles_vague_input_gracefully():
    result = marketing_service.analyze_business({
        "business_name": "Mystery Shop",
        "business_type": "",
        "location": "Somewhere, CA",
        "description": "",
        "target_audience": "",
        "goal": "",
        "budget": 0,
    })
    assert result["business_category"]  # falls back to "local lifestyle", never blank
    assert result["target_age_min"] < result["target_age_max"]


def test_generate_campaign_stays_within_budget():
    business = {
        "business_name": "Sakura Bakery",
        "business_category": "food",
        "location": "Arcadia, CA",
        "marketing_goal": "local_customer_acquisition",
    }
    creators = [
        {"handle": "@a", "fit_score": 95, "estimated_collaboration_cost": 150, "followers": 10000},
        {"handle": "@b", "fit_score": 90, "estimated_collaboration_cost": 100, "followers": 8000},
        {"handle": "@c", "fit_score": 80, "estimated_collaboration_cost": 100, "followers": 5000},
    ]
    campaign = marketing_service.generate_campaign(business, creators, budget=200, goal="local_customer_acquisition")

    assert campaign["estimated_spend"] <= 200
    assert campaign["expected_reach"] > 0
    assert len(campaign["content_ideas"]) >= 1


def test_generate_campaign_never_treats_unknown_cost_as_free():
    """Real creators (found via search) have no public pricing data --
    None must not be treated as $0, or a campaign could claim "$0 spend"
    while actually including creators with millions of followers, wildly
    misrepresenting the true cost to the business owner."""
    business = {"business_name": "Ace Karaoke", "business_category": "nightlife", "location": "San Gabriel, CA"}
    creators = [
        {"handle": "@superstar", "fit_score": 95, "estimated_collaboration_cost": None, "followers": 3_000_000},
        {"handle": "@superstar2", "fit_score": 90, "estimated_collaboration_cost": None, "followers": 2_000_000},
    ]
    campaign = marketing_service.generate_campaign(business, creators, budget=300, goal="local_customer_acquisition")

    assert campaign["estimated_spend"] > 0  # never silently "free"
    assert campaign["estimated_spend"] <= 300


def test_generate_campaign_always_includes_at_least_one_creator():
    business = {"business_name": "Tiny Shop", "business_category": "food", "location": "Arcadia, CA"}
    creators = [{"handle": "@expensive", "fit_score": 99, "estimated_collaboration_cost": 5000, "followers": 1000}]
    campaign = marketing_service.generate_campaign(business, creators, budget=10, goal="local_customer_acquisition")
    assert len(campaign["creators"]) == 1
