"""
OUTTHERE MCP server.

Exposes business analysis, creator search/scoring/ranking, outreach
generation, and campaign generation as MCP tools so an AI agent (or any
MCP-compatible client, e.g. Claude Desktop) can drive the whole
recommendation workflow by calling tools rather than the app hardcoding
the pipeline.

Run directly for local stdio testing:
    python -m backend.mcp.server
"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp import FastMCP

from backend.mcp.tools import business_tools, creator_tools, campaign_tools, crm_tools, video_tools

mcp = FastMCP(
    "outthere",
    instructions=(
        "OUTTHERE helps small businesses find the RIGHT local content creators to "
        "market with -- fit over fame, not just follower count. Typical workflow: "
        "1) analyze_business to structure the business's info, "
        "2) search_creators to find candidates, "
        "3) analyze_creator or rank_creators to score them (deterministically), "
        "4) generate_campaign to build a plan from the top creators, "
        "5) generate_video_script to turn one of its content ideas into a filmable script, "
        "6) generate_video_ad ONLY if the owner explicitly wants a real AI-generated video clip "
        "(slow async job, real cost -- never call this automatically), "
        "7) generate_outreach once the user picks a creator to contact, "
        "8) log_creator_outreach once the owner actually sends it, to track status in HubSpot."
    ),
)

business_tools.register(mcp)
creator_tools.register(mcp)
campaign_tools.register(mcp)
crm_tools.register(mcp)
video_tools.register(mcp)


if __name__ == "__main__":
    mcp.run()
