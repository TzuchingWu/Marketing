"""
The AI agent orchestrator -- drives the discovery workflow through the
shared MCP ClientSession (see client_manager.py), exactly like Claude
Desktop or any other MCP host would drive a tool-using agent. This is
what makes MCP central to the architecture rather than a README mention:
nothing here calls the service layer directly, every step goes
analyze_business -> search_creators -> rank_creators -> generate_campaign
through real MCP tool_call requests.

Two modes:
  - Agentic (requires ANTHROPIC_API_KEY): Claude sees the MCP tool list
    and decides which tools to call and in what order/args, based on the
    business input. We just relay tool_use blocks to the MCP server.
  - Scripted fallback (no API key, or the LLM call fails): the same
    workflow is driven by fixed Python control flow instead of an LLM
    choosing it, but every step still goes through the same MCP
    ClientSession.call_tool(), so the demo keeps working offline.

Either way, the full sequence of MCP tool calls is recorded and returned
as an activity log for the frontend's "AI Agent Activity" panel.
"""

from __future__ import annotations

import json
import os
from typing import Any

from . import client_manager

AGENT_SYSTEM_PROMPT = (
    "You are the OUTTHERE marketing agent. A small business owner has described their "
    "business, and you have MCP tools to find them the RIGHT local content creators to "
    "market with -- fit over fame, not just follower count.\n\n"
    "Follow this workflow using the tools available to you: "
    "1) analyze_business first. "
    "2) search_creators using the resulting category/location. "
    "3) rank_creators on the candidate ids search_creators returned, to score them. "
    "4) generate_campaign using business_id and the top 3-5 creator_ids from rank_creators. "
    "Then write a short (2-3 sentence) summary of your recommendation for the business owner. "
    "Do not call generate_outreach yet -- that happens later once the owner picks a creator."
)


def _summarize(tool_name: str, args: dict, parsed: Any) -> str:
    try:
        if tool_name == "analyze_business":
            return f"Understood: {parsed.get('sub_category', parsed.get('business_category', 'business'))} in {parsed.get('location', '')}"
        if tool_name == "search_creators":
            return f"Found {len(parsed)} candidate creator(s)"
        if tool_name == "analyze_creator":
            return f"Evaluated {parsed.get('handle', args.get('creator_id', ''))} -- {parsed.get('fit_score', '?')}/100"
        if tool_name == "rank_creators":
            return (f"Ranked {len(parsed)} creator(s), top match {parsed[0]['handle']} ({parsed[0]['fit_score']}/100)"
                    if parsed else "No creators to rank")
        if tool_name == "generate_campaign":
            return f"Created ${parsed.get('estimated_spend', 0)} campaign reaching ~{parsed.get('expected_reach', 0):,}"
        if tool_name == "generate_outreach":
            return "Drafted personalized outreach message"
        if tool_name == "analyze_online_presence":
            return f"Overall visibility: {parsed.get('overall_visibility', '?')}/100"
    except Exception:
        pass
    return "Done"


async def _call(name: str, args: dict, activity_log: list[dict]) -> Any:
    parsed, is_error = await client_manager.call_tool(name, args)
    activity_log.append({
        "tool": name,
        "input": args,
        "summary": _summarize(name, args, parsed),
        "is_error": is_error,
    })
    return parsed


async def _run_scripted(business_input: dict, activity_log: list[dict]) -> dict:
    """Deterministic fallback workflow -- same MCP tool calls, fixed order."""
    business = await _call("analyze_business", {"business": business_input}, activity_log)
    business_id = business["business_id"]

    candidates = await _call("search_creators", {
        "category": business["business_category"],
        "location": business["location"],
        "target_audience": business_input.get("target_audience", ""),
        "max_results": 10,
    }, activity_log)
    candidate_ids = [c["id"] for c in candidates]

    ranked = await _call("rank_creators", {
        "business_id": business_id,
        "creator_ids": candidate_ids,
    }, activity_log)

    top_ids = [r["creator_id"] for r in ranked[:5]]
    campaign = await _call("generate_campaign", {
        "business_id": business_id,
        "creator_ids": top_ids,
    }, activity_log)

    provider_lookup = {c["id"]: c for c in candidates}
    top_creators = [{**provider_lookup.get(r["creator_id"], {}), **r} for r in ranked[:5]]

    summary = "No strong creator matches were found for this business yet."
    if top_creators:
        summary = (
            f"Based on {business_input['business_name']}'s profile, we found {len(candidates)} candidate "
            f"creators and ranked them by fit. The top match is {top_creators[0]['handle']} at "
            f"{top_creators[0]['fit_score']}/100."
        )

    return {
        "business": business,
        "creators": top_creators,
        "campaign": campaign,
        "agent_summary": summary,
        "mode": "scripted",
    }


async def _run_agentic(business_input: dict, activity_log: list[dict]) -> dict:
    import anthropic

    tools = await client_manager.list_tools()
    anthropic_tools = [
        {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
        for t in tools
        if t.name != "generate_outreach"  # not part of the discovery workflow yet
    ]

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

    messages = [{
        "role": "user",
        "content": f"Here is the business's raw input:\n{json.dumps(business_input, indent=2)}",
    }]

    business_id = None
    ranked = None
    campaign = None
    candidates = []
    final_text = ""

    for _ in range(8):
        response = client.messages.create(
            model=model,
            max_tokens=1200,
            system=AGENT_SYSTEM_PROMPT,
            tools=anthropic_tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            final_text = "".join(b.text for b in response.content if b.type == "text").strip()
            break

        tool_result_blocks = []
        for block in tool_uses:
            parsed = await _call(block.name, block.input, activity_log)

            if block.name == "analyze_business":
                business_id = parsed.get("business_id")
            elif block.name == "search_creators":
                candidates = parsed if isinstance(parsed, list) else candidates
            elif block.name == "rank_creators":
                ranked = parsed if isinstance(parsed, list) else ranked
            elif block.name == "generate_campaign":
                campaign = parsed if isinstance(parsed, dict) else campaign

            tool_result_blocks.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(parsed) if not isinstance(parsed, str) else parsed,
            })
        messages.append({"role": "user", "content": tool_result_blocks})

    if ranked is None or campaign is None:
        # The model didn't finish the workflow within the turn budget --
        # fall back to the deterministic path so the demo still produces
        # a full result. (Fresh activity log: don't mix partial agentic
        # attempts with the scripted run in the UI trace.)
        activity_log.clear()
        return await _run_scripted(business_input, activity_log)

    provider_lookup = {c["id"]: c for c in candidates}
    top_creators = [{**provider_lookup.get(r["creator_id"], {}), **r} for r in ranked[:5]]

    return {
        "business": {"business_id": business_id, **business_input},
        "creators": top_creators,
        "campaign": campaign,
        "agent_summary": final_text or "Recommendation ready.",
        "mode": "agentic",
    }


async def run_agent_workflow(business_input: dict) -> dict:
    """Run the full discovery -> ranking -> campaign workflow through the
    shared MCP client/server connection, returning the result plus an
    activity log of every MCP tool call made along the way."""
    activity_log: list[dict] = []

    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            result = await _run_agentic(business_input, activity_log)
        except Exception:
            activity_log.clear()
            result = await _run_scripted(business_input, activity_log)
    else:
        result = await _run_scripted(business_input, activity_log)

    result["activity_log"] = activity_log
    return result
