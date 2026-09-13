"""
Tests for Google Veo video generation and the ad-concept pipeline.

No real network calls: `httpx.post`/`httpx.get` are monkeypatched with
fake response objects. Poll timing constants are shrunk via monkeypatch
so the timeout-path test doesn't actually wait 180 seconds.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from backend.services import marketing_service, veo_service


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code
        self.text = str(json_data)

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://example.com")
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    def json(self):
        return self._json


def test_veo_not_configured(monkeypatch):
    monkeypatch.delenv("GOOGLE_VEO_API_KEY", raising=False)
    result = veo_service.generate_video("a prompt")
    assert result == {"status": "not_configured", "video_url": None, "reason": "GOOGLE_VEO_API_KEY not set"}


def test_veo_submit_failure(monkeypatch):
    monkeypatch.setenv("GOOGLE_VEO_API_KEY", "fake-key")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _FakeResponse({"error": "bad request"}, status_code=400))

    result = veo_service.generate_video("a prompt")
    assert result["status"] == "failed"
    assert "submit rejected" in result["reason"].lower()


def test_veo_submit_missing_operation_name(monkeypatch):
    monkeypatch.setenv("GOOGLE_VEO_API_KEY", "fake-key")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _FakeResponse({"unexpected": "shape"}))

    result = veo_service.generate_video("a prompt")
    assert result["status"] == "failed"
    assert "no operation name" in result["reason"].lower()


def test_veo_ready_after_polling(monkeypatch):
    monkeypatch.setenv("GOOGLE_VEO_API_KEY", "fake-key")
    monkeypatch.setattr(veo_service, "_POLL_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _FakeResponse({"name": "operations/abc123"}))

    call_count = {"n": 0}

    def fake_get(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] < 2:
            return _FakeResponse({"done": False})
        return _FakeResponse({
            "done": True,
            "response": {"generateVideoResponse": {"generatedSamples": [
                {"video": {"uri": "https://example.com/video.mp4"}}
            ]}},
        })

    monkeypatch.setattr(httpx, "get", fake_get)

    result = veo_service.generate_video("a prompt")
    assert result["status"] == "ready"
    assert result["video_url"] == "https://example.com/video.mp4&key=fake-key"
    assert call_count["n"] >= 2  # confirms it actually polled more than once


def test_veo_error_reported_by_google(monkeypatch):
    monkeypatch.setenv("GOOGLE_VEO_API_KEY", "fake-key")
    monkeypatch.setattr(veo_service, "_POLL_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _FakeResponse({"name": "operations/abc123"}))
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(
        {"done": True, "error": {"code": 8, "message": "quota exceeded"}}
    ))

    result = veo_service.generate_video("a prompt")
    assert result["status"] == "failed"
    assert "quota exceeded" in result["reason"]


def test_veo_times_out_if_never_done(monkeypatch):
    monkeypatch.setenv("GOOGLE_VEO_API_KEY", "fake-key")
    monkeypatch.setattr(veo_service, "_POLL_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(veo_service, "_MAX_WAIT_SECONDS", 0.03)
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _FakeResponse({"name": "operations/abc123"}))
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse({"done": False}))

    result = veo_service.generate_video("a prompt")
    assert result["status"] == "timed_out"


BUSINESS_UNVERIFIED = {"business_name": "Tony's Ramen", "business_category": "food", "location": "Riverside, CA"}
BUSINESS_VERIFIED = {
    "business_name": "Tony's Ramen", "business_category": "food", "sub_category": "restaurant",
    "location": "Riverside, CA", "google_verified": True, "google_rating": 4.2,
    "google_review_count": 340, "formatted_address": "123 University Ave, Riverside, CA",
}


def test_ad_concept_fallback_has_required_shape(monkeypatch):
    monkeypatch.setattr(marketing_service.llm_client, "generate_text", lambda *a, **k: None)

    result = marketing_service.generate_ad_concept(
        BUSINESS_UNVERIFIED, "$12 lunch special", "college students", "energetic", duration_seconds=8
    )
    assert result["campaign_angle"]
    assert len(result["scenes"]) >= 1
    assert "Tony's Ramen" in result["video_prompt"]
    assert "$12 lunch special" in result["video_prompt"]


def test_ad_concept_incorporates_discovered_facts_into_prompt(monkeypatch):
    """When analyze_business found real Places data, the LLM prompt sent
    to generate the ad concept should include those facts -- this is
    what makes the pipeline 'discovers real signals' rather than 'makes
    up generic filler'."""
    captured_prompts = []

    def fake_generate_text(system_prompt, user_prompt, max_tokens=500):
        captured_prompts.append(user_prompt)
        return None  # force fallback so we don't need to also fake a full LLM response here

    monkeypatch.setattr(marketing_service.llm_client, "generate_text", fake_generate_text)

    marketing_service.generate_ad_concept(BUSINESS_VERIFIED, "20% off", "students near UCR", "authentic")

    assert len(captured_prompts) == 1
    assert "4.2" in captured_prompts[0]
    assert "340" in captured_prompts[0]


def test_ad_concept_parses_llm_response(monkeypatch):
    fake_response = (
        "ANGLE: Your $12 Study Break\n"
        "VIDEO_PROMPT: A tired college student walks out of a lecture hall, cuts to steam rising off "
        "a fresh bowl of ramen being ladled at Tony's Ramen, ending on the logo with a 20% off offer.\n"
        "SCENES:\n"
        "1. 0-2s | Student leaving class looking tired | \n"
        "2. 2-5s | Close-up of steaming ramen being prepared | Tony's Ramen\n"
        "3. 5-8s | Logo and offer text | 20% off today\n"
    )
    monkeypatch.setattr(marketing_service.llm_client, "generate_text", lambda *a, **k: fake_response)

    result = marketing_service.generate_ad_concept(BUSINESS_VERIFIED, "20% off", "students near UCR", "authentic")

    assert result["campaign_angle"] == "Your $12 Study Break"
    assert len(result["scenes"]) == 3
    assert result["scenes"][1]["shot"] == "Close-up of steaming ramen being prepared"
    assert "tired college student" in result["video_prompt"].lower()


def test_generate_video_ad_tool_returns_concept_even_when_video_unconfigured(monkeypatch):
    """The MCP tool should still return a usable ad concept when Veo
    itself isn't configured -- video.status carries that information,
    it doesn't become a hard failure for the whole tool call."""
    from backend.mcp.tools import video_tools
    from backend.services import business_store

    monkeypatch.delenv("GOOGLE_VEO_API_KEY", raising=False)
    monkeypatch.setattr(marketing_service.llm_client, "generate_text", lambda *a, **k: None)

    business_id = business_store.save_business(BUSINESS_VERIFIED)

    class _FakeMCP:
        def tool(self):
            def decorator(fn):
                self.registered = getattr(self, "registered", {})
                self.registered[fn.__name__] = fn
                return fn
            return decorator

    fake_mcp = _FakeMCP()
    video_tools.register(fake_mcp)

    result = fake_mcp.registered["generate_video_ad"](
        business_id=business_id, offer="20% off", target_audience="students", style="authentic",
    )

    assert result["video"]["status"] == "not_configured"
    assert result["campaign_angle"]
    assert result["video_prompt"]
