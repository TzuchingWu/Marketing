"""MCP tools for outreach message and campaign generation."""

from __future__ import annotations

import hashlib

from pydantic import BaseModel, Field

from backend.services import creator_service, marketing_service
from backend.services.business_store import get_business


class OutreachBusiness(BaseModel):
    name: str = Field(..., description="Business name")
    description: str = Field("", description="Short description of the business")
    goal: str = Field("", description="The business's marketing goal")
    location: str = Field("", description="Business location, e.g. 'Arcadia, CA'")


class OutreachCreator(BaseModel):
    handle: str = Field(..., description="Creator's @handle")
    name: str = Field("", description="Creator's display name")
    category: list[str] = Field(default_factory=list, description="Creator's content categories")
    location: str = Field("", description="Creator's location")


def register(mcp) -> None:
    @mcp.tool()
    def generate_outreach(
        business: OutreachBusiness,
        creator: OutreachCreator,
        offer: str,
        tone: str = "friendly",
    ) -> dict:
        """
        Generate a short, personalized outreach message for a business to
        send to a specific creator, referencing what the creator actually
        posts about and a concrete collaboration offer.

        Use this AFTER the user has picked a creator they want to reach
        out to. Never sends anything automatically -- the message is
        returned for the business owner to review, edit, and send
        themselves.

        Input: business (name, description, goal, location), creator
        (handle, name, category, location), offer (e.g. "Free tasting +
        $100 sponsored post"), and optional tone (default "friendly").

        Returns: { "message": "<the generated outreach text>" }
        """
        message = marketing_service.generate_outreach(
            business.model_dump(), creator.model_dump(), offer, tone
        )
        return {"message": message}

    @mcp.tool()
    def generate_campaign(
        business_id: str,
        creator_ids: list[str],
        budget: int | None = None,
        goal: str | None = None,
    ) -> dict:
        """
        Build a complete campaign plan (name, strategy, content ideas,
        offer, budget allocation, and expected reach) from a shortlist of
        creators already scored against a business.

        Use this LAST in the workflow, after rank_creators has produced an
        ordered shortlist -- pass the business_id and the creator_ids you
        want included (typically the top 3-5 from rank_creators). Budget
        allocation greedily fills the budget with the highest-fit creators
        first; it will not overspend the business's budget.

        Input: business_id (from analyze_business), creator_ids (list),
        optional budget override, optional goal override.

        Returns: campaign_name, objective, budget, strategy, creators
        (with spend), content_ideas, offers, estimated_spend, expected_reach.
        """
        business = get_business(business_id)
        if business is None:
            raise ValueError(f"Could not find business '{business_id}'. Call analyze_business first.")

        creators = creator_service.get_creators_with_fit(business_id, creator_ids)
        if not creators:
            raise ValueError("None of the provided creator_ids could be found.")

        effective_budget = budget if budget is not None else business.get("budget", 0)
        effective_goal = goal or business.get("marketing_goal", "local_customer_acquisition")

        return marketing_service.generate_campaign(business, creators, effective_budget, effective_goal)

    @mcp.tool()
    def analyze_online_presence(business_id: str) -> dict:
        """
        Estimate a business's current online/discovery visibility (Google
        presence, social presence, content consistency) and suggest ways
        to improve it before or alongside a creator campaign.

        This runs on simulated/demo signals derived from the business
        profile, not a live web crawl -- it's meant to contextualize *why*
        creator marketing helps, not to be a real SEO audit.

        Input: business_id (from analyze_business).

        Returns: google_presence, social_presence, content_consistency,
        overall_visibility (all 0-100), and a list of recommendations.
        """
        business = get_business(business_id)
        if business is None:
            raise ValueError(f"Could not find business '{business_id}'. Call analyze_business first.")

        # Deterministic pseudo-signal so repeated calls for the same
        # business always return the same demo numbers.
        seed = int(hashlib.sha256(business.get("business_name", "").encode()).hexdigest(), 16)
        google_presence = 40 + (seed % 45)
        social_presence = 30 + ((seed // 7) % 50)
        content_consistency = 25 + ((seed // 13) % 55)
        overall_visibility = round((google_presence + social_presence + content_consistency) / 3)

        recommendations = []
        if google_presence < 60:
            recommendations.append("Claim and complete your Google Business Profile with current hours and photos")
        if social_presence < 60:
            recommendations.append("Post consistently on at least one platform your target audience actually uses")
        if content_consistency < 60:
            recommendations.append("Establish a regular posting cadence instead of sporadic updates")
        recommendations.append("Partner with locally-relevant creators to reach audiences your own channels can't")

        return {
            "google_presence": google_presence,
            "social_presence": social_presence,
            "content_consistency": content_consistency,
            "overall_visibility": overall_visibility,
            "recommendations": recommendations,
        }
