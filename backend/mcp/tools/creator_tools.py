"""MCP tools for finding, scoring, and ranking creators."""

from __future__ import annotations

from backend.services import creator_service, marketing_service, scoring_service, web_search_service
from backend.services.business_store import get_business
from backend.data.creator_provider import get_provider


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
        creator = get_provider().get_creator(creator_id)
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
            creator = provider.get_creator(result["creator_id"])
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

        results = []
        for creator in creators:
            score_result = scoring_service.calculate_creator_fit_score(business, creator)
            score_result["explanation"] = marketing_service.explain_creator_fit(business, creator, score_result)
            results.append({
                **creator,
                **score_result,
            })

        results.sort(key=lambda r: r["fit_score"], reverse=True)
        return results
