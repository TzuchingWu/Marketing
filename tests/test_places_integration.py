"""
Tests for Google Places integration -- analyze_business enrichment and
analyze_online_presence's real-vs-simulated scoring.

No real network calls are made: `places_service.lookup_business` /
`nearby_places` are monkeypatched directly, since these are the only
seams that ever touch the network. This also means these tests don't
need a real GOOGLE_MAPS_API_KEY to run.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services import marketing_service, places_service


BASE_BUSINESS_INPUT = {
    "business_name": "Sakura Bakery",
    "business_type": "Korean bakery",
    "location": "Arcadia, CA",
    "description": "Small Korean bakery selling pastries, coffee, and fresh bread.",
    "target_audience": "18-30 year olds",
    "goal": "Get more local customers",
    "budget": 300,
}


def test_analyze_business_without_places_key_is_unaffected(monkeypatch):
    """No GOOGLE_MAPS_API_KEY -> lookup_business returns None -> business
    analysis behaves exactly as it did before Places existed."""
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    result = marketing_service.analyze_business(BASE_BUSINESS_INPUT)
    assert result["google_verified"] is False
    assert result["business_category"] == "food"  # deterministic classification still works


def test_analyze_business_merges_real_places_data(monkeypatch):
    fake_places_data = {
        "google_place_id": "abc123",
        "google_verified": True,
        "formatted_address": "123 Main St, Arcadia, CA 91006",
        "latitude": 34.1397,
        "longitude": -118.0353,
        "google_rating": 4.7,
        "google_review_count": 152,
        "has_website": True,
        "business_status": "OPERATIONAL",
        "has_hours_listed": True,
    }
    monkeypatch.setattr(places_service, "lookup_business", lambda *a, **k: fake_places_data)

    result = marketing_service.analyze_business(BASE_BUSINESS_INPUT)

    assert result["google_verified"] is True
    assert result["latitude"] == 34.1397
    assert result["longitude"] == -118.0353
    assert result["google_rating"] == 4.7
    # Deterministic classification fields are untouched by the merge.
    assert result["business_category"] == "food"
    assert result["sub_category"] == "bakery"


def test_analyze_business_survives_places_lookup_failure(monkeypatch):
    def _raise(*args, **kwargs):
        raise ConnectionError("simulated network failure")

    monkeypatch.setattr(places_service, "lookup_business", _raise)

    result = marketing_service.analyze_business(BASE_BUSINESS_INPUT)
    assert result["google_verified"] is False
    assert result["business_category"] == "food"


def test_online_presence_uses_simulated_data_when_unverified():
    business = {"business_name": "Sakura Bakery", "google_verified": False}
    result = marketing_service.analyze_online_presence(business)

    assert result["data_source"] == "simulated"
    assert 0 <= result["google_presence"] <= 100
    assert result["nearby_competitors"] == []
    assert any("Google Business Profile" in r for r in result["recommendations"])


def test_online_presence_uses_real_data_when_verified(monkeypatch):
    monkeypatch.setattr(
        places_service, "nearby_places",
        lambda *a, **k: [{"name": "Rival Bakery", "place_id": "xyz", "rating": 4.2,
                           "user_ratings_total": 80, "vicinity": "Arcadia"}],
    )
    business = {
        "business_name": "Sakura Bakery",
        "google_verified": True,
        "google_rating": 4.8,
        "google_review_count": 200,
        "has_website": True,
        "latitude": 34.14,
        "longitude": -118.03,
        "google_place_id": "abc123",
        "sub_category": "bakery",
    }
    result = marketing_service.analyze_online_presence(business)

    assert result["data_source"] == "real"
    # 4.8/5 rating + 200 reviews (capped) + website bonus should score high.
    assert result["google_presence"] >= 90
    assert len(result["nearby_competitors"]) == 1
    assert result["nearby_competitors"][0]["name"] == "Rival Bakery"
    assert any("similar businesses" in r for r in result["recommendations"])


def test_online_presence_score_bounds_regardless_of_source():
    for verified in (True, False):
        business = {
            "business_name": "Test Biz", "google_verified": verified,
            "google_rating": 5, "google_review_count": 10000,  # extreme values
        }
        result = marketing_service.analyze_online_presence(business)
        assert 0 <= result["google_presence"] <= 100
        assert 0 <= result["overall_visibility"] <= 100


def test_places_service_returns_none_without_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    assert places_service.is_configured() is False
    assert places_service.lookup_business("Sakura Bakery", "Arcadia, CA") is None
    assert places_service.nearby_places(34.14, -118.03, "bakery") == []
