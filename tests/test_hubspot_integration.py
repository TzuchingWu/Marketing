"""
Tests for HubSpot CRM integration (log_creator_outreach).

No real network calls: `hubspot_service`'s internal HTTP-calling helpers
are monkeypatched directly, so these tests need no real access token to
run.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services import hubspot_service


def test_log_outreach_without_token_is_a_soft_failure(monkeypatch):
    monkeypatch.delenv("HUBSPOT_ACCESS_TOKEN", raising=False)

    result = hubspot_service.log_outreach(
        "@arcadiaeats", "Arcadia Eats", "Instagram", "Sakura Bakery",
        "Free tasting + $100 sponsored post", "Hey @arcadiaeats! ...",
    )

    assert result["logged"] is False
    assert result["contact_id"] is None
    assert "not configured" in result["reason"].lower()


def test_log_outreach_creates_contact_and_note(monkeypatch):
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "fake-token-for-test")
    monkeypatch.setattr(hubspot_service, "_find_contact_by_handle", lambda handle: None)
    monkeypatch.setattr(hubspot_service, "_upsert_creator_contact", lambda *a, **k: "contact_123")
    monkeypatch.setattr(hubspot_service, "_attach_outreach_note", lambda *a, **k: True)

    result = hubspot_service.log_outreach(
        "@arcadiaeats", "Arcadia Eats", "Instagram", "Sakura Bakery",
        "Free tasting + $100 sponsored post", "Hey @arcadiaeats! ...",
    )

    assert result == {"logged": True, "contact_id": "contact_123", "reason": None}


def test_log_outreach_reuses_existing_contact(monkeypatch):
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "fake-token-for-test")
    calls = {"search": 0}

    def fake_find(handle):
        calls["search"] += 1
        return "existing_456"

    monkeypatch.setattr(hubspot_service, "_find_contact_by_handle", fake_find)
    monkeypatch.setattr(hubspot_service, "_upsert_creator_contact",
                         lambda handle, name, platform: hubspot_service._find_contact_by_handle(handle))
    monkeypatch.setattr(hubspot_service, "_attach_outreach_note", lambda *a, **k: True)

    result = hubspot_service.log_outreach(
        "@arcadiaeats", "Arcadia Eats", "Instagram", "Sakura Bakery", "offer", "message",
    )

    assert result["contact_id"] == "existing_456"
    assert calls["search"] == 1


def test_log_outreach_survives_contact_creation_failure(monkeypatch):
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "fake-token-for-test")
    monkeypatch.setattr(hubspot_service, "_upsert_creator_contact", lambda *a, **k: None)

    result = hubspot_service.log_outreach(
        "@arcadiaeats", "Arcadia Eats", "Instagram", "Sakura Bakery", "offer", "message",
    )

    assert result["logged"] is False
    assert "could not find or create" in result["reason"].lower()


def test_log_outreach_reports_partial_success_when_note_fails(monkeypatch):
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "fake-token-for-test")
    monkeypatch.setattr(hubspot_service, "_upsert_creator_contact", lambda *a, **k: "contact_789")
    monkeypatch.setattr(hubspot_service, "_attach_outreach_note", lambda *a, **k: False)

    result = hubspot_service.log_outreach(
        "@arcadiaeats", "Arcadia Eats", "Instagram", "Sakura Bakery", "offer", "message",
    )

    assert result["logged"] is True
    assert result["contact_id"] == "contact_789"
    assert "note" in result["reason"].lower()


def test_log_outreach_never_raises_on_unexpected_failure(monkeypatch):
    """Even if something totally unexpected blows up inside the HubSpot
    call chain (not just a plain httpx.HTTPError), log_outreach must
    degrade gracefully rather than raise -- CRM logging must never break
    the outreach workflow it's attached to."""
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "fake-token-for-test")

    def _raise(*args, **kwargs):
        raise ConnectionError("simulated network failure")

    monkeypatch.setattr(hubspot_service, "_upsert_creator_contact", _raise)

    result = hubspot_service.log_outreach("@x", "X", "Instagram", "Biz", "offer", "msg")

    assert result["logged"] is False
    assert "unexpected hubspot error" in result["reason"].lower()
