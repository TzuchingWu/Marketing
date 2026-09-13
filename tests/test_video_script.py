"""Tests for the video script generation feature (free/instant path)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services import marketing_service


BUSINESS = {
    "business_name": "Sakura Bakery",
    "business_category": "food",
    "location": "Arcadia, CA",
}


def test_fallback_script_has_required_shape(monkeypatch):
    monkeypatch.setattr(marketing_service.llm_client, "generate_text", lambda *a, **k: None)

    result = marketing_service.generate_video_script(BUSINESS, "Weekend bakery run", duration_seconds=30)

    assert result["platform"]
    assert result["duration_seconds"] == 30
    assert result["based_on_idea"] == "Weekend bakery run"
    assert len(result["scenes"]) >= 1
    for scene in result["scenes"]:
        assert "timing" in scene and "shot" in scene and "on_screen_text" in scene
    assert result["caption"]
    assert isinstance(result["hashtags"], list) and len(result["hashtags"]) > 0
    assert result["cta"]


def test_fallback_script_uses_category_template():
    food_result = marketing_service.generate_video_script(
        {"business_name": "X", "business_category": "food", "location": "Y, CA"}, "idea",
    )
    fitness_result = marketing_service.generate_video_script(
        {"business_name": "X", "business_category": "fitness", "location": "Y, CA"}, "idea",
    )
    # Different categories should produce different scene content, not one
    # generic script reused everywhere.
    assert food_result["scenes"] != fitness_result["scenes"]


def test_fallback_script_scene_timings_span_full_duration():
    result = marketing_service.generate_video_script(BUSINESS, "idea", duration_seconds=40)
    first_start = int(result["scenes"][0]["timing"].split("-")[0])
    last_end = int(result["scenes"][-1]["timing"].split("-")[1].rstrip("s"))
    assert first_start == 0
    assert last_end == 40


def test_llm_script_is_parsed_into_scenes(monkeypatch):
    fake_llm_response = (
        "CAPTION: Your new favorite bakery\n"
        "HASHTAGS: #ArcadiaEats #KoreanBakery #SupportLocal\n"
        "SCENES:\n"
        "1. 0-5s | Close-up of pastries in the display case | Fresh daily\n"
        "2. 5-15s | Barista pouring coffee | Pair it with coffee\n"
        "3. 15-30s | Storefront exterior with people walking in | Visit us this weekend\n"
        "CTA: Tag someone who needs this\n"
    )
    monkeypatch.setattr(marketing_service.llm_client, "generate_text", lambda *a, **k: fake_llm_response)

    result = marketing_service.generate_video_script(BUSINESS, "Weekend bakery run", duration_seconds=30)

    assert result["caption"] == "Your new favorite bakery"
    assert result["hashtags"] == ["#ArcadiaEats", "#KoreanBakery", "#SupportLocal"]
    assert result["cta"] == "Tag someone who needs this"
    assert len(result["scenes"]) == 3
    assert result["scenes"][0] == {
        "timing": "0-5s", "shot": "Close-up of pastries in the display case",
        "on_screen_text": "Fresh daily", "audio_note": "",
    }


def test_falls_back_cleanly_when_llm_response_is_malformed(monkeypatch):
    monkeypatch.setattr(marketing_service.llm_client, "generate_text", lambda *a, **k: "not a structured response at all")

    result = marketing_service.generate_video_script(BUSINESS, "idea")
    # No parseable CAPTION/SCENES/etc -- should still return a complete,
    # usable script via the fallback fields, not a broken/empty result.
    assert result["caption"]
    assert len(result["scenes"]) >= 1
