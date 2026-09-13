"""MCP tools for CRM logging (HubSpot)."""

from __future__ import annotations

from backend.services import hubspot_service


def register(mcp) -> None:
    @mcp.tool()
    def log_creator_outreach(
        creator_handle: str,
        creator_name: str,
        platform: str,
        business_name: str,
        offer: str,
        message: str,
    ) -> dict:
        """
        Record that a business reached out to a creator, by creating or
        updating a HubSpot CRM contact for that creator and attaching a
        note with the offer and outreach message sent.

        Use this AFTER generate_outreach, once the business owner has
        decided to actually send the message -- this does NOT send
        anything itself, it only logs that outreach happened, so status
        across many creators can be tracked in one place (HubSpot)
        instead of being lost after this session ends.

        Requires a HubSpot Service Key / Private App access token to be
        configured (HUBSPOT_ACCESS_TOKEN). If it isn't set, or the
        HubSpot API call fails for any reason, this returns
        {"logged": false, "reason": "..."} rather than raising -- CRM
        logging failing should never block or error out the rest of the
        workflow.

        Input: creator_handle, creator_name, platform (e.g. "Instagram"),
        business_name, offer, message (the outreach text that was sent).

        Returns: {"logged": bool, "contact_id": str | None, "reason": str | None}
        """
        return hubspot_service.log_outreach(
            creator_handle, creator_name, platform, business_name, offer, message
        )
