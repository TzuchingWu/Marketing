"""
Tests for the "general search" flow: free-text intent extraction, real
business disambiguation search, and resolving analyze_business from a
confirmed place_id.

No real network calls: `places_service`/`llm_client` internals are
monkeypatched, so these tests need no real API keys to run.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services import marketing_service, places_service


# --- extract_business_intent ---

def test_extract_intent_fallback_without_llm(monkeypatch):
    monkeypatch.setattr(marketing_service.llm_client, "generate_text", lambda *a, **k: None)

    intent = marketing_service.extract_business_intent(
        "I am Ace Karaoke, I am looking to target a younger audience what should i do"
    )
    assert intent["business_name"] == "Ace Karaoke"
    assert intent["goal"]
    assert intent["location_hint"] == ""


def test_extract_intent_fallback_handles_no_pattern_match(monkeypatch):
    monkeypatch.setattr(marketing_service.llm_client, "generate_text", lambda *a, **k: None)

    intent = marketing_service.extract_business_intent("help me find creators for my shop")
    assert intent["business_name"]  # always returns something searchable, never blank


def test_extract_intent_uses_llm_json_when_available(monkeypatch):
    fake_response = (
        '{"business_name": "Ace Karaoke", "location_hint": "San Gabriel", '
        '"goal": "reach younger customers", "target_audience": "18-27 year olds"}'
    )
    monkeypatch.setattr(marketing_service.llm_client, "generate_text", lambda *a, **k: fake_response)

    intent = marketing_service.extract_business_intent("I am Ace Karaoke, target younger folks")
    assert intent["business_name"] == "Ace Karaoke"
    assert intent["location_hint"] == "San Gabriel"
    assert intent["target_audience"] == "18-27 year olds"


def test_extract_intent_falls_back_on_malformed_llm_json(monkeypatch):
    monkeypatch.setattr(marketing_service.llm_client, "generate_text", lambda *a, **k: "not json")

    intent = marketing_service.extract_business_intent("I am Ace Karaoke, target younger folks")
    assert intent["business_name"] == "Ace Karaoke"


# --- places_service: multi-result search + address parsing ---

def test_city_state_parsing_from_full_street_address():
    address = "711 S San Gabriel Blvd, San Gabriel, CA 91776, USA"
    assert places_service._city_state_from_formatted_address(address) == "San Gabriel, CA"


def test_city_state_parsing_handles_missing_country():
    address = "San Gabriel, CA 91776"
    assert places_service._city_state_from_formatted_address(address) == "San Gabriel, CA"


def test_city_state_parsing_handles_empty_input():
    assert places_service._city_state_from_formatted_address("") == ""


def test_search_businesses_without_key_returns_empty(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    assert places_service.search_businesses("Ace Karaoke") == []


def test_search_businesses_always_sends_explicit_location_bias(monkeypatch):
    """Places biases ambiguous queries toward the REQUESTING SERVER'S IP
    geolocation when no explicit bias is given -- observed live: a query
    with no location resolved to a business in Salem, OR because the
    backend happened to be hosted in an Oregon datacenter. This must
    always pass an explicit bias so results don't depend on server
    hosting location."""
    captured = {}

    def fake_get(path, params):
        captured["params"] = params
        return {"status": "OK", "results": []}

    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fake-key")
    monkeypatch.setattr(places_service, "_get", fake_get)

    places_service.search_businesses("Silver Spoon")
    assert "location" in captured["params"]
    assert "radius" in captured["params"]


def test_lookup_business_always_sends_explicit_location_bias(monkeypatch):
    captured = {}

    def fake_get(path, params):
        captured["params"] = params
        return {"status": "ZERO_RESULTS", "candidates": []}

    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fake-key")
    monkeypatch.setattr(places_service, "_get", fake_get)

    places_service.lookup_business("Some Business", "Arcadia, CA")
    assert "locationbias" in captured["params"]


def test_search_businesses_parses_multiple_results(monkeypatch):
    fake_response = {
        "status": "OK",
        "results": [
            {
                "place_id": "abc123", "name": "Ace Karaoke",
                "formatted_address": "711 S San Gabriel Blvd, San Gabriel, CA 91776, USA",
                "rating": 3.9, "user_ratings_total": 24, "business_status": "OPERATIONAL",
                "geometry": {"location": {"lat": 34.09, "lng": -118.09}}, "types": ["establishment"],
            },
            {
                "place_id": "def456", "name": "Ace Karaoke",
                "formatted_address": "161 S 8th Ave, City of Industry, CA 91746, USA",
                "rating": 4.1, "user_ratings_total": 44, "business_status": "OPERATIONAL",
                "geometry": {"location": {"lat": 34.03, "lng": -117.97}}, "types": ["store"],
            },
        ],
    }
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fake-key")
    monkeypatch.setattr(places_service, "_get", lambda path, params: fake_response)

    results = places_service.search_businesses("Ace Karaoke")
    assert len(results) == 2
    assert results[0]["place_id"] == "abc123"
    assert results[1]["formatted_address"].startswith("161 S 8th Ave")


def test_get_place_details_sets_clean_location(monkeypatch):
    fake_details = {
        "status": "OK",
        "result": {
            "name": "Ace Karaoke",
            "formatted_address": "711 S San Gabriel Blvd, San Gabriel, CA 91776, USA",
            "geometry": {"location": {"lat": 34.09, "lng": -118.09}},
            "rating": 3.9, "user_ratings_total": 24,
            "business_status": "OPERATIONAL", "types": ["establishment"],
        },
    }
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fake-key")
    monkeypatch.setattr(places_service, "_get", lambda path, params: fake_details)

    details = places_service.get_place_details("abc123")
    assert details["location"] == "San Gabriel, CA"
    assert details["google_verified"] is True
    assert details["business_name"] == "Ace Karaoke"


# --- analyze_business with place_id ---

def test_analyze_business_with_place_id_uses_resolved_location(monkeypatch):
    monkeypatch.setattr(marketing_service.llm_client, "generate_text", lambda *a, **k: None)
    monkeypatch.setattr(places_service, "get_place_details", lambda place_id: {
        "google_place_id": place_id,
        "google_verified": True,
        "business_name": "Ace Karaoke",
        "formatted_address": "711 S San Gabriel Blvd, San Gabriel, CA 91776, USA",
        "location": "San Gabriel, CA",
        "latitude": 34.09, "longitude": -118.09,
        "google_rating": 3.9, "google_review_count": 24,
        "has_website": True, "business_status": "OPERATIONAL", "google_types": [],
    })

    business_input = {
        "business_name": "Ace Karaoke", "business_type": "karaoke bar",
        "location": "somewhere vague the user typed", "description": "target younger crowd",
        "target_audience": "18-27 year olds", "goal": "reach younger customers", "budget": 300,
    }
    result = marketing_service.analyze_business(business_input, place_id="abc123")

    assert result["location"] == "San Gabriel, CA"  # resolved, not the vague input
    assert result["google_verified"] is True
    assert result["business_category"] == "nightlife"
    assert result["sub_category"] == "karaoke bar"


def test_analyze_business_without_place_id_falls_back_to_fuzzy_lookup(monkeypatch):
    monkeypatch.setattr(marketing_service.llm_client, "generate_text", lambda *a, **k: None)
    called = {}

    def fake_lookup(name, location, business_type):
        called["args"] = (name, location, business_type)
        return None

    monkeypatch.setattr(places_service, "lookup_business", fake_lookup)

    business_input = {
        "business_name": "Sakura Bakery", "business_type": "bakery",
        "location": "Arcadia, CA", "description": "", "target_audience": "",
        "goal": "", "budget": 100,
    }
    marketing_service.analyze_business(business_input)
    assert called["args"] == ("Sakura Bakery", "Arcadia, CA", "bakery")
