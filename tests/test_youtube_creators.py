"""
Tests for real creator discovery via the YouTube Data API v3.

No real network calls: `youtube_service._get` is monkeypatched with
canned responses, so these tests need no real API key to run.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services import scoring_service, youtube_service


def test_not_configured_returns_empty_list(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API", raising=False)
    assert youtube_service.is_configured() is False
    assert youtube_service.search_creators("food", "Los Angeles") == []


SEARCH_RESPONSE = {
    "items": [
        {"snippet": {"channelId": "UC_aaa"}},
        {"snippet": {"channelId": "UC_bbb"}},
    ],
}

CHANNELS_RESPONSE = {
    "items": [
        {
            "id": "UC_aaa",
            "snippet": {"title": "Big Food Channel", "customUrl": "@bigfood", "description": "LA food reviews"},
            "statistics": {"subscriberCount": "750000"},
        },
        {
            "id": "UC_bbb",
            "snippet": {"title": "Small Food Channel", "description": "Cheap eats in LA"},
            "statistics": {"subscriberCount": "1200"},
        },
    ],
}


def test_search_creators_returns_real_verified_data(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API", "fake-key")

    def fake_get(path, params):
        if path == "search":
            return SEARCH_RESPONSE
        if path == "channels":
            return CHANNELS_RESPONSE
        return None

    monkeypatch.setattr(youtube_service, "_get", fake_get)

    results = youtube_service.search_creators("food", "Los Angeles", max_results=5)

    assert len(results) == 2
    # Sorted by real subscriber count, highest first.
    assert results[0]["name"] == "Big Food Channel"
    assert results[0]["followers"] == 750000
    assert results[0]["handle"] == "@bigfood"
    assert results[0]["source"] == "youtube_api"
    assert results[0]["verified"] is True
    assert results[0]["engagement_rate"] is None  # never fabricated

    assert results[1]["followers"] == 1200
    assert results[1]["handle"] == "Small Food Channel"  # falls back to title when no customUrl


def test_search_creators_respects_max_results(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API", "fake-key")
    monkeypatch.setattr(youtube_service, "_get", lambda path, params: SEARCH_RESPONSE if path == "search" else CHANNELS_RESPONSE)

    results = youtube_service.search_creators("food", "Los Angeles", max_results=1)
    assert len(results) == 1


def test_hidden_subscriber_count_is_none_not_zero(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API", "fake-key")
    channels_with_hidden = {
        "items": [{
            "id": "UC_ccc",
            "snippet": {"title": "Private Count Channel"},
            "statistics": {"hiddenSubscriberCount": True, "subscriberCount": "0"},
        }],
    }

    def fake_get(path, params):
        return {"items": [{"snippet": {"channelId": "UC_ccc"}}]} if path == "search" else channels_with_hidden

    monkeypatch.setattr(youtube_service, "_get", fake_get)

    results = youtube_service.search_creators("food", "")
    assert results[0]["followers"] is None  # not fabricated as 0


def test_search_creators_survives_zero_search_results(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API", "fake-key")
    monkeypatch.setattr(youtube_service, "_get", lambda path, params: {"items": []})
    assert youtube_service.search_creators("food", "Nowhere") == []


def test_search_creators_survives_api_failure(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API", "fake-key")
    monkeypatch.setattr(youtube_service, "_get", lambda path, params: None)
    assert youtube_service.search_creators("food", "Los Angeles") == []


def test_channel_missing_title_is_skipped(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API", "fake-key")
    bad_channels = {"items": [{"id": "UC_ddd", "snippet": {}, "statistics": {}}]}

    def fake_get(path, params):
        return {"items": [{"snippet": {"channelId": "UC_ddd"}}]} if path == "search" else bad_channels

    monkeypatch.setattr(youtube_service, "_get", fake_get)
    assert youtube_service.search_creators("food", "") == []


def test_youtube_creator_gets_reasonable_overall_score():
    """A real YouTube creator with only followers/category/location known
    (everything else unverifiable) should score in a plausible middle
    range via scoring_service's neutral-default handling, same as
    web-search-discovered creators."""
    business = {
        "business_category": "food", "location": "Los Angeles, CA",
        "target_age_min": 18, "target_age_max": 35,
        "target_interests": ["food"], "budget": 300,
    }
    creator = {
        "id": "youtube_UC_aaa", "handle": "@bigfood", "name": "Big Food Channel",
        "platform": "YouTube", "location": "Los Angeles", "categories": ["food"],
        "followers": 750000, "bio": "LA food reviews",
        "avg_likes": None, "avg_comments": None, "engagement_rate": None,
        "audience_age_range": None, "audience_local_percentage": None,
        "estimated_collaboration_cost": None,
    }
    result = scoring_service.calculate_creator_fit_score(business, creator)
    assert 40 <= result["fit_score"] <= 90
