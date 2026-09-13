"""
Tests for real creator discovery via OpenAI web search, and the scoring
service's neutral-default handling of unknown (not fabricated) creator
fields.

No real network/API calls: `web_search_service._get_client` is
monkeypatched with a fake client whose `.responses.create()` returns a
canned response, so these tests need no real API key to run.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services import scoring_service, web_search_service


class _FakeResponse:
    def __init__(self, output_text):
        self.output_text = output_text


class _FakeResponses:
    def __init__(self, output_text):
        self._output_text = output_text

    def create(self, **kwargs):
        return _FakeResponse(self._output_text)


class _FakeClient:
    def __init__(self, output_text):
        self.responses = _FakeResponses(output_text)


def test_not_configured_returns_empty_list(monkeypatch):
    monkeypatch.delenv("OPEN_AI_WEBSEARCH_API_KEY", raising=False)
    assert web_search_service.is_configured() is False
    assert web_search_service.find_real_creators("food", "Arcadia, CA") == []


VALID_RESPONSE = """[
  {"platform": "Instagram", "handle": "@realfoodie909", "name": "Real Foodie 909",
   "approximate_followers": 15000, "bio": "SGV food reviews", "source_url": "https://instagram.com/realfoodie909"},
  {"platform": "TikTok", "handle": "arcadiaeatsnow", "name": "Arcadia Eats Now",
   "approximate_followers": null, "bio": "Local eats", "source_url": null}
]"""


def test_parses_valid_json_response(monkeypatch):
    monkeypatch.setattr(web_search_service, "_get_client", lambda: _FakeClient(VALID_RESPONSE))

    results = web_search_service.find_real_creators("food", "Arcadia, CA", max_results=5)

    assert len(results) == 2
    first = results[0]
    assert first["handle"] == "@realfoodie909"
    assert first["followers"] == 15000
    assert first["source"] == "web_search"
    assert first["verified"] is True
    assert first["engagement_rate"] is None
    assert first["audience_local_percentage"] is None

    second = results[1]
    assert second["followers"] is None
    assert second["verified"] is False


def test_handles_markdown_fenced_response(monkeypatch):
    fenced = f"Here are the creators I found:\n```json\n{VALID_RESPONSE}\n```"
    monkeypatch.setattr(web_search_service, "_get_client", lambda: _FakeClient(fenced))

    results = web_search_service.find_real_creators("food", "Arcadia, CA")
    assert len(results) == 2


def test_handles_malformed_json_gracefully(monkeypatch):
    monkeypatch.setattr(web_search_service, "_get_client", lambda: _FakeClient("not json at all"))
    assert web_search_service.find_real_creators("food", "Arcadia, CA") == []


def test_skips_items_without_a_handle(monkeypatch):
    response = '[{"platform": "Instagram", "name": "No Handle", "bio": "..."}]'
    monkeypatch.setattr(web_search_service, "_get_client", lambda: _FakeClient(response))
    assert web_search_service.find_real_creators("food", "Arcadia, CA") == []


def test_never_raises_on_api_exception(monkeypatch):
    class _RaisingResponses:
        def create(self, **kwargs):
            raise ConnectionError("simulated network failure")

    class _RaisingClient:
        responses = _RaisingResponses()

    monkeypatch.setattr(web_search_service, "_get_client", lambda: _RaisingClient())
    assert web_search_service.find_real_creators("food", "Arcadia, CA") == []


def test_respects_max_results(monkeypatch):
    many = "[" + ",".join(
        f'{{"platform": "Instagram", "handle": "@creator{i}", "name": "Creator {i}", "bio": "x"}}'
        for i in range(10)
    ) + "]"
    monkeypatch.setattr(web_search_service, "_get_client", lambda: _FakeClient(many))

    results = web_search_service.find_real_creators("food", "Arcadia, CA", max_results=3)
    assert len(results) == 3


# --- Scoring service: unknown fields must be neutral, not confirmed-zero ---

BUSINESS = {
    "business_category": "food",
    "location": "Arcadia, CA",
    "target_age_min": 18,
    "target_age_max": 30,
    "target_interests": ["food"],
    "budget": 300,
}


def test_unknown_engagement_rate_is_neutral_not_zero():
    creator_unknown = {"engagement_rate": None}
    creator_zero = {"engagement_rate": 0}
    assert scoring_service.engagement_score(creator_unknown) > scoring_service.engagement_score(creator_zero)


def test_unknown_local_percentage_is_neutral_not_zero():
    creator_unknown = {"location": "Arcadia, CA", "audience_local_percentage": None}
    creator_zero = {"location": "Arcadia, CA", "audience_local_percentage": 0}
    assert scoring_service.locality_score(BUSINESS, creator_unknown) > scoring_service.locality_score(BUSINESS, creator_zero)


def test_unknown_audience_age_range_is_neutral_not_zero():
    creator_unknown = {"audience_age_range": None}
    creator_missing = {"audience_age_range": ""}
    assert scoring_service.audience_score(BUSINESS, creator_unknown) == 12.5
    assert scoring_service.audience_score(BUSINESS, creator_missing) == 12.5


def test_web_search_creator_gets_reasonable_overall_score():
    """A real creator with only followers/location/category known (everything
    else unknown) should score in a plausible middle range, not be crushed
    to near-zero just because most fields are unverifiable."""
    real_creator = {
        "id": "web_0_realfoodie909", "handle": "@realfoodie909", "name": "Real Foodie 909",
        "platform": "Instagram", "location": "Arcadia, CA", "categories": ["food"],
        "followers": 15000, "bio": "SGV food reviews",
        "avg_likes": None, "avg_comments": None, "engagement_rate": None,
        "audience_age_range": None, "audience_local_percentage": None,
        "estimated_collaboration_cost": None,
    }
    result = scoring_service.calculate_creator_fit_score(BUSINESS, real_creator)
    assert 40 <= result["fit_score"] <= 90
