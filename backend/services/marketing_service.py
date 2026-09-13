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

import hashlib
import re

from . import llm_client, places_service

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

    result = {
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

    # Best-effort real-world validation via Google Places. Never raises and
    # never blocks the deterministic fields above -- if this fails or isn't
    # configured, `google_verified` is simply False and everything else
    # about analyze_business behaves exactly as it did before this existed.
    try:
        places_data = places_service.lookup_business(
            result["business_name"], result["location"], business_type
        )
    except Exception:
        places_data = None

    if places_data:
        result.update(places_data)
    else:
        result["google_verified"] = False

    return result


def explain_creator_fit(business: dict, creator: dict, score_result: dict, use_llm: bool = True) -> str:
    """One or two sentence explanation of why a creator fits (or doesn't).
    Tries the LLM first, falls back to a templated sentence built from the
    deterministic strengths list. `use_llm=False` skips straight to the
    template -- used for lower-ranked candidates where an LLM call would
    just add latency for an explanation nobody will read."""
    strengths = score_result.get("strengths", [])
    fallback = (
        f"{creator.get('handle')} scored {score_result.get('fit_score')}/100 for "
        f"{business.get('business_name', 'this business')}. "
        + (f"Key reasons: {', '.join(strengths[:3])}." if strengths else "")
    )
    if not use_llm:
        return fallback

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
        "(3) exactly 3 short content ideas (one sentence each, under 20 words), (4) one simple "
        "promotional offer (under 15 words). Respond in plain text with labeled sections IN THIS "
        "EXACT ORDER: NAME:, STRATEGY:, OFFER:, IDEAS: (IDEAS last, since it's fine if the least "
        "critical section runs out of room before the others do)."
    )
    text = llm_client.generate_text(
        system_prompt=(
            "You are a marketing strategist creating simple, actionable small-business campaigns. "
            "You are concise and always finish each section completely before moving to the next."
        ),
        user_prompt=prompt,
        max_tokens=600,
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
        offer_match = re.search(r"OFFER:\s*(.+?)(?:\nIDEAS:|$)", text, re.DOTALL)
        ideas_match = re.search(r"IDEAS:\s*(.+)$", text, re.DOTALL)

        if name_match:
            campaign_name = name_match.group(1).strip().strip('"')
        if strategy_match:
            strategy = strategy_match.group(1).strip()
        if ideas_match:
            parsed_ideas = [
                re.sub(r"^\s*(?:[\-\*•]|\d+[\.\)])\s*", "", line).strip()
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


def _simulated_presence_scores(business: dict) -> tuple[int, int, int]:
    """Deterministic pseudo-signal fallback for when Places data isn't
    available -- same business always returns the same demo numbers."""
    seed = int(hashlib.sha256(business.get("business_name", "").encode()).hexdigest(), 16)
    google_presence = 40 + (seed % 45)
    social_presence = 30 + ((seed // 7) % 50)
    content_consistency = 25 + ((seed // 13) % 55)
    return google_presence, social_presence, content_consistency


def analyze_online_presence(business: dict) -> dict:
    """Estimate online visibility, using real Google Places signals for
    `google_presence` when analyze_business successfully validated the
    business (google_verified=True), and clearly-labeled simulated demo
    numbers otherwise. `social_presence`/`content_consistency` are always
    simulated -- Places has no visibility into social media."""
    _, fallback_social, fallback_consistency = _simulated_presence_scores(business)
    social_presence = fallback_social
    content_consistency = fallback_consistency

    nearby_competitors: list[dict] = []
    data_source = "simulated"

    if business.get("google_verified"):
        data_source = "real"
        rating = business.get("google_rating") or 0
        review_count = business.get("google_review_count") or 0
        # Rating carries most of the weight; review volume is a secondary
        # signal capped so one viral spot doesn't dominate the score.
        google_presence = round(min(rating, 5) / 5 * 70 + min(review_count, 200) / 200 * 30)
        if business.get("has_website"):
            google_presence = min(100, google_presence + 5)

        lat, lng = business.get("latitude"), business.get("longitude")
        if lat is not None and lng is not None:
            keyword = business.get("sub_category") or business.get("business_category", "")
            try:
                nearby_competitors = places_service.nearby_places(
                    lat, lng, keyword, exclude_place_id=business.get("google_place_id")
                )
            except Exception:
                nearby_competitors = []
    else:
        google_presence, _, _ = _simulated_presence_scores(business)

    overall_visibility = round((google_presence + social_presence + content_consistency) / 3)

    recommendations = []
    if business.get("google_verified") is False:
        recommendations.append("We couldn't find a verified Google Business Profile for this business -- claiming one is the single highest-leverage fix")
    elif google_presence < 60:
        recommendations.append("Complete your Google Business Profile with current hours, photos, and encourage more reviews")
    if social_presence < 60:
        recommendations.append("Post consistently on at least one platform your target audience actually uses")
    if content_consistency < 60:
        recommendations.append("Establish a regular posting cadence instead of sporadic updates")
    if nearby_competitors:
        recommendations.append(
            f"{len(nearby_competitors)} similar businesses were found nearby on Google -- creator content is a "
            "way to stand out that a Google listing alone can't provide"
        )
    recommendations.append("Partner with locally-relevant creators to reach audiences your own channels can't")

    return {
        "google_presence": google_presence,
        "social_presence": social_presence,
        "content_consistency": content_consistency,
        "overall_visibility": overall_visibility,
        "recommendations": recommendations,
        "data_source": data_source,
        "nearby_competitors": nearby_competitors,
    }


_FALLBACK_SCENE_TEMPLATES = {
    "food": [
        ("Close-up shot of the signature item being made or plated, steam/texture visible", "POV: {business_name}'s best kept secret"),
        ("Quick pan across 3-4 menu items in focus", "You didn't know you needed this"),
        ("Customer taking a first bite, genuine reaction", "{location}"),
        ("Storefront exterior, inviting entrance shot", "Visit this weekend 👇"),
    ],
    "beauty": [
        ("Before/prep shot -- product or tools laid out", "The glow-up starts here"),
        ("Close-up of the service/technique in action", "{business_name} magic ✨"),
        ("Reveal shot -- final result, genuine reaction", "Book your spot"),
        ("Storefront or interior ambience shot", "{location}"),
    ],
    "fitness": [
        ("Energetic establishing shot of the space/class in action", "Your new favorite workout"),
        ("Close-up of proper form / a signature move", "{business_name}"),
        ("Group energy / high-five / celebration moment", "Real people, real results"),
        ("Exterior or schedule board shot", "First class free -- {location}"),
    ],
}
_DEFAULT_SCENE_TEMPLATE = [
    ("Establishing shot introducing the business", "{business_name}"),
    ("Close-up on the product/service that makes it special", "This is why locals love it"),
    ("A real customer or team moment, genuine and unscripted-feeling", "{location}"),
    ("Closing shot with a clear call to action", "Come see for yourself"),
]


def _fallback_video_script(business: dict, content_idea: str, platform: str, duration_seconds: int) -> dict:
    category = business.get("business_category", "")
    business_name = business.get("business_name", business.get("name", "this business"))
    location = business.get("location", "")

    template = _FALLBACK_SCENE_TEMPLATES.get(category, _DEFAULT_SCENE_TEMPLATE)
    slice_seconds = duration_seconds / len(template)
    scenes = []
    for i, (shot, text) in enumerate(template):
        start = round(i * slice_seconds)
        end = round((i + 1) * slice_seconds)
        scenes.append({
            "timing": f"{start}-{end}s",
            "shot": shot,
            "on_screen_text": text.format(business_name=business_name, location=location),
            "audio_note": "Trending upbeat track, cut on the beat" if i == 0 else "",
        })

    return {
        "platform": platform,
        "duration_seconds": duration_seconds,
        "based_on_idea": content_idea,
        "scenes": scenes,
        "caption": f"{business_name} -- {content_idea}" if content_idea else business_name,
        "hashtags": [f"#{location.split(',')[0].strip().replace(' ', '')}" if location else "#local",
                     f"#{category}" if category else "#smallbusiness", "#supportlocal"],
        "cta": "Tag a friend who needs to see this",
    }


def generate_video_script(business: dict, content_idea: str, platform: str = "TikTok / Instagram Reels",
                           duration_seconds: int = 30) -> dict:
    """Turn one campaign content idea into a shot-by-shot short-form video
    script (scenes with timing/visual/on-screen text, caption, hashtags,
    CTA) -- something a business owner or creator could actually film
    from, not just a vague idea. Deterministic template fallback if the
    LLM is unavailable."""
    fallback = _fallback_video_script(business, content_idea, platform, duration_seconds)

    prompt = (
        f"Business: {business.get('business_name', business.get('name'))} "
        f"({business.get('business_category', '')}) in {business.get('location', '')}.\n"
        f"Content idea to turn into a script: {content_idea}\n"
        f"Platform: {platform}. Target length: {duration_seconds} seconds.\n\n"
        "Write a shot-by-shot short-form video script a small business owner (not a professional "
        "videographer) could actually film on a phone. Respond in plain text with labeled sections:\n"
        "CAPTION: <one line caption for the post>\n"
        "HASHTAGS: <4-6 relevant hashtags, space separated>\n"
        "SCENES: <numbered list, each line as 'START-ENDs | shot description | on-screen text'>\n"
        "CTA: <one short call to action line>"
    )
    text = llm_client.generate_text(
        system_prompt="You are a short-form video creative director who writes simple, filmable scripts for small businesses with no production budget.",
        user_prompt=prompt,
        max_tokens=500,
    )
    if not text:
        return fallback

    caption_match = re.search(r"CAPTION:\s*(.+)", text)
    hashtags_match = re.search(r"HASHTAGS:\s*(.+)", text)
    scenes_match = re.search(r"SCENES:\s*(.+?)(?:\nCTA:|$)", text, re.DOTALL)
    cta_match = re.search(r"CTA:\s*(.+)", text)

    scenes = fallback["scenes"]
    if scenes_match:
        parsed_scenes = []
        for line in scenes_match.group(1).strip().splitlines():
            line = re.sub(r"^\s*(?:[\-\*•]|\d+[\.\)])\s*", "", line).strip()
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                parsed_scenes.append({"timing": parts[0], "shot": parts[1], "on_screen_text": parts[2], "audio_note": ""})
        if parsed_scenes:
            scenes = parsed_scenes

    return {
        "platform": platform,
        "duration_seconds": duration_seconds,
        "based_on_idea": content_idea,
        "scenes": scenes,
        "caption": caption_match.group(1).strip() if caption_match else fallback["caption"],
        "hashtags": hashtags_match.group(1).strip().split() if hashtags_match else fallback["hashtags"],
        "cta": cta_match.group(1).strip() if cta_match else fallback["cta"],
    }


def _discovered_facts(business: dict) -> list[str]:
    """Real signals already known about this business (from analyze_business's
    Google Places lookup) -- used to ground the ad concept in facts instead
    of generic filler, e.g. "4.5★ (2,876 reviews)" instead of "great food"."""
    facts = []
    if business.get("google_verified"):
        if business.get("google_rating"):
            reviews = f" ({business['google_review_count']} reviews)" if business.get("google_review_count") else ""
            facts.append(f"{business['google_rating']}★ on Google{reviews}")
        if business.get("formatted_address"):
            facts.append(f"located at {business['formatted_address']}")
    if business.get("sub_category") or business.get("business_category"):
        facts.append(f"category: {business.get('sub_category') or business.get('business_category')}")
    return facts


def _fallback_ad_concept(business: dict, offer: str, target_audience: str, style: str, duration_seconds: int) -> dict:
    business_name = business.get("business_name", business.get("name", "This business"))
    category = business.get("business_category", "")
    angle = f"{offer} -- made for {target_audience}" if offer else f"Discover {business_name}"

    template = [
        (f"Establishing shot of {business_name} / its product, {style} feel", business_name),
        (f"Close-up on the specific thing being offered: {offer or 'the signature item'}", offer or "Today's special"),
        ("Logo + offer text, clear call to action", "Come see for yourself"),
    ]
    slice_seconds = duration_seconds / len(template)
    scenes = []
    for i, (shot, text) in enumerate(template):
        start = round(i * slice_seconds)
        end = round((i + 1) * slice_seconds)
        scenes.append({"timing": f"{start}-{end}s", "shot": shot, "on_screen_text": text})

    video_prompt = (
        f"An {duration_seconds}-second vertical social media advertisement for {business_name}, a "
        f"{category or 'local business'}. Style: {style}. " +
        " Then, ".join(s["shot"] for s in scenes) +
        f". Aimed at {target_audience}. Include the offer: {offer}."
    )

    return {"campaign_angle": angle, "scenes": scenes, "video_prompt": video_prompt}


def generate_ad_concept(business: dict, offer: str, target_audience: str, style: str,
                         duration_seconds: int = 8) -> dict:
    """LLM-driven ad concept: a specific marketing angle, a short scene
    breakdown, and one synthesized text-to-video prompt -- grounded in any
    real signals already discovered about the business (Google rating,
    address, category) via analyze_business, rather than generic filler.
    Falls back to a deterministic template if the LLM is unavailable."""
    fallback = _fallback_ad_concept(business, offer, target_audience, style, duration_seconds)
    facts = _discovered_facts(business)

    prompt = (
        f"Business: {business.get('business_name', business.get('name'))}\n"
        f"Category: {business.get('business_category', '')} / {business.get('sub_category', '')}\n"
        f"Location: {business.get('location', '')}\n"
        + (f"Discovered facts: {'; '.join(facts)}\n" if facts else "")
        + f"Offer: {offer}\nTarget audience: {target_audience}\nVisual style: {style}\n"
        f"Ad length: {duration_seconds} seconds, vertical (TikTok/Reels/Shorts).\n\n"
        "Come up with a specific, catchy marketing angle for a short video ad -- not a generic "
        "'shop now' angle, make it specific to this business and audience. Then write ONE dense "
        f"paragraph (2-4 sentences, under 100 words) describing all {duration_seconds} seconds of the "
        "ad as a single flowing cinematic description, suitable as a direct prompt for a text-to-video "
        "AI model. Finally, break that same paragraph into 3 quick scenes for reference -- keep each "
        "scene's shot description to one short sentence (under 15 words).\n\n"
        "Respond in plain text with labeled sections IN THIS EXACT ORDER (most important fields first, "
        "in case you run out of room):\n"
        "ANGLE: <short campaign angle/name>\n"
        "VIDEO_PROMPT: <the single combined paragraph for the video model -- write this fully before SCENES>\n"
        "SCENES: <numbered list, each line as 'START-ENDs | short shot description | on-screen text'>"
    )
    text = llm_client.generate_text(
        system_prompt=(
            "You are a performance-marketing creative director who writes sharp, specific short-video "
            "ad concepts for small businesses, then translates them into prompts for a text-to-video AI model. "
            "You are concise and always finish the VIDEO_PROMPT section completely before moving on."
        ),
        user_prompt=prompt,
        max_tokens=700,
    )
    if not text:
        return fallback

    angle_match = re.search(r"ANGLE:\s*(.+)", text)
    video_prompt_match = re.search(r"VIDEO_PROMPT:\s*(.+?)(?:\nSCENES:|$)", text, re.DOTALL)
    scenes_match = re.search(r"SCENES:\s*(.+)$", text, re.DOTALL)

    scenes = fallback["scenes"]
    if scenes_match:
        parsed_scenes = []
        for line in scenes_match.group(1).strip().splitlines():
            line = re.sub(r"^\s*(?:[\-\*•]|\d+[\.\)])\s*", "", line).strip()
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                parsed_scenes.append({"timing": parts[0], "shot": parts[1], "on_screen_text": parts[2]})
        if parsed_scenes:
            scenes = parsed_scenes

    return {
        "campaign_angle": angle_match.group(1).strip() if angle_match else fallback["campaign_angle"],
        "scenes": scenes,
        "video_prompt": video_prompt_match.group(1).strip() if video_prompt_match else fallback["video_prompt"],
    }
