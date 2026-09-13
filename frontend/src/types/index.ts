export interface Opportunity {
  id: string;
  name: string;
  growth: number;
  match: number;
  relevance: number;
  score: number;
  momentum: number;
  stage: string;
  audience: string;
  platform: string;
  format: string;
  product: string;
  reasoning: string;
  hook: string;
  cta: string;
  color: string;
}
export interface Trend {
  name: string;
  growth: number;
  volume: string;
  match: number;
  relevance: number;
  stage: string;
}
export interface AudienceSegment {
  name: string;
  age: string;
  share: number;
  customers: string;
  revenue: number;
  channel: string;
  content: string;
  interests: string[];
  color: string;
}
export type CampaignStatus =
  "Draft" | "Approved" | "Active" | "Completed" | "Rejected";
export interface Campaign {
  id: string;
  opportunityId: string;
  name: string;
  audience: string;
  platform: string;
  format: string;
  objective: string;
  concept: string;
  hook: string;
  script: string;
  cta: string;
  caption: string;
  hashtags: string;
  notes: string;
  status: CampaignStatus;
  ctr?: string;
  conversions?: number;
  cpa?: string;
  engagement?: string;
  roas?: string;
}
export interface AgentActivity {
  id: string;
  time: string;
  category: "Research" | "Analysis" | "Decision" | "Action";
  title: string;
  description: string;
}
export interface Integration {
  name: string;
  category: string;
  connected: boolean;
  description: string;
  letter: string;
  color: string;
}
export type Page =
  | "Overview"
  | "Opportunities"
  | "Opportunity Detail"
  | "Audience"
  | "Trends"
  | "Campaign Builder"
  | "Campaigns"
  | "Agent Activity"
  | "Integrations";
