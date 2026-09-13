"""
HubSpot CRM integration.

Used for exactly one thing: recording that a business reached out to a
creator, as a CRM contact + note, so outreach status across many
creators can be tracked in one place instead of disappearing once this
session ends. This module never sends anything on its own -- it only
logs that a human decided to reach out, consistent with generate_outreach
never auto-sending messages either.

Auth is a HubSpot Service Key / Private App access token (a static
Bearer token scoped to one HubSpot account) -- not OAuth, since this is
a single-account integration, not a multi-tenant app.

Every function here degrades to None/False on ANY failure -- missing
token, network error, bad scopes, HubSpot API error -- so the rest of
the app never depends on this working. Same fallback pattern as
places_service.py and llm_client.py.
"""

from __future__ import annotations

import os
import time
from typing import Optional

import httpx

_BASE_URL = "https://api.hubapi.com"
_TIMEOUT = 6.0

# HubSpot's standard built-in association type id for "note to contact".
_NOTE_TO_CONTACT_ASSOCIATION_TYPE_ID = 202


def is_configured() -> bool:
    return bool(os.getenv("HUBSPOT_ACCESS_TOKEN"))


def _headers() -> Optional[dict]:
    token = os.getenv("HUBSPOT_ACCESS_TOKEN")
    if not token:
        return None
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _find_contact_by_handle(handle: str) -> Optional[str]:
    """Look up an existing contact for this creator by handle (stored in
    the `firstname` property, since our creators have no email address --
    the field HubSpot contacts otherwise dedupe on)."""
    headers = _headers()
    if not headers:
        return None

    try:
        response = httpx.post(
            f"{_BASE_URL}/crm/v3/objects/contacts/search",
            headers=headers,
            json={
                "filterGroups": [{"filters": [
                    {"propertyName": "firstname", "operator": "EQ", "value": handle}
                ]}],
                "properties": ["firstname"],
                "limit": 1,
            },
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        return results[0]["id"] if results else None
    except (httpx.HTTPError, ValueError, KeyError, IndexError):
        return None


def _upsert_creator_contact(handle: str, creator_name: str, platform: str) -> Optional[str]:
    """Find or create a HubSpot contact representing this creator.
    Returns the contact id, or None on failure."""
    headers = _headers()
    if not headers:
        return None

    existing_id = _find_contact_by_handle(handle)
    properties = {
        "firstname": handle,
        "lastname": creator_name or "(via OUTTHERE)",
        "company": f"{platform} Creator" if platform else "Content Creator",
    }

    try:
        if existing_id:
            response = httpx.patch(
                f"{_BASE_URL}/crm/v3/objects/contacts/{existing_id}",
                headers=headers, json={"properties": properties}, timeout=_TIMEOUT,
            )
            response.raise_for_status()
            return existing_id

        response = httpx.post(
            f"{_BASE_URL}/crm/v3/objects/contacts",
            headers=headers, json={"properties": properties}, timeout=_TIMEOUT,
        )
        response.raise_for_status()
        return response.json().get("id")
    except (httpx.HTTPError, ValueError):
        return None


def _attach_outreach_note(contact_id: str, note_body: str) -> bool:
    headers = _headers()
    if not headers:
        return False

    try:
        response = httpx.post(
            f"{_BASE_URL}/crm/v3/objects/notes",
            headers=headers,
            json={
                "properties": {
                    "hs_note_body": note_body,
                    "hs_timestamp": int(time.time() * 1000),
                },
                "associations": [{
                    "to": {"id": contact_id},
                    "types": [{
                        "associationCategory": "HUBSPOT_DEFINED",
                        "associationTypeId": _NOTE_TO_CONTACT_ASSOCIATION_TYPE_ID,
                    }],
                }],
            },
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        return True
    except httpx.HTTPError:
        return False


def log_outreach(
    creator_handle: str,
    creator_name: str,
    platform: str,
    business_name: str,
    offer: str,
    message: str,
) -> dict:
    """Record an outreach attempt in HubSpot: find-or-create a contact for
    the creator, then attach a note with the offer and message sent.

    Returns {"logged": bool, "contact_id": str | None, "reason": str | None}
    -- never raises, since CRM logging failing should never block the rest
    of the outreach workflow.
    """
    if not is_configured():
        return {"logged": False, "contact_id": None, "reason": "HubSpot not configured"}

    try:
        return _do_log_outreach(creator_handle, creator_name, platform, business_name, offer, message)
    except Exception as exc:
        return {"logged": False, "contact_id": None, "reason": f"Unexpected HubSpot error: {exc}"}


def _do_log_outreach(
    creator_handle: str,
    creator_name: str,
    platform: str,
    business_name: str,
    offer: str,
    message: str,
) -> dict:
    contact_id = _upsert_creator_contact(creator_handle, creator_name, platform)
    if not contact_id:
        return {"logged": False, "contact_id": None, "reason": "Could not find or create HubSpot contact"}

    note_body = (
        f"Outreach sent via OUTTHERE on behalf of {business_name}.\n\n"
        f"Offer: {offer}\n\nMessage:\n{message}"
    )
    note_attached = _attach_outreach_note(contact_id, note_body)

    return {
        "logged": True,
        "contact_id": contact_id,
        "reason": None if note_attached else "Contact saved, but the note could not be attached",
    }
