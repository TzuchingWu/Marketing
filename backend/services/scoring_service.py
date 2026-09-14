"""
Deterministic creator-fit scoring.

This is intentionally pure, dependency-free arithmetic -- no LLM calls.
Given the same business + creator input, `calculate_creator_fit_score`
always returns the same output. The LLM's job (elsewhere) is to explain
*why* a score looks the way it does, never to compute the score itself.

Weighting (out of 100):
    locality / geographic relevance   30
    audience demographic match        25
    content / category relevance      20
    engagement quality                15
    budget compatibility              10
"""

from __future__ import annotations

# Cities are grouped so nearby-but-not-identical locations still score
# reasonably well on locality instead of falling off a cliff.
SGV_REGION_CITIES = {
    "arcadia", "monrovia", "pasadena", "san gabriel", "alhambra",
    "temple city", "rosemead", "el monte", "san marino",
}
GREATER_LA_CITIES = SGV_REGION_CITIES | {"glendale", "los angeles"}

# Small hand-built adjacency map of neighboring SGV-area cities.
ADJACENT_CITIES = {
    "arcadia": {"monrovia", "temple city", "san marino", "pasadena"},
    "monrovia": {"arcadia", "temple city", "el monte"},
    "pasadena": {"arcadia", "san marino", "glendale"},
    "san gabriel": {"alhambra", "rosemead", "temple city", "san marino"},
    "alhambra": {"san gabriel", "rosemead", "los angeles"},
    "temple city": {"arcadia", "san gabriel", "rosemead", "monrovia"},
    "rosemead": {"san gabriel", "alhambra", "temple city", "el monte"},
    "el monte": {"rosemead", "monrovia", "temple city"},
    "san marino": {"arcadia", "pasadena", "san gabriel"},
    "glendale": {"pasadena", "los angeles"},
    "los angeles": {"alhambra", "glendale"},
}


def _city_key(location: str) -> str:
    """Normalize a "City, ST" style string down to just the city name."""
    if not location:
        return ""
    return location.split(",")[0].strip().lower()


def _parse_age_range(age_range: str) -> tuple[int, int]:
    try:
        lo, hi = age_range.split("-")
        return int(lo), int(hi)
    except (ValueError, AttributeError):
        return (0, 0)


def locality_score(business: dict, creator: dict) -> float:
    """0-30 points: geographic proximity + how local the creator's audience is."""
    business_city = _city_key(business.get("location", ""))
    creator_city = _city_key(creator.get("location", ""))

    if business_city and creator_city == business_city:
        proximity = 20.0
    elif creator_city in ADJACENT_CITIES.get(business_city, set()):
        proximity = 14.0
    elif business_city in GREATER_LA_CITIES and creator_city in GREATER_LA_CITIES:
        proximity = 8.0
    else:
        proximity = 2.0

    # None means genuinely unknown (e.g. a web-search-discovered creator,
    # where this isn't public data) -- treat that as a neutral assumption
    # rather than confirmed 0%, which would unfairly tank real creators
    # for data the mock dataset simply fabricates.
    local_pct = creator.get("audience_local_percentage")
    local_pct = 50.0 if local_pct is None else local_pct
    local_pct_contribution = min(local_pct, 100) / 100 * 10.0

    return round(min(proximity + local_pct_contribution, 30.0), 1)


def audience_score(business: dict, creator: dict) -> float:
    """0-25 points: overlap between the business's target age range and the
    creator's audience age range, as a fraction of the business's target range."""
    biz_lo = business.get("target_age_min")
    biz_hi = business.get("target_age_max")
    if biz_lo is None or biz_hi is None or biz_hi <= biz_lo:
        return 12.5  # neutral default when the business gave no usable range

    if not creator.get("audience_age_range"):
        return 12.5  # unknown (not fabricated), not confirmed mismatch -- same neutral default

    cre_lo, cre_hi = _parse_age_range(creator.get("audience_age_range", ""))
    if cre_hi <= cre_lo:
        return 0.0

    overlap = max(0, min(biz_hi, cre_hi) - max(biz_lo, cre_lo))
    business_span = biz_hi - biz_lo
    overlap_ratio = min(overlap / business_span, 1.0)

    return round(overlap_ratio * 25.0, 1)


def content_relevance_score(business: dict, creator: dict) -> float:
    """0-20 points: overlap between the business's category/interests and the
    creator's content categories."""
    business_terms = {business.get("business_category", "").lower()}
    business_terms |= {i.lower() for i in business.get("target_interests", [])}
    business_terms.discard("")

    creator_terms = {c.lower() for c in creator.get("categories", [])}

    if not business_terms or not creator_terms:
        return 0.0

    matches = business_terms & creator_terms
    if not matches:
        return 0.0

    match_ratio = len(matches) / len(business_terms)
    # Direct category hit (e.g. "food" == "food") is the strongest signal,
    # so give it a floor even if the business has many other interests.
    base = 12.0 if business.get("business_category", "").lower() in creator_terms else 0.0
    return round(min(base + match_ratio * 20.0, 20.0), 1)


def engagement_score(creator: dict) -> float:
    """0-15 points: engagement rate normalized against a realistic ceiling.

    Micro/local creators often post double-digit engagement rates, so a
    12% ceiling (rather than follower-count-driven benchmarks) keeps the
    score meaningful without over-rewarding outliers.
    """
    # None means unknown (not public data for a web-discovered creator),
    # not confirmed zero -- assume an average ~5% rather than penalizing
    # a real creator for data the mock dataset simply fabricates.
    rate = creator.get("engagement_rate")
    rate = 5.0 if rate is None else rate
    ceiling = 12.0
    return round(min(rate, ceiling) / ceiling * 15.0, 1)


def budget_score(business: dict, creator: dict) -> float:
    """0-10 points: how comfortably the creator's collaboration cost fits
    inside the business's monthly budget."""
    budget = business.get("budget", 0) or 0
    cost = creator.get("estimated_collaboration_cost")

    if budget <= 0:
        return 0.0
    # None means genuinely unknown (real creators have no public pricing
    # data) -- treat that as neutral, NOT as "definitely affordable".
    # Explicitly-stated 0 (e.g. free promotion) still gets full marks.
    if cost is None:
        return 5.0
    if cost <= 0:
        return 10.0

    ratio = cost / budget
    if ratio <= 0.33:
        return 10.0
    if ratio <= 0.6:
        return 8.0
    if ratio <= 1.0:
        return 5.0
    if ratio <= 1.3:
        return 2.0
    return 0.0


def _recommendation_label(total: float) -> str:
    if total >= 85:
        return "Strong match"
    if total >= 70:
        return "Good match"
    if total >= 50:
        return "Moderate match"
    return "Weak match"


def _strengths_and_weaknesses(creator: dict, breakdown: dict) -> tuple[list[str], list[str]]:
    strengths, weaknesses = [], []

    if breakdown["locality"] >= 24:
        strengths.append("Strong local audience")
    elif breakdown["locality"] <= 10:
        weaknesses.append("Limited geographic overlap")

    if breakdown["audience_match"] >= 20:
        strengths.append("Audience overlaps target demographic")
    elif breakdown["audience_match"] <= 10:
        weaknesses.append("Audience age range doesn't align well")

    if breakdown["content_relevance"] >= 16:
        strengths.append("Highly relevant content")
    elif breakdown["content_relevance"] <= 6:
        weaknesses.append("Content categories don't closely match")

    if breakdown["engagement"] >= 11:
        strengths.append("Strong, active engagement")
    elif breakdown["engagement"] <= 5:
        weaknesses.append("Below-average engagement rate")

    if breakdown["budget_fit"] >= 8:
        strengths.append("Affordable collaboration estimate")
    elif breakdown["budget_fit"] <= 2:
        weaknesses.append("Collaboration cost is tight for the budget")

    if creator.get("followers", 0) < 8000:
        weaknesses.append("Smaller total audience")

    return strengths, weaknesses


def calculate_creator_fit_score(business: dict, creator: dict) -> dict:
    """Compute the full Creator Fit Score for one business/creator pair.

    Returns the individual weighted components (each already scaled to its
    max) plus the final 0-100 score, strengths/weaknesses, and a short
    recommendation label.
    """
    breakdown = {
        "locality": locality_score(business, creator),
        "audience_match": audience_score(business, creator),
        "content_relevance": content_relevance_score(business, creator),
        "engagement": engagement_score(creator),
        "budget_fit": budget_score(business, creator),
    }
    total = round(sum(breakdown.values()))
    total = max(0, min(total, 100))

    strengths, weaknesses = _strengths_and_weaknesses(creator, breakdown)

    return {
        "creator_id": creator.get("id"),
        "handle": creator.get("handle"),
        "fit_score": total,
        "score_breakdown": {k: round(v) for k, v in breakdown.items()},
        "strengths": strengths,
        "weaknesses": weaknesses or ["No major concerns identified"],
        "recommendation": _recommendation_label(total),
    }
