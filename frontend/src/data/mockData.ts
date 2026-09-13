import type {
  Opportunity,
  Trend,
  AudienceSegment,
  Campaign,
  AgentActivity,
  Integration,
} from "../types";
export const opportunities: Opportunity[] = [
  {
    id: "sunday",
    name: "Sunday Reset",
    growth: 218,
    match: 92,
    relevance: 89,
    score: 91,
    momentum: 95,
    stage: "Rising fast",
    audience: "College Wellness",
    platform: "TikTok",
    format: "UGC Video",
    product: "Hydra Electrolyte Mix",
    reasoning:
      "Sunday Reset content is rapidly growing among Hydra’s highest-converting younger audience. Wellness, productivity, and hydration frequently appear together in this content category.",
    hook: "3 things I do Sunday night so Monday doesn’t destroy me.",
    cta: "Start your week hydrated.",
    color: "sage",
  },
  {
    id: "run",
    name: "Run Clubs",
    growth: 146,
    match: 87,
    relevance: 94,
    score: 88,
    momentum: 90,
    stage: "Rising",
    audience: "Active Professionals",
    platform: "Instagram Reels",
    format: "Creator Collaboration",
    product: "Hydra Electrolyte Mix",
    reasoning:
      "Social running is bringing active professionals together. Post-run hydration fits naturally into creator-led community content.",
    hook: "The best part of run club happens after the finish line.",
    cta: "Find your pace. Bring your Hydra.",
    color: "peach",
  },
  {
    id: "morning",
    name: "Morning Routine",
    growth: 94,
    match: 84,
    relevance: 86,
    score: 85,
    momentum: 82,
    stage: "Emerging",
    audience: "College Wellness",
    platform: "TikTok",
    format: "UGC Tutorial",
    product: "Hydra Electrolyte Mix",
    reasoning:
      "Simple morning rituals resonate with wellness-minded students seeking an achievable start to their day.",
    hook: "My morning routine starts before my first scroll.",
    cta: "Make hydration your first move.",
    color: "lavender",
  },
];
export const trends: Trend[] = [
  {
    name: "Sunday Reset",
    growth: 218,
    volume: "High",
    match: 92,
    relevance: 89,
    stage: "Rising",
  },
  {
    name: "Run Clubs",
    growth: 146,
    volume: "High",
    match: 87,
    relevance: 94,
    stage: "Rising",
  },
  {
    name: "Protein Coffee",
    growth: 121,
    volume: "Medium",
    match: 78,
    relevance: 72,
    stage: "Emerging",
  },
  {
    name: "Morning Shed",
    growth: 98,
    volume: "High",
    match: 71,
    relevance: 42,
    stage: "Peak",
  },
  {
    name: "Cold Plunge",
    growth: -12,
    volume: "Low",
    match: 54,
    relevance: 63,
    stage: "Declining",
  },
];
export const scanTrend: Trend = {
  name: "Desk-to-Gym Ritual",
  growth: 76,
  volume: "Medium",
  match: 86,
  relevance: 91,
  stage: "Emerging",
};
export const audience: AudienceSegment[] = [
  {
    name: "College Wellness",
    age: "18–24",
    share: 46,
    customers: "5,906",
    revenue: 58400,
    channel: "TikTok",
    content: "UGC",
    interests: ["Fitness", "Wellness", "Productivity", "Lifestyle"],
    color: "#28775b",
  },
  {
    name: "Active Professionals",
    age: "25–34",
    share: 34,
    customers: "4,365",
    revenue: 48200,
    channel: "Instagram",
    content: "Creator demonstrations",
    interests: ["Running", "Fitness", "Community"],
    color: "#adc7b1",
  },
  {
    name: "Search-Driven Buyers",
    age: "22–40",
    share: 20,
    customers: "2,567",
    revenue: 28600,
    channel: "Google Search",
    content: "Product comparisons",
    interests: ["Nutrition", "Value", "Product research"],
    color: "#e8bda0",
  },
];
export const trendHistory = Array.from({ length: 30 }, (_, i) => ({
  day: i < 17 ? `Aug ${i + 15}` : `Sep ${i - 16}`,
  interest: Math.round(
    22 + i * 1.8 + (i > 17 ? (i - 17) * 4 : 0) + Math.sin(i * 1.4) * 5,
  ),
}));
export const initialActivity: AgentActivity[] = [
  {
    id: "a1",
    time: "10:42 AM",
    category: "Analysis",
    title: "Your audience, a little clearer",
    description:
      "Analyzed 1,284 recent customer purchases. College Wellness remains your highest-converting segment.",
  },
  {
    id: "a2",
    time: "10:40 AM",
    category: "Research",
    title: "Spotted a signal: Sunday Reset",
    description:
      "Interest increased 218%. Hydration is showing up alongside wellness and productivity.",
  },
  {
    id: "a3",
    time: "10:37 AM",
    category: "Decision",
    title: "Found the right fit for Hydra",
    description:
      "Compared 24 emerging trends. Sunday Reset: 92% audience match, 89% brand relevance. Recommendation: build a campaign.",
  },
  {
    id: "a4",
    time: "10:32 AM",
    category: "Analysis",
    title: "Learned from your last campaigns",
    description:
      "Creator-led videos drove 2.4× more engagement than product-only creative.",
  },
  {
    id: "a5",
    time: "10:28 AM",
    category: "Action",
    title: "Generated a campaign strategy",
    description:
      "Recommended TikTok UGC for College Wellness, featuring Hydra Electrolyte Mix.",
  },
];
export const integrations: Integration[] = [
  {
    name: "Shopify",
    category: "Customer Data",
    connected: true,
    description: "Purchase patterns, products, and customer segments.",
    letter: "S",
    color: "#80a846",
  },
  {
    name: "HubSpot",
    category: "Customer Data",
    connected: false,
    description: "Understand your contacts and customer lifecycle.",
    letter: "H",
    color: "#eb815d",
  },
  {
    name: "Google Trends",
    category: "Trend Intelligence",
    connected: true,
    description: "Discover what your audience is searching for.",
    letter: "G",
    color: "#5387df",
  },
  {
    name: "TikTok",
    category: "Trend Intelligence",
    connected: true,
    description: "Spot emerging conversations and creator formats.",
    letter: "T",
    color: "#292b32",
  },
  {
    name: "Reddit",
    category: "Trend Intelligence",
    connected: true,
    description: "Follow communities and authentic conversations.",
    letter: "R",
    color: "#e97645",
  },
  {
    name: "Canva",
    category: "Creative",
    connected: false,
    description: "Turn campaign concepts into branded creative.",
    letter: "C",
    color: "#59aaa4",
  },
  {
    name: "TikTok Ads",
    category: "Distribution",
    connected: false,
    description: "Bring approved short-form campaigns to your audience.",
    letter: "T",
    color: "#292b32",
  },
  {
    name: "Meta Ads",
    category: "Distribution",
    connected: false,
    description: "Reach your customers on Instagram and Facebook.",
    letter: "M",
    color: "#5387df",
  },
];
export function createCampaign(o: Opportunity): Campaign {
  return {
    id: `campaign-${o.id}`,
    opportunityId: o.id,
    name: `${o.name} — Hydra Electrolyte Mix`,
    audience: o.audience,
    platform: o.platform,
    format: o.format,
    objective: "Product Awareness + Conversion",
    concept:
      o.id === "sunday"
        ? "A casual creator walks through their Sunday reset routine: cleaning, planning workouts, preparing for Monday, and mixing Hydra for the next morning."
        : `A creator brings viewers into their ${o.name.toLowerCase()} ritual and naturally introduces Hydra as their hydration companion.`,
    hook: o.hook,
    script:
      o.id === "sunday"
        ? "[0–4s · Hook] 3 things I do Sunday night so Monday doesn’t destroy me.\n\n[4–11s · Reset] First, a ten-minute room reset. Clear space, clear head.\n\n[11–18s · Plan] Then I plan my workouts and pack my bag. Future me says thank you.\n\n[18–25s · Hydrate] Last step: water, ice, and my favorite Hydra electrolyte mix. One small ritual I actually look forward to.\n\n[25–28s · CTA] Start your week hydrated. Try Hydra."
        : `[0–5s · Hook] ${o.hook}\n\n[5–15s · Routine] Come along for my ${o.name.toLowerCase()}. A little movement, a little time for myself.\n\n[15–24s · Product] Water, ice, Hydra. My simple hydration ritual.\n\n[24–28s · CTA] ${o.cta}`,
    cta: o.cta,
    caption: `A little ${o.name.toLowerCase()}, a better start. Find your hydration ritual with Hydra.`,
    hashtags: `#${o.name.replaceAll(" ", "")} #Hydra #HydrationRoutine #Wellness`,
    notes:
      "Vertical 9:16 · 20–30 seconds · Natural window light · Handheld creator footage · Add captions · Show product mixing close-up.",
    status: "Draft",
  };
}
export const initialCampaigns: Campaign[] = [
  {
    ...createCampaign(opportunities[1]),
    id: "past-run",
    name: "After the finish line",
    status: "Active",
    ctr: "3.8%",
    conversions: 142,
    cpa: "$8.42",
    engagement: "6.2%",
    roas: "3.4×",
  },
  {
    ...createCampaign(opportunities[2]),
    id: "past-morning",
    name: "Your first good decision",
    status: "Completed",
    ctr: "4.1%",
    conversions: 286,
    cpa: "$7.18",
    engagement: "7.4%",
    roas: "4.2×",
  },
  {
    ...createCampaign(opportunities[2]),
    id: "draft-morning",
    name: "A better kind of morning",
    status: "Draft",
  },
];
export const promptSuggestions = [
  "Find opportunities for our electrolyte mix",
  "What is trending among college students?",
  "Build a TikTok campaign for our highest-value audience",
  "Why does Sunday Reset fit Hydra?",
];
export function mockReply(question: string) {
  const q = question.toLowerCase();
  if (q.includes("why") || q.includes("fit"))
    return "Sunday Reset matches 92% of College Wellness interests and has 89% brand relevance. Hydration appears naturally alongside planning and wellness. I recommend a creator-led TikTok showing Hydra as the final step in a Sunday routine.";
  if (q.includes("build") || q.includes("campaign"))
    return "I have a campaign direction ready: a 28-second TikTok UGC video for College Wellness. Hook: “3 things I do Sunday night so Monday doesn’t destroy me.” Open the opportunity below to review and build it.";
  if (q.includes("trend") || q.includes("college"))
    return "Sunday Reset is up 218%, followed by Run Clubs at 146% and Protein Coffee at 121%. Sunday Reset is the strongest match for College Wellness, with a 91/100 opportunity score.";
  return "Your strongest opportunity is Sunday Reset: +218% growth and 92% audience match. Pair Hydra Electrolyte Mix with a relatable TikTok UGC routine. Run Clubs and Morning Routine are also worth exploring.";
}
export const alternateHooks = [
  "My Monday starts with what I do on Sunday.",
  "Your next good week starts with one small ritual.",
];
