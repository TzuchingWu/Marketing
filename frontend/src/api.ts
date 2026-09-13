import type {
  AnalyzedBusiness,
  BusinessInput,
  DiscoverResult,
  IntegrationStatus,
  LogOutreachResult,
  PresenceResult,
  RecommendResult,
  VideoAdResult,
  VideoScript,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

// Video ad generation is a real async job on Google's end (submit + poll,
// can take a few minutes) -- everything else is a normal fast request.
const DEFAULT_TIMEOUT_MS = 30_000;
const VIDEO_AD_TIMEOUT_MS = 200_000;

async function request<T>(path: string, options: RequestInit, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${BASE_URL}${path}`, { ...options, signal: controller.signal });
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const body = await response.json();
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
      } catch {
        // response body wasn't JSON -- fall back to statusText
      }
      throw new Error(detail);
    }
    return (await response.json()) as T;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s`);
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

function post<T>(path: string, body: unknown, timeoutMs?: number): Promise<T> {
  return request<T>(
    path,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) },
    timeoutMs,
  );
}

function get<T>(path: string): Promise<T> {
  return request<T>(path, { method: "GET" });
}

export function health(): Promise<{ status: string; mcp_tools: string[] }> {
  return get("/api/health");
}

export function integrationsStatus(): Promise<IntegrationStatus> {
  return get("/api/integrations/status");
}

/** General-search entry point: extract intent from free text and search
 * Google Places for real matching businesses in one call. */
export function discoverBusiness(query: string): Promise<DiscoverResult> {
  return post("/api/business/discover", { query }, 20_000);
}

/** The main "Find My Creators" action -- runs the full discovery workflow
 * through the real MCP server and returns creators, campaign, and the
 * agent's tool-call activity log all at once. Agentic mode can make many
 * sequential LLM calls (one per creator explanation, plus the agent's own
 * reasoning turns), so this needs real headroom beyond the default timeout. */
export function recommend(business: BusinessInput): Promise<RecommendResult> {
  return post("/api/agent/recommend", business, 120_000);
}

export function analyzeBusiness(business: BusinessInput): Promise<AnalyzedBusiness & { business_id: string }> {
  return post("/api/business/analyze", business);
}

export function analyzePresence(businessId: string): Promise<PresenceResult> {
  return post(`/api/business/${encodeURIComponent(businessId)}/presence`, {});
}

export interface OutreachBusiness {
  name: string;
  description: string;
  goal: string;
  location: string;
}
export interface OutreachCreator {
  handle: string;
  name: string;
  category: string[];
  location: string;
}

export function generateOutreach(
  business: OutreachBusiness,
  creator: OutreachCreator,
  offer: string,
  tone = "friendly",
): Promise<{ message: string }> {
  return post("/api/outreach/generate", { business, creator, offer, tone });
}

export function logOutreach(args: {
  creator_handle: string;
  creator_name: string;
  platform: string;
  business_name: string;
  offer: string;
  message: string;
}): Promise<LogOutreachResult> {
  return post("/api/outreach/log", args);
}

export function generateVideoScript(
  business: { business_name: string; business_category: string; location: string },
  content_idea: string,
  platform = "TikTok / Instagram Reels",
  duration_seconds = 30,
): Promise<VideoScript> {
  return post("/api/video/script", { business, content_idea, platform, duration_seconds });
}

export function generateVideoAd(args: {
  business_id: string;
  offer: string;
  target_audience: string;
  style?: string;
  duration_seconds?: number;
}): Promise<VideoAdResult> {
  return post("/api/video/ad", args, VIDEO_AD_TIMEOUT_MS);
}
