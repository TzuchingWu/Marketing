"""
LLM-assisted marketing reasoning: business understanding, recommendation
explanations, outreach messages, and campaign generation.

Structured extraction (category, age range, interests) is done with
deterministic keyword rules so the pipeline never breaks if the LLM is
unavailable -- the LLM is layered on top purely for natural-language
narrative (explanations, outreach copy, campaign ideas), with a
templated fallback for every LLM call.
"""

from __future__ import annotations

import re

from . import llm_client

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "food": [
        "bakery", "cafe", "café", "coffee", "restaurant", "pastry", "pastries",
        "bread", "dessert", "food", "eatery", "diner", "bbq", "pizza", "sushi",
        "taco", "deli", "catering", "kitchen", "brunch",
    ],
    "beauty": ["salon", "spa", "beauty", "makeup", "cosmetic", "nails", "hair", "skincare"],
    "fashion": ["boutique", "clothing", "apparel", "fashion", "style", "streetwear"],
    "fitness": ["gym", "fitness", "yoga", "pilates", "studio", "training", "crossfit"],
    "gaming": ["gaming", "esports", "arcade", "game lounge"],
    "tech": ["tech", "software", "electronics", "computer", "repair shop"],
    "travel": ["travel", "tour", "agency", "excursion"],
}

SUB_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "bakery": ["bakery", "pastry", "pastries", "bread"],
    "coffee shop": ["coffee", "cafe", "café", "espresso"],
    "restaurant": ["restaurant", "eatery", "diner", "kitchen", "bbq", "pizza", "sushi", "taco"],
    "salon": ["salon", "hair", "nails"],
    "spa": ["spa", "skincare", "wellness"],
    "boutique": ["boutique", "clothing", "apparel", "streetwear"],
    "gym": ["gym", "fitness", "crossfit", "training"],
    "yoga studio": ["yoga", "pilates"],
}

GOAL_KEYWORDS: dict[str, list[str]] = {
    "local_customer_acquisition": ["local customer", "more customers", "foot traffic", "walk-in", "local business"],
    "brand_awareness": ["awareness", "brand", "visibility", "get noticed", "exposure"],
    "increase_sales": ["sales", "revenue", "orders", "sell more"],
    "event_promotion": ["event", "launch", "grand opening", "promotion", "promote"],
}

AGE_RANGE_RE = re.compile(r"(\d{1,2})\s*(?:-|–|to)\s*(\d{1,2})")

DEFAULT_INTERESTS_BY_CATEGORY = {
    "food": ["food", "local businesses", "desserts"],
    "beauty": ["beauty", "self-care", "local businesses"],
    "fashion": ["fashion", "style", "local businesses"],
    "fitness": ["fitness", "wellness", "local businesses"],
    "gaming": ["gaming", "tech"],
    "tech": ["tech", "gadgets"],
    "travel": ["travel", "local businesses"],
}


def _match_keywords(text: str, keyword_map: dict[str, list[str]], default: str) -> str:
    text_lower = text.lower()
    for label, keywords in keyword_map.items():
        if any(kw in text_lower for kw in keywords):
            return label
    return default


def _extract_age_range(target_audience: str) -> tuple[int, int]:
    match = AGE_RANGE_RE.search(target_audience or "")
    if match:
        lo, hi = int(match.group(1)), int(match.group(2))
        if lo < hi:
            return lo, hi
    return 18, 45


def analyze_business(business_input: dict) -> dict:
    """Deterministically classify a business into structured marketing
    fields. Kept rule-based (not LLM-based) so this core step never fails
    or drifts between runs."""
    business_type = business_input.get("business_type", "") or ""
    description = business_input.get("description", "") or ""
    combined_text = f"{business_type} {description}"

    business_category = _match_keywords(combined_text, CATEGORY_KEYWORDS, default="local lifestyle")
    sub_category = _match_keywords(combined_text, SUB_CATEGORY_KEYWORDS, default=business_category)

    age_min, age_max = _extract_age_range(business_input.get("target_audience", ""))

    interests = list(DEFAULT_INTERESTS_BY_CATEGORY.get(business_category, [business_category, "local businesses"]))
    # Pull in any extra category keywords explicitly mentioned in the text
    # (e.g. a bakery that also mentions "coffee") so interests reflect the
    # actual business, not just its primary category.
    for label, keywords in CATEGORY_KEYWORDS.items():
        if label != business_category and any(kw in combined_text.lower() for kw in keywords):
            if label not in interests:
                interests.append(label)

    marketing_goal = _match_keywords(
        business_input.get("goal", "") or "", GOAL_KEYWORDS, default="local_customer_acquisition"
    )

    return {
        "business_category": business_category,
        "sub_category": sub_category,
        "location": business_input.get("location", ""),
        "target_age_min": age_min,
        "target_age_max": age_max,
        "target_interests": interests,
        "marketing_goal": marketing_goal,
        "budget": business_input.get("budget", 0),
        "business_name": business_input.get("business_name", ""),
        "description": description,
    }


def explain_creator_fit(business: dict, creator: dict, score_result: dict) -> str:
    """One or two sentence explanation of why a creator fits (or doesn't).
    Tries the LLM first, falls back to a templated sentence built from the
    deterministic strengths list."""
    strengths = score_result.get("strengths", [])
    fallback = (
        f"{creator.get('handle')} scored {score_result.get('fit_score')}/100 for "
        f"{business.get('business_name', 'this business')}. "
        + (f"Key reasons: {', '.join(strengths[:3])}." if strengths else "")
    )

    prompt = (
        f"Business: {business.get('business_name')} ({business.get('business_category')}) "
        f"in {business.get('location')}. Goal: {business.get('marketing_goal')}.\n"
        f"Creator: {creator.get('handle')} ({creator.get('platform')}), categories "
        f"{creator.get('categories')}, {creator.get('followers')} followers, "
        f"{creator.get('engagement_rate')}% engagement, {creator.get('audience_local_percentage')}% "
        f"local audience.\n"
        f"Fit score: {score_result.get('fit_score')}/100. Strengths: {strengths}.\n\n"
        "Write 1-2 short, specific sentences explaining why this creator is (or isn't) "
        "a good marketing fit for this business. Plain language, no hashtags, no bullet points."
    )
    text = llm_client.generate_text(
        system_prompt="You are a marketing analyst explaining creator-fit recommendations concisely and specifically.",
        user_prompt=prompt,
        max_tokens=150,
    )
    return text or fallback


def generate_outreach(business: dict, creator: dict, offer: str, tone: str = "friendly") -> str:
    """Personalized outreach message from the business to a creator."""
    business_desc = business.get("description") or business.get("business_category") or "a local business"
    if business_desc.split()[0].lower() not in ("a", "an", "the"):
        business_desc = f"a {business_desc}"

    fallback = (
        f"Hey {creator.get('handle')}! We love your {', '.join(creator.get('category', creator.get('categories', []))[:2]) or 'local'} "
        f"content and think {business.get('name', business.get('business_name', 'we'))} would be a great fit for your audience. "
        f"We're {business_desc}, and we'd love to offer you {offer}. "
        "Let us know if you'd be interested in collaborating -- we think your followers would genuinely enjoy it!"
    )

    prompt = (
        f"Write a short, specific, non-spammy outreach DM from a small business to a content creator, "
        f"in a {tone} tone.\n\n"
        f"Business: {business.get('name', business.get('business_name'))} -- "
        f"{business.get('description', '')}\n"
        f"Business goal: {business.get('goal', business.get('marketing_goal', ''))}\n"
        f"Creator: {creator.get('handle')} ({creator.get('name', '')}), known for "
        f"{creator.get('category', creator.get('categories', ''))} content in {creator.get('location', '')}\n"
        f"Offer: {offer}\n\n"
        "Keep it under 80 words, personal (reference what the creator actually posts about), "
        "and end with a clear but low-pressure call to action. No hashtags, no emojis-spam, no generic "
        "'Hi, I hope this finds you well'."
    )
    text = llm_client.generate_text(
        system_prompt="You write concise, genuine creator-outreach messages for small businesses. Never generic or spammy.",
        user_prompt=prompt,
        max_tokens=200,
    )
    return text or fallback


def _allocate_budget(creators: list[dict], budget: int) -> tuple[list[dict], int]:
    """Greedily include creators (highest fit first) while staying within
    budget. Returns (included_creators_with_spend, total_spend)."""
    ordered = sorted(creators, key=lambda c: c.get("fit_score", 0), reverse=True)
    included = []
    remaining = budget
    for creator in ordered:
        cost = creator.get("estimated_collaboration_cost", 0) or 0
        if cost <= remaining:
            included.append(creator)
            remaining -= cost
    if not included and ordered:
        included = [ordered[0]]  # always recommend at least one creator
    total_spend = sum(c.get("estimated_collaboration_cost", 0) or 0 for c in included)
    return included, total_spend


def _fallback_campaign_name(business_category: str) -> str:
    names = {
        "food": "Local Foodie Discovery",
        "beauty": "Glow Up Local",
        "fashion": "Style Spotlight",
        "fitness": "Get Moving Local",
        "gaming": "Level Up Local",
        "tech": "Tech Discovery Days",
        "travel": "Weekend Getaway Push",
    }
    return names.get(business_category, "Local Discovery Campaign")


def _fallback_content_ideas(business: dict, creators: list[dict]) -> list[str]:
    category = business.get("business_category", "local")
    return [
        f"Short-form {category} review featuring your best-selling item",
        "Behind-the-scenes video of how your product/service is made",
        f"Weekend special or limited-time offer promoted by {creators[0].get('handle')}" if creators else
        "Weekend special or limited-time offer post",
    ]


def generate_campaign(business: dict, creators: list[dict], budget: int, goal: str) -> dict:
    """Build a full campaign plan from a shortlist of ranked creators."""
    included, total_spend = _allocate_budget(creators, budget)
    expected_reach = round(sum((c.get("followers", 0) or 0) for c in included) * 1.05)

    prompt = (
        f"Business: {business.get('business_name', business.get('name'))} "
        f"({business.get('business_category', '')}) in {business.get('location', '')}.\n"
        f"Goal: {goal}. Budget: ${budget}.\n"
        f"Selected creators: {[c.get('handle') for c in included]}.\n\n"
        "Suggest: (1) a catchy 3-5 word campaign name, (2) a 1-2 sentence strategy summary, "
        "(3) exactly 3 short content ideas, (4) one simple promotional offer. "
        "Respond in plain text with labeled sections: NAME:, STRATEGY:, IDEAS:, OFFER:."
    )
    text = llm_client.generate_text(
        system_prompt="You are a marketing strategist creating simple, actionable small-business campaigns.",
        user_prompt=prompt,
        max_tokens=350,
    )

    campaign_name = _fallback_campaign_name(business.get("business_category", ""))
    strategy = (
        f"Partner with {len(included)} highly-relevant local creator(s) to put "
        f"{business.get('business_name', business.get('name', 'the business'))} in front of "
        f"an audience that's already local and already interested in {business.get('business_category', 'this category')}."
    )
    content_ideas = _fallback_content_ideas(business, included)
    offers = [f"${min(100, budget)} sponsored post + free product sampling"]

    if text:
        name_match = re.search(r"NAME:\s*(.+)", text)
        strategy_match = re.search(r"STRATEGY:\s*(.+?)(?:\n[A-Z]+:|$)", text, re.DOTALL)
        ideas_match = re.search(r"IDEAS:\s*(.+?)(?:\nOFFER:|$)", text, re.DOTALL)
        offer_match = re.search(r"OFFER:\s*(.+)", text, re.DOTALL)

        if name_match:
            campaign_name = name_match.group(1).strip().strip('"')
        if strategy_match:
            strategy = strategy_match.group(1).strip()
        if ideas_match:
            parsed_ideas = [
                re.sub(r"^[\-\*\d\.\)\s]+", "", line).strip()
                for line in ideas_match.group(1).strip().splitlines()
                if line.strip()
            ]
            if parsed_ideas:
                content_ideas = parsed_ideas[:3]
        if offer_match:
            offers = [offer_match.group(1).strip()]

    return {
        "campaign_name": campaign_name,
        "objective": goal,
        "budget": budget,
        "strategy": strategy,
        "creators": included,
        "content_ideas": content_ideas,
        "offers": offers,
        "estimated_spend": total_spend,
        "expected_reach": expected_reach,
    }
