"""MCP tools for turning raw business input into structured marketing data,
and for finding a real business on Google Places before analyzing it."""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.services import business_store, marketing_service, places_service


class BusinessInput(BaseModel):
    business_name: str = Field(..., description="The business's name, e.g. 'Sakura Bakery'")
    business_type: str = Field(..., description="What kind of business it is, e.g. 'Korean bakery'")
    location: str = Field(..., description="City and state, e.g. 'Arcadia, CA'")
    description: str = Field("", description="A short free-text description of what the business sells or does")
    target_audience: str = Field("", description="Who the business wants to reach, e.g. '18-30 year olds'")
    goal: str = Field("", description="The business's marketing goal in plain language")
    budget: int = Field(0, description="Monthly marketing budget in whole dollars")
    place_id: str | None = Field(
        None,
        description=(
            "A Google Places place_id, if the caller already knows exactly which real "
            "business this is (e.g. the user picked it from find_real_business's candidate "
            "list). When set, skips fuzzy name matching and fetches that listing directly."
        ),
    )


def register(mcp) -> None:
    @mcp.tool()
    def analyze_business(business: BusinessInput) -> dict:
        """
        Turn a small business owner's raw input into structured marketing
        information: business category, target age range, interests, and
        marketing goal.

        Use this FIRST, before searching for creators -- every other tool
        in this server (search_creators, analyze_creator, rank_creators,
        generate_campaign) needs the business_id this tool returns.

        Input: business_name, business_type, location, description,
        target_audience, goal, budget, and optional place_id (pass this
        when the business was already confirmed via find_real_business,
        to fetch that exact listing instead of fuzzy-matching by name).

        Returns: the structured business profile plus a `business_id` to
        pass into later tool calls.
        """
        data = business.model_dump()
        place_id = data.pop("place_id", None)
        analyzed = marketing_service.analyze_business(data, place_id=place_id)
        business_id = business_store.save_business(analyzed)
        return {"business_id": business_id, **analyzed}

    @mcp.tool()
    def find_real_business(query: str, location_hint: str = "") -> dict:
        """
        Search Google Places for real businesses matching a name (and
        optional location hint), for disambiguation BEFORE calling
        analyze_business -- e.g. when a business name isn't unique (a
        chain with multiple real locations) and the user needs to confirm
        which one they mean.

        Use this when starting from unstructured free text (e.g. "I am
        Ace Karaoke, I want to target a younger audience") instead of a
        fully-filled-out business form: search for the name first, and if
        multiple real locations come back, ask the user which one before
        calling analyze_business with that specific place_id.

        Requires GOOGLE_MAPS_API_KEY to be configured; returns
        status="not_configured" if it isn't, and status="not_found" if
        the search comes back empty (both cases: fall back to asking the
        user for their business details directly, or proceed with
        unverified demo data).

        Input: query (the business name to search for), location_hint
        (optional city/area to narrow the search).

        Returns: {"status": "found_one" | "found_multiple" | "not_found" |
        "not_configured", "candidates": [{place_id, name,
        formatted_address, rating, user_ratings_total, ...}]}
        """
        if not places_service.is_configured():
            return {"status": "not_configured", "candidates": []}

        candidates = places_service.search_businesses(query, location_hint)
        if not candidates:
            return {"status": "not_found", "candidates": []}
        if len(candidates) == 1:
            return {"status": "found_one", "candidates": candidates}
        return {"status": "found_multiple", "candidates": candidates}

    @mcp.tool()
    def discover_business_from_text(free_text: str) -> dict:
        """
        The entry point for "general search" mode: given a single free-text
        request like "I am Ace Karaoke, I want to target a younger
        audience", extract the business name and marketing intent, then
        search Google Places for real matching businesses in one call.

        Use this INSTEAD of asking the user to fill out a structured form
        -- it combines intent extraction (business name, goal, target
        audience) with find_real_business's disambiguation search. If
        status is "found_multiple", show the candidates and ask the user
        which real business they meant before calling analyze_business
        with that place_id; if "found_one", you can proceed directly.

        Input: free_text (the user's raw request).

        Returns: {"extracted": {business_name, location_hint, goal,
        target_audience}, "status": "found_one" | "found_multiple" |
        "not_found" | "not_configured", "candidates": [...]}
        """
        extracted = marketing_service.extract_business_intent(free_text)

        if not places_service.is_configured():
            return {"extracted": extracted, "status": "not_configured", "candidates": []}

        candidates = places_service.search_businesses(extracted["business_name"], extracted["location_hint"])
        if not candidates:
            status = "not_found"
        elif len(candidates) == 1:
            status = "found_one"
        else:
            status = "found_multiple"

        return {"extracted": extracted, "status": status, "candidates": candidates}
