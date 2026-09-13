"""MCP tools for turning raw business input into structured marketing data."""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.services import business_store, marketing_service


class BusinessInput(BaseModel):
    business_name: str = Field(..., description="The business's name, e.g. 'Sakura Bakery'")
    business_type: str = Field(..., description="What kind of business it is, e.g. 'Korean bakery'")
    location: str = Field(..., description="City and state, e.g. 'Arcadia, CA'")
    description: str = Field("", description="A short free-text description of what the business sells or does")
    target_audience: str = Field("", description="Who the business wants to reach, e.g. '18-30 year olds'")
    goal: str = Field("", description="The business's marketing goal in plain language")
    budget: int = Field(0, description="Monthly marketing budget in whole dollars")


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
        target_audience, goal, and budget.

        Returns: the structured business profile plus a `business_id` to
        pass into later tool calls.
        """
        analyzed = marketing_service.analyze_business(business.model_dump())
        business_id = business_store.save_business(analyzed)
        return {"business_id": business_id, **analyzed}
