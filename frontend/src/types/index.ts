export interface BusinessInput {
  business_name: string;
  business_type: string;
  location: string;
  description: string;
  target_audience: string;
  goal: string;
  budget: number;
  place_id?: string | null;
}

export interface PlaceCandidate {
  place_id: string;
  name: string;
  formatted_address: string;
  rating?: number;
  user_ratings_total?: number;
  business_status: string;
  latitude?: number;
  longitude?: number;
  types: string[];
}

export interface ExtractedIntent {
  business_name: string;
  location_hint: string;
  goal: string;
  target_audience: string;
}

export interface DiscoverResult {
  extracted: ExtractedIntent;
  status: "found_one" | "found_multiple" | "not_found" | "not_configured";
  candidates: PlaceCandidate[];
}

export interface AnalyzedBusiness {
  business_id?: string;
  business_name: string;
  business_category: string;
  sub_category: string;
  location: string;
  target_age_min: number;
  target_age_max: number;
  target_interests: string[];
  marketing_goal: string;
  budget: number;
  description: string;
  google_verified: boolean;
  google_rating?: number;
  google_review_count?: number;
  formatted_address?: string;
  latitude?: number;
  longitude?: number;
  has_website?: boolean;
}

export interface ScoreBreakdown {
  locality: number;
  audience_match: number;
  content_relevance: number;
  engagement: number;
  budget_fit: number;
}

export interface CreatorMatch {
  id: string;
  creator_id: string;
  handle: string;
  name: string;
  platform: string;
  location: string;
  categories: string[];
  // Real creators (source: "youtube_api" | "web_search") only have what
  // their respective API can actually verify -- everything else comes
  // back null rather than fabricated. The demo dataset always has all of these.
  followers: number | null;
  avg_likes: number | null;
  avg_comments: number | null;
  engagement_rate: number | null;
  audience_age_range: string | null;
  audience_local_percentage: number | null;
  estimated_collaboration_cost: number | null;
  bio: string;
  fit_score: number;
  score_breakdown: ScoreBreakdown;
  strengths: string[];
  weaknesses: string[];
  recommendation: string;
  explanation: string;
  source?: "demo" | "youtube_api" | "web_search";
  source_url?: string | null;
  verified?: boolean;
}

export interface CampaignCreator {
  id: string;
  handle: string;
  name: string;
  followers: number;
  estimated_collaboration_cost: number;
  fit_score: number;
}

export interface Campaign {
  campaign_name: string;
  objective: string;
  budget: number;
  strategy: string;
  creators: CampaignCreator[];
  content_ideas: string[];
  offers: string[];
  estimated_spend: number;
  expected_reach: number;
}

export interface ActivityLogEntry {
  tool: string;
  input: Record<string, unknown>;
  summary: string;
  is_error: boolean;
}

export interface RecommendResult {
  business: AnalyzedBusiness;
  creators: CreatorMatch[];
  campaign: Campaign;
  agent_summary: string;
  mode: "agentic" | "scripted";
  activity_log: ActivityLogEntry[];
  creator_source?: "real" | "demo";
}

export interface VideoScriptScene {
  timing: string;
  shot: string;
  on_screen_text: string;
  audio_note?: string;
}

export interface VideoScript {
  platform: string;
  duration_seconds: number;
  based_on_idea: string;
  scenes: VideoScriptScene[];
  caption: string;
  hashtags: string[];
  cta: string;
}

export interface VideoAdResult {
  campaign_angle: string;
  scenes: VideoScriptScene[];
  video_prompt: string;
  video: {
    status: "not_configured" | "ready" | "failed" | "timed_out";
    video_url: string | null;
    reason: string | null;
  };
}

export interface NearbyCompetitor {
  name: string;
  place_id: string;
  rating?: number;
  user_ratings_total?: number;
  vicinity?: string;
}

export interface PresenceResult {
  google_presence: number;
  social_presence: number;
  content_consistency: number;
  overall_visibility: number;
  recommendations: string[];
  data_source: "real" | "simulated";
  nearby_competitors: NearbyCompetitor[];
}

export interface LogOutreachResult {
  logged: boolean;
  contact_id: string | null;
  reason: string | null;
}

export interface IntegrationStatus {
  anthropic: boolean;
  google_maps: boolean;
  hubspot: boolean;
  veo: boolean;
}

export interface AgentActivityItem {
  id: string;
  time: string;
  category: "Research" | "Analysis" | "Decision" | "Action";
  title: string;
  description: string;
}

export type Page = "Home" | "Results" | "Agent Activity" | "Integrations";
