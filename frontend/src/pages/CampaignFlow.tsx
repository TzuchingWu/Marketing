import {
  ArrowLeft,
  ArrowRight,
  Check,
  RotateCcw,
  Pencil,
  Target,
  Users,
  Play,
} from "lucide-react";
import type { Opportunity, Campaign } from "../types";
import {
  Badge,
  SectionTitle,
  TrendChart,
  OpportunityArt,
} from "../components/ui";
export function OpportunityDetail({
  opportunity: o,
  onBuild,
  onBack,
}: {
  opportunity: Opportunity;
  onBuild: () => void;
  onBack: () => void;
}) {
  return (
    <>
      <button className="text-button mb-5" onClick={onBack}>
        <ArrowLeft size={15} />
        All opportunities
      </button>
      <div className="detail-heading">
        <div>
          <Badge>{o.stage}</Badge>
          <h1>{o.name}</h1>
          <p>A timely conversation. A natural place for Hydra.</p>
        </div>
        <button className="btn primary" onClick={onBuild}>
          <Target size={16} />
          Build This Campaign
          <ArrowRight size={16} />
        </button>
      </div>
      <div className="detail-metrics">
        {[
          ["Trend growth", `+${o.growth}%`],
          ["Opportunity score", `${o.score}/100`],
          ["Audience fit", `${o.match}%`],
          ["Brand fit", `${o.relevance}%`],
          ["Momentum", `${o.momentum}%`],
        ].map(([l, v]) => (
          <div className="metric" key={l}>
            <span>{l}</span>
            <strong>{v}</strong>
          </div>
        ))}
      </div>
      <div className="detail-grid">
        <section className="panel">
          <SectionTitle title="From a trend to an opportunity">
            <Badge tone="neutral">30 days</Badge>
          </SectionTitle>
          <p className="muted">
            {o.name === "Sunday Reset"
              ? "Sunday Reset relative search interest"
              : "Illustrative 30-day momentum pattern"}{" "}
            · Mock trend data
          </p>
          <TrendChart />
          <div className="insight">
            <Target size={20} />
            <div>
              <strong>Why Pulse sees potential</strong>
              <p>{o.reasoning}</p>
            </div>
          </div>
        </section>
        <section className="panel">
          <SectionTitle title="The right people" />
          <div className="audience-icon">
            <Users size={24} />
          </div>
          <h3>{o.audience}</h3>
          <p className="muted">
            {o.id === "run"
              ? "Active professionals · Age 25–34"
              : "College students and young professionals · Age 18–26"}
          </p>
          <div className="tags mt-5">
            {["Fitness", "Wellness", "Productivity", "Lifestyle"].map((x) => (
              <span key={x}>{x}</span>
            ))}
          </div>
          <hr />
          <span className="eyebrow">PREFERRED CONTENT</span>
          <p>UGC, short-form video, creator recommendations</p>
          <div className="fit-bar">
            <span style={{ width: `${o.match}%` }} />
          </div>
          <small className="green-text">{o.match}% audience alignment</small>
        </section>
      </div>
      <section className="panel recommendation">
        <div>
          <div className="eyebrow">FROM YOUR MARKETING AGENT</div>
          <h2>
            <Target size={21} />
            The Pulse recommendation
          </h2>
          <div className="recommendation-facts">
            <div>
              <span>Platform</span>
              <strong>{o.platform}</strong>
            </div>
            <div>
              <span>Content format</span>
              <strong>{o.format}</strong>
            </div>
            <div>
              <span>Campaign angle</span>
              <strong>{o.name} Routine</strong>
            </div>
            <div>
              <span>Product</span>
              <strong>{o.product}</strong>
            </div>
          </div>
          <blockquote>“{o.hook}”</blockquote>
          <p className="muted">CTA: {o.cta}</p>
          <button className="btn primary mt-5" onClick={onBuild}>
            Build This Campaign
            <ArrowRight size={16} />
          </button>
        </div>
        <OpportunityArt opportunity={o} />
      </section>
    </>
  );
}
export function CampaignBuilder({
  campaign: c,
  editing,
  onEdit,
  onChange,
  onRegenerate,
  onApprove,
  onReject,
  onBack,
}: {
  campaign: Campaign;
  editing: boolean;
  onEdit: () => void;
  onChange: (c: Campaign) => void;
  onRegenerate: () => void;
  onApprove: () => void;
  onReject: () => void;
  onBack: () => void;
}) {
  const fields: {
    key:
      "concept" | "hook" | "script" | "cta" | "caption" | "hashtags" | "notes";
    label: string;
  }[] = [
    { key: "concept", label: "Creative concept" },
    { key: "hook", label: "The hook" },
    { key: "script", label: "UGC script · 28 seconds" },
    { key: "cta", label: "Call to action" },
    { key: "caption", label: "Caption" },
    { key: "hashtags", label: "Hashtags" },
    { key: "notes", label: "Creative notes" },
  ];
  return (
    <>
      <button className="text-button mb-5" onClick={onBack}>
        <ArrowLeft size={15} />
        Back to campaigns
      </button>
      <div className="builder-title">
        <div>
          <div className="eyebrow">CAMPAIGN STUDIO</div>
          <h1>{c.name}</h1>
        </div>
        <Badge
          tone={
            c.status === "Rejected"
              ? "red"
              : c.status === "Draft"
                ? "amber"
                : "green"
          }
        >
          {c.status}
        </Badge>
      </div>
      <div className="steps">
        <span>
          <Check size={14} />
          Opportunity discovered
        </span>
        <i />
        <span>
          <Check size={14} />
          Strategy generated
        </span>
        <i />
        <span className={c.status === "Approved" ? "" : "current"}>
          {c.status === "Approved" ? (
            <Check size={14} />
          ) : (
            <span className="step-number">3</span>
          )}
          {c.status === "Approved" ? "Campaign approved" : "Review & approve"}
        </span>
      </div>
      <div className="builder-grid">
        <section className="panel creative-panel">
          <SectionTitle title="An idea, ready for your voice">
            <div className="flex gap-2">
              <button
                className="btn compact"
                onClick={onRegenerate}
                disabled={c.status === "Active" || c.status === "Completed"}
              >
                <RotateCcw size={14} />
                Regenerate
              </button>
              <button
                className="btn compact"
                onClick={onEdit}
                disabled={c.status === "Active" || c.status === "Completed"}
              >
                <Pencil size={14} />
                {editing ? "Save edits" : "Edit"}
              </button>
            </div>
          </SectionTitle>
          {editing && (
            <div className="edit-notice">
              Editing creates a draft for a fresh review. Your changes stay in
              this demo session.
            </div>
          )}
          {fields.map((f) => (
            <div
              className={`creative-field ${f.key === "hook" ? "hook-field" : ""}`}
              key={f.key}
            >
              <label htmlFor={`field-${f.key}`}>{f.label}</label>
              {editing ? (
                <textarea
                  id={`field-${f.key}`}
                  rows={f.key === "script" ? 10 : 3}
                  value={c[f.key]}
                  onChange={(e) =>
                    onChange({ ...c, [f.key]: e.target.value, status: "Draft" })
                  }
                />
              ) : (
                <p className={f.key === "script" ? "script-text" : ""}>
                  {c[f.key]}
                </p>
              )}
            </div>
          ))}
        </section>
        <aside>
          <section className="panel">
            <SectionTitle title="Campaign brief" />
            {[
              [Users, "Target audience", c.audience],
              [Play, "Platform & format", `${c.platform} · ${c.format}`],
              [Target, "Objective", c.objective],
            ].map(([Icon, label, value]) => {
              const I = Icon as typeof Users;
              return (
                <div className="brief-item" key={String(label)}>
                  <I size={18} />
                  <div>
                    <span>{String(label)}</span>
                    <strong>{String(value)}</strong>
                  </div>
                </div>
              );
            })}
            <div className="insight">
              <Target size={18} />
              <p>
                Designed around your audience’s interests, with Hydra woven
                naturally into the story.
              </p>
            </div>
          </section>
          <section className="panel approval-panel">
            <div className="eyebrow">YOU HAVE THE FINAL SAY</div>
            <h3>
              {c.status === "Approved"
                ? "Ready for what’s next."
                : "A good idea needs your go."}
            </h3>
            <p>
              {c.status === "Approved"
                ? "Your campaign is approved and saved to the Approved tab."
                : "Review the creative, make it yours, then approve when it feels right."}
            </p>
            <button
              className="btn primary w-full"
              onClick={onApprove}
              disabled={
                c.status === "Approved" ||
                c.status === "Active" ||
                c.status === "Completed"
              }
            >
              <Check size={16} />
              {c.status === "Approved"
                ? "Campaign Approved"
                : "Approve Campaign"}
            </button>
            <button
              className="btn w-full mt-2"
              onClick={onReject}
              disabled={
                c.status === "Rejected" ||
                c.status === "Active" ||
                c.status === "Completed"
              }
            >
              Reject
            </button>
            <small>Demo only. Approval does not publish or spend money.</small>
          </section>
        </aside>
      </div>
    </>
  );
}
