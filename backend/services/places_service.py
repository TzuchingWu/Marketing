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


def _city_state_from_formatted_address(formatted_address: str) -> str:
    """Google's formatted_address is typically "STREET, CITY, STATE ZIP,
    COUNTRY" -- reduce that to a plain "City, ST" string matching the
    format the rest of the app (and scoring's city-adjacency logic)
    expects, rather than accidentally treating the street address as the
    "city" (which naive comma-splitting would do)."""
    if not formatted_address:
        return ""
    parts = [p.strip() for p in formatted_address.split(",") if p.strip()]
    if parts and parts[-1].upper() in ("USA", "UNITED STATES", "US"):
        parts = parts[:-1]
    if len(parts) < 2:
        return formatted_address
    city = parts[-2]
    state = (parts[-1].split() or [parts[-1]])[0]
    return f"{city}, {state}"


def get_place_details(place_id: str) -> Optional[dict]:
    """Fetch full details for an ALREADY-KNOWN place_id (e.g. one the user
    explicitly picked from a disambiguation list) -- skips the fuzzy
    find-by-text step entirely, so it can't drift to a different business
    than the one actually selected."""
    details_result = _get("details", {
        "place_id": place_id,
        "fields": "name,formatted_address,geometry,rating,user_ratings_total,"
                   "website,business_status,opening_hours,types",
    })
    details = (details_result or {}).get("result", {})
    if not details:
        return None

    location_data = (details.get("geometry") or {}).get("location", {})
    formatted_address = details.get("formatted_address", "")

    return {
        "google_place_id": place_id,
        "google_verified": True,
        "business_name": details.get("name"),
        "formatted_address": formatted_address,
        "location": _city_state_from_formatted_address(formatted_address),
        "latitude": location_data.get("lat"),
        "longitude": location_data.get("lng"),
        "google_rating": details.get("rating"),
        "google_review_count": details.get("user_ratings_total"),
        "has_website": bool(details.get("website")),
        "business_status": details.get("business_status", "OPERATIONAL"),
        "has_hours_listed": "opening_hours" in details,
        "google_types": details.get("types", []),
    }


def lookup_business(business_name: str, location: str, business_type: str = "") -> Optional[dict]:
    """Find and validate a business's real Google Places listing by fuzzy
    name/type/location match (single best guess -- use search_businesses
    instead when the caller needs to disambiguate between multiple
    same-named results rather than silently picking the top one).

    Returns None if Places isn't configured, the business can't be found,
    or any request fails -- callers should treat this as "no real data
    available" and keep using their existing (simulated) fields.
    """
    query = f"{business_name} {business_type} {location}".strip()
    find_result = _get("findplacefromtext", {
        "input": query,
        "inputtype": "textquery",
        "fields": "place_id",
    })
    if not find_result or not find_result.get("candidates"):
        return None

    place_id = find_result["candidates"][0].get("place_id")
    if not place_id:
        return None

    return get_place_details(place_id)


def search_businesses(query: str, location_hint: str = "", max_results: int = 5) -> list[dict]:
    """Search for businesses matching a free-text query, returning
    MULTIPLE candidates (unlike lookup_business's single best guess) --
    used to disambiguate when a business name isn't unique, e.g. multiple
    real locations of the same chain/franchise.

    Returns [] if Places isn't configured or the search fails/finds
    nothing.
    """
    full_query = f"{query} {location_hint}".strip()
    result = _get("textsearch", {"query": full_query})
    if not result:
        return []

    candidates = []
    for place in result.get("results", [])[:max_results]:
        location_data = (place.get("geometry") or {}).get("location", {})
        candidates.append({
            "place_id": place.get("place_id"),
            "name": place.get("name"),
            "formatted_address": place.get("formatted_address"),
            "rating": place.get("rating"),
            "user_ratings_total": place.get("user_ratings_total"),
            "business_status": place.get("business_status", "OPERATIONAL"),
            "latitude": location_data.get("lat"),
            "longitude": location_data.get("lng"),
            "types": place.get("types", []),
        })
    return candidates


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
