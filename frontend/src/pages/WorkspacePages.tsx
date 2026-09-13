import { useState } from "react";
import { Radar, Link2, Check, X, Loader2 } from "lucide-react";
import type { AgentActivityItem, IntegrationStatus } from "../types";
import { ActivityFeed, Badge } from "../components/ui";

export function AgentActivityPage({ items }: { items: AgentActivityItem[] }) {
  const [filter, setFilter] = useState("All activity");
  return (
    <>
      <div className="agent-banner">
        <div className="banner-icon">
          <Radar />
        </div>
        <div>
          <strong>A transparent look at your marketing agent at work.</strong>
          <p>Every entry here is a real MCP tool call made against the OUTTHERE server -- not simulated.</p>
        </div>
        <Badge tone={items.length ? "green" : "neutral"}>{items.length ? "Live" : "No activity yet"}</Badge>
      </div>
      {items.length > 0 && (
        <div className="tabs mb-5">
          {["All activity", "Research", "Analysis", "Decision", "Action"].map((x) => (
            <button key={x} className={x === filter ? "active" : ""} onClick={() => setFilter(x)}>
              {x}
            </button>
          ))}
        </div>
      )}
      <section className="panel activity-page">
        <div className="eyebrow mb-5">MOST RECENT SEARCH</div>
        {items.length ? (
          <ActivityFeed items={items.filter((a) => filter === "All activity" || a.category === filter)} />
        ) : (
          <p className="muted">Run a search from Home to see the agent's tool-call activity here.</p>
        )}
      </section>
    </>
  );
}

const INTEGRATION_INFO: { key: keyof IntegrationStatus; name: string; description: string }[] = [
  {
    key: "anthropic",
    name: "Anthropic (Claude)",
    description: "Lets the agent choose which MCP tools to call and generates richer explanations, outreach, and campaign copy. Falls back to deterministic templates when off.",
  },
  {
    key: "google_maps",
    name: "Google Places",
    description: "Validates businesses against real Google data (rating, reviews, address) and finds real nearby competitors. Falls back to simulated presence data when off.",
  },
  {
    key: "hubspot",
    name: "HubSpot CRM",
    description: "Logs outreach as CRM contacts + notes so status across many creators can be tracked. Never sends anything itself.",
  },
  {
    key: "veo",
    name: "Google Veo",
    description: "Generates a real short AI video ad from the campaign concept. Async job, real per-clip cost -- explicitly opt-in.",
  },
];

export function Integrations({ status }: { status: IntegrationStatus | null; loading?: boolean }) {
  return (
    <>
      <div className="integration-banner">
        <Link2 size={21} />
        <div>
          <strong>Your tools. One connected picture.</strong>
          <p>Real configured status, read from the backend -- not a toggle. Set API keys in the backend's .env to enable one.</p>
        </div>
        <Badge tone="neutral">{status ? "Live status" : "Loading..."}</Badge>
      </div>
      <div className="integration-status-grid">
        {INTEGRATION_INFO.map((i) => {
          const connected = status?.[i.key] ?? false;
          return (
            <article className="panel integration-card" key={i.key}>
              <div className="flex justify-between items-center">
                <h3 style={{ margin: 0, fontSize: 16 }}>{i.name}</h3>
                {status === null ? (
                  <Loader2 size={16} className="working-icon" />
                ) : (
                  <span className={`status-pill ${connected ? "ok" : "off"}`}>
                    {connected ? <Check size={14} /> : <X size={14} />}
                    {connected ? "Configured" : "Not configured"}
                  </span>
                )}
              </div>
              <p className="muted mt-2">{i.description}</p>
            </article>
          );
        })}
      </div>
    </>
  );
}
