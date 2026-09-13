"""
Interactive CLI for trying out OUTTHERE without a frontend.

Prompts for a business (defaults let you just mash Enter for a quick
demo), calls the running FastAPI server's /api/agent/recommend endpoint,
and pretty-prints the creator matches + campaign -- the same data a
frontend would render as cards.

Usage:
    1. In one terminal: uvicorn backend.main:app --reload --port 8000
    2. In another:       python scripts/try_it.py
"""

from __future__ import annotations

import sys

import httpx

SERVER_URL = "http://127.0.0.1:8000"


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def ask_int(prompt: str, default: int) -> int:
    raw = ask(prompt, str(default))
    try:
        return int(raw)
    except ValueError:
        print(f"  (not a number, using {default})")
        return default


def print_header(text: str) -> None:
    print()
    print(text)
    print("-" * len(text))


def run_once() -> None:
    print_header("Tell us about your business")
    business = {
        "business_name": ask("Business name", "Din Tai Fung"),
        "business_type": ask("Business type", "restaurant"),
        "location": ask("Location (City, ST)", "Arcadia, CA"),
        "description": ask("Description", "Taiwanese restaurant known for soup dumplings"),
        "target_audience": ask("Target audience", "25-45 year olds"),
        "goal": ask("Marketing goal", "Get more local customers"),
        "budget": ask_int("Monthly budget ($)", 300),
    }

    print()
    print("Finding creators...")
    try:
        response = httpx.post(f"{SERVER_URL}/api/agent/recommend", json=business, timeout=60)
        response.raise_for_status()
    except httpx.ConnectError:
        print(f"\nCouldn't reach {SERVER_URL} -- is the server running?")
        print("  Run this first, in another terminal: uvicorn backend.main:app --reload --port 8000")
        sys.exit(1)
    except httpx.HTTPStatusError as exc:
        print(f"\nServer returned an error: {exc.response.status_code} {exc.response.text}")
        sys.exit(1)

    result = response.json()
    biz = result["business"]

    print_header(f"{biz.get('business_name')} -- {biz.get('location')}")
    print(f"Category: {biz.get('business_category')} / {biz.get('sub_category')}")
    if biz.get("google_verified"):
        print(f"Google: verified -- {biz.get('google_rating')}★ ({biz.get('google_review_count')} reviews)")
        print(f"Address: {biz.get('formatted_address')}")
    else:
        print("Google: not verified (no Google Maps key configured, or business not found)")
    print(f"Mode: {result.get('mode')}  |  Agent said: {result.get('agent_summary', '')[:200]}")

    print_header("AI Agent Activity")
    for entry in result.get("activity_log", []):
        print(f"  ✓ {entry['tool']:<22} {entry['summary']}")

    print_header("Top Creator Matches")
    for i, creator in enumerate(result.get("creators", []), start=1):
        breakdown = creator.get("score_breakdown", {})
        print(f"\n#{i}  {creator.get('handle')}  --  Fit Score {creator.get('fit_score')}/100  ({creator.get('recommendation')})")
        print(f"    {creator.get('platform', '')} | {creator.get('followers', 0):,} followers | "
              f"{creator.get('engagement_rate', 0)}% engagement | ${creator.get('estimated_collaboration_cost', 0)} est. cost")
        print(f"    Locality {breakdown.get('locality','?')}/30  Audience {breakdown.get('audience_match','?')}/25  "
              f"Content {breakdown.get('content_relevance','?')}/20  Engagement {breakdown.get('engagement','?')}/15  "
              f"Budget {breakdown.get('budget_fit','?')}/10")
        if creator.get("explanation"):
            print(f"    \"{creator['explanation']}\"")

    campaign = result.get("campaign", {})
    print_header(f"Campaign: {campaign.get('campaign_name', '')}")
    print(f"Budget: ${campaign.get('estimated_spend', 0)} of ${campaign.get('budget', 0)}")
    print(f"Expected reach: ~{campaign.get('expected_reach', 0):,}")
    print(f"Strategy: {campaign.get('strategy', '')}")
    print("Content ideas:")
    for idea in campaign.get("content_ideas", []):
        print(f"  - {idea}")


if __name__ == "__main__":
    while True:
        run_once()
        print()
        if ask("Try another business? (y/n)", "y").lower().startswith("n"):
            break
