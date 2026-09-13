"""
Google Places API integration.

Used for two things, in priority order:
  1. Validating a business's real Google presence during analyze_business /
     analyze_online_presence (place_id, address, rating, review count,
     whether it has a website) -- geocoding (lat/lng) is a SIDE EFFECT of
     that lookup, not the point of it.
  2. Retaining the resolved coordinates/address on the business record so
     they're available for future local-creator and competitor discovery
     (see `nearby_places`, used today for the competitor list in
     analyze_online_presence).

Every function here degrades to None/[] on ANY failure -- missing key,
network error, zero results, quota exceeded -- so the app keeps working
exactly as before for anyone without a Google Maps key configured. This
mirrors the same fallback pattern as llm_client.py: real data when
available, never a hard dependency.

Uses the Places API (Legacy) REST endpoints directly over plain HTTP
(no google-maps SDK dependency) -- make sure "Places API" is enabled for
your key in Google Cloud Console, not only "Places API (New)".
"""

from __future__ import annotations

import os
from typing import Optional

import httpx

_BASE_URL = "https://maps.googleapis.com/maps/api/place"
_TIMEOUT = 6.0  # seconds -- fail fast so a slow/unreachable API never hangs a demo request


def is_configured() -> bool:
    return bool(os.getenv("GOOGLE_MAPS_API_KEY"))


def _get(path: str, params: dict) -> Optional[dict]:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return None

    try:
        response = httpx.get(
            f"{_BASE_URL}/{path}/json",
            params={**params, "key": api_key},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    status = data.get("status")
    if status not in ("OK", "ZERO_RESULTS"):
        return None
    return data


def lookup_business(business_name: str, location: str, business_type: str = "") -> Optional[dict]:
    """Find and validate a business's real Google Places listing.

    Returns None if Places isn't configured, the business can't be found,
    or any request fails -- callers should treat this as "no real data
    available" and keep using their existing (simulated) fields.
    """
    query = f"{business_name} {business_type} {location}".strip()
    find_result = _get("findplacefromtext", {
        "input": query,
        "inputtype": "textquery",
        "fields": "place_id,name,formatted_address,geometry",
    })
    if not find_result or not find_result.get("candidates"):
        return None

    candidate = find_result["candidates"][0]
    place_id = candidate.get("place_id")
    if not place_id:
        return None

    details_result = _get("details", {
        "place_id": place_id,
        "fields": "name,formatted_address,geometry,rating,user_ratings_total,"
                   "website,business_status,opening_hours",
    })
    details = (details_result or {}).get("result", {})

    location_data = (details.get("geometry") or candidate.get("geometry", {})).get("location", {})

    return {
        "google_place_id": place_id,
        "google_verified": True,
        "formatted_address": details.get("formatted_address") or candidate.get("formatted_address"),
        "latitude": location_data.get("lat"),
        "longitude": location_data.get("lng"),
        "google_rating": details.get("rating"),
        "google_review_count": details.get("user_ratings_total"),
        "has_website": bool(details.get("website")),
        "business_status": details.get("business_status", "OPERATIONAL"),
        "has_hours_listed": "opening_hours" in details,
    }


def nearby_places(
    latitude: float,
    longitude: float,
    keyword: str,
    exclude_place_id: Optional[str] = None,
    radius_meters: int = 3218,  # ~2 miles
    max_results: int = 6,
) -> list[dict]:
    """Find real nearby businesses matching `keyword` -- used to surface
    actual local competitors. Returns [] if unavailable for any reason."""
    if latitude is None or longitude is None:
        return []

    result = _get("nearbysearch", {
        "location": f"{latitude},{longitude}",
        "radius": radius_meters,
        "keyword": keyword,
    })
    if not result:
        return []

    places = []
    for place in result.get("results", []):
        if place.get("place_id") == exclude_place_id:
            continue
        places.append({
            "name": place.get("name"),
            "place_id": place.get("place_id"),
            "rating": place.get("rating"),
            "user_ratings_total": place.get("user_ratings_total"),
            "vicinity": place.get("vicinity"),
        })
        if len(places) >= max_results:
            break
    return places
