"""MCP tools for finding, scoring, and ranking creators."""

from __future__ import annotations

from backend.services import creator_cache, creator_service, marketing_service, scoring_service, web_search_service, youtube_service
from backend.services.business_store import get_business
from backend.data.creator_provider import get_provider


def _score_and_rank_real_creators(business: dict, creators: list[dict]) -> list[dict]:
    """Shared by search_real_creators and search_youtube_creators: apply
    the same deterministic Fit Score + LLM explanation to a list of
    externally-discovered (non-demo-dataset) creators, best fit first."""
    # The search term used to find these (e.g. "karaoke") is often more
    # specific than the business's own normalized category ("nightlife")
    # -- great for finding relevant real accounts, but content_relevance
    # scoring only matches on literal string overlap, so without this a
    # perfectly relevant creator can score a flat content_relevance of 0
    # just because "karaoke" != "nightlife" as strings. Tag every result
    # with the business's own category/sub_category too, regardless of
    # what search term was actually used to find it.
    extra_categories = [c for c in (business.get("business_category"), business.get("sub_category")) if c]

    results = []
    for creator in creators:
        enriched = {**creator, "categories": list({*creator.get("categories", []), *extra_categories})}
        score_result = scoring_service.calculate_creator_fit_score(business, enriched)
        score_result["explanation"] = marketing_service.explain_creator_fit(business, enriched, score_result)
        results.append({**enriched, **score_result})
    # Fit score is always the primary sort key ("fit over fame"). Real
    # follower count only matters as a tie-breaker -- and for
    # externally-discovered creators, ties are common: most of the score
    # inputs (engagement, audience, local %) are genuinely unknown and
    # fall back to the same neutral default for everyone, so without a
    # tie-breaker "top creators" would come back in arbitrary API order.
    results.sort(key=lambda r: (r["fit_score"], r.get("followers") or 0), reverse=True)
    creator_cache.cache_creators(results)  # so generate_campaign etc. can resolve these ids later
    return results


def register(mcp) -> None:
    @mcp.tool()
    def search_creators(
        category: str,
        location: str,
        target_audience: str = "",
        max_results: int = 10,
    ) -> list[dict]:
        """
        Search for candidate creators who could be a good marketing fit for
        a business, based on content category and geographic location.

        Use this AFTER analyze_business, once you know the business's
        category and location. This returns *candidates only* -- it does
        not compute a fit score. Follow up with analyze_creator or
        rank_creators to actually score them against the business.

        If very few creators match the category exactly, this tool
        automatically widens the search rather than returning an empty list.

        Input: category (e.g. "food"), location (e.g. "Arcadia, CA"),
        target_audience (free text, optional), max_results (default 10).

        Returns: a list of creator profile objects (demo/simulated data).
        """
        return creator_service.search_creators(category, location, target_audience, max_results)

    @mcp.tool()
    def analyze_creator(creator_id: str, business_id: str) -> dict:
        """
        Compute a deterministic Creator Fit Score (0-100) for one specific
        creator against one specific business, with a full breakdown across
        locality, audience match, content relevance, engagement, and budget
        fit, plus a natural-language explanation of the result.

        Use this to evaluate an individual creator candidate returned by
        search_creators. Requires a business_id from a prior analyze_business
        call.

        Returns: fit_score, score_breakdown (5 components), strengths,
        weaknesses, recommendation label, and a short explanation.
        """
        result = creator_service.analyze_creator(creator_id, business_id)
        if result is None:
            raise ValueError(f"Could not find creator '{creator_id}' or business '{business_id}'.")

        business = get_business(business_id)
        creator = creator_cache.get_cached_creator(creator_id) or get_provider().get_creator(creator_id)
        result["explanation"] = marketing_service.explain_creator_fit(business, creator, result)
        return result

    @mcp.tool()
    def rank_creators(business_id: str, creator_ids: list[str]) -> list[dict]:
        """
        Score and rank a list of candidate creators for one business, best
        fit first, using the same deterministic Creator Fit Score as
        analyze_creator.

        Use this once you have a shortlist of candidate creator_ids (e.g.
        from search_creators) and want a single ranked list rather than
        calling analyze_creator repeatedly and sorting yourself.

        Returns: a list of fit-score results ordered from best to worst
        match, ready to hand to generate_campaign.
        """
        business = get_business(business_id)
        if business is None:
            raise ValueError(f"Could not find business '{business_id}'. Call analyze_business first.")

        results = creator_service.rank_creators(business_id, creator_ids)
        if not results:
            return []

        # Only the top handful ever get shown to the user (generate_campaign
        # and the UI both only use the first ~5) -- generating an LLM
        # explanation for every candidate just adds latency for sentences
        # nobody reads. `results` is already sorted best-first.
        max_llm_explanations = 5
        provider = get_provider()
        for i, result in enumerate(results):
            creator = creator_cache.get_cached_creator(result["creator_id"]) or provider.get_creator(result["creator_id"])
            result["explanation"] = marketing_service.explain_creator_fit(
                business, creator, result, use_llm=i < max_llm_explanations
            )
        return results

    @mcp.tool()
    def search_real_creators(
        business_id: str,
        category: str,
        location: str,
        target_audience: str = "",
        max_results: int = 5,
    ) -> list[dict]:
        """
        Search the live web (via OpenAI web search) for REAL, currently
        active creators -- not the demo dataset -- matching a category and
        location, then score and rank them the same way as rank_creators.

        Use this ONLY when the user explicitly wants real creators looked
        up live (e.g. "find me actual accounts", "who's real"), not as
        part of the normal fast/free recommend flow -- this is a slower,
        real-cost LLM+web-search call, similar in spirit to
        generate_video_ad's opt-in nature.

        IMPORTANT: web search can only verify a creator's platform,
        handle, name, bio, and (sometimes) an approximate follower count.
        It cannot verify engagement rate, audience demographics, or
        collaboration cost -- those come back as unknown and the fit
        score treats unknowns as neutral rather than fabricating specific
        numbers. Each result is tagged `"source": "web_search"` and
        `"verified"` (whether a source URL was found) so callers can
        clearly label this as different from the demo dataset.

        Requires OPEN_AI_WEBSEARCH_API_KEY to be configured; returns an
        empty list (not an error) if it isn't set or the search finds
        nothing -- callers should fall back to search_creators.

        Input: business_id (from analyze_business), category, location,
        target_audience (optional), max_results (default 5).

        Returns: a list of fit-score results (same shape as rank_creators)
        plus followers, bio, source_url, verified -- ordered best fit first.
        """
        business = get_business(business_id)
        if business is None:
            raise ValueError(f"Could not find business '{business_id}'. Call analyze_business first.")

        creators = web_search_service.find_real_creators(category, location, target_audience, max_results)
        if not creators:
            return []
        return _score_and_rank_real_creators(business, creators)

    @mcp.tool()
    def search_youtube_creators(
        business_id: str,
        category: str,
        location: str = "",
        max_results: int = 5,
    ) -> list[dict]:
        """
        Search the real YouTube Data API for REAL, currently active
        channels matching a category (optionally narrowed by location
        text), then score and rank them the same way as rank_creators.

        Use this ONLY when the user explicitly wants real YouTube
        creators looked up live, not as part of the normal fast/free
        recommend flow -- like search_real_creators, this is a real API
        call with its own quota, kept as a deliberate opt-in action.

        Unlike search_real_creators (which asks an LLM to interpret
        generic web search results), this hits YouTube's own API
        directly -- subscriber count comes back exact and verified
        straight from the platform, not an LLM's guess. It still can't
        give engagement rate, audience demographics, or collaboration
        cost (not public API data), so those stay unknown and the fit
        score treats unknowns as neutral rather than fabricating numbers.
        Each result is tagged `"source": "youtube_api"` and
        `"verified": true`.

        Requires YOUTUBE_API to be configured (a Google Cloud API key
        with the YouTube Data API v3 enabled); returns an empty list
        (not an error) if it isn't set or the search finds nothing --
        callers should fall back to search_creators.

        Input: business_id (from analyze_business), category, location
        (optional -- narrows the search query text, YouTube has no true
        geographic filter), max_results (default 5).

        Returns: a list of fit-score results (same shape as rank_creators)
        plus followers (real subscriber count), bio, source_url, verified
        -- ordered best fit first, not by subscriber count.
        """
        business = get_business(business_id)
        if business is None:
            raise ValueError(f"Could not find business '{business_id}'. Call analyze_business first.")

        creators = youtube_service.search_creators(category, location, max_results)
        if not creators:
            return []
        return _score_and_rank_real_creators(business, creators)

    @mcp.tool()
    def find_and_rank_creators(
        business_id: str,
        category: str,
        location: str,
        target_audience: str = "",
        max_results: int = 5,
    ) -> dict:
        """
        The preferred way to find creators for the main recommend flow:
        searches REAL creators first (YouTube Data API + OpenAI web
        search, combined and deduplicated) whenever those are configured,
        and only falls back to the demo dataset if no real-creator keys
        are set or a real search comes back empty. Always returns
        scored, ranked results either way.

        Use this INSTEAD of calling search_creators + rank_creators
        separately for the primary "find my creators" action -- it
        automatically prefers real data when available, with a fully
        reliable offline fallback so the workflow never breaks.

        Input: business_id (from analyze_business), category, location,
        target_audience (optional), max_results (default 5).

        Returns: {"creators": [...same shape as rank_creators, plus
        "source"/"verified" on real ones...], "source": "real" | "demo"}
        """
        business = get_business(business_id)
        if business is None:
            raise ValueError(f"Could not find business '{business_id}'. Call analyze_business first.")

        # Prefer the business's own sub_category as the actual search term
        # when it's more specific than the broad category passed in (e.g.
        # "karaoke bar" vs "nightlife") -- a vague category returns
        # generic results with no real topical connection to the business.
        sub_category = business.get("sub_category")
        search_term = sub_category if sub_category and sub_category != category else category

        # Try the location-qualified search first (most targeted, and the
        # common case where it's enough). Only ALSO run a location-less
        # search if that came back thin -- a small/ambiguous city name
        # (e.g. "San Gabriel", also a common Spanish given name) can drag
        # a location-qualified query toward unrelated results, and a
        # sparse result set is the main symptom of that. This keeps the
        # common case to one API call per source instead of always two,
        # since each real search is a real network call with its own
        # latency/failure risk.
        real_creators: list[dict] = []
        if web_search_service.is_configured():
            real_creators += web_search_service.find_real_creators(search_term, location, target_audience, max_results)
        if youtube_service.is_configured():
            real_creators += youtube_service.search_creators(search_term, location, max_results)

        if len(real_creators) < max_results:
            if web_search_service.is_configured():
                real_creators += web_search_service.find_real_creators(search_term, "", target_audience, max_results)
            if youtube_service.is_configured():
                real_creators += youtube_service.search_creators(search_term, "", max_results)

        if real_creators:
            # Same creator can legitimately turn up in both the broad and
            # location-qualified searches above -- when it does, keep
            # whichever occurrence actually carries a location (needed
            # for locality scoring to give it fair credit) over one that
            # came back from the location-less search with location="".
            by_key: dict[tuple[str, str], dict] = {}
            for creator in real_creators:
                key = (creator.get("platform", "").lower(), creator.get("handle", "").lower().lstrip("@"))
                existing = by_key.get(key)
                if existing is None or (not existing.get("location") and creator.get("location")):
                    by_key[key] = creator
            deduped = list(by_key.values())

            ranked = _score_and_rank_real_creators(business, deduped)[:max_results]
            if ranked:
                return {"creators": ranked, "source": "real"}

        # Fallback: the always-available demo dataset.
        candidates = creator_service.search_creators(category, location, target_audience, max_results * 2)
        candidate_lookup = {c["id"]: c for c in candidates}
        ranked_demo = creator_service.rank_creators(business_id, list(candidate_lookup.keys()))[:max_results]

        max_llm_explanations = 5
        results = []
        for i, r in enumerate(ranked_demo):
            creator = candidate_lookup.get(r["creator_id"], {})
            r["explanation"] = marketing_service.explain_creator_fit(business, creator, r, use_llm=i < max_llm_explanations)
            results.append({**creator, **r})
        return {"creators": results, "source": "demo"}
