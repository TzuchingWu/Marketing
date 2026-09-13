import { useState } from "react";
import {
  ArrowRight,
  Search,
  Radar,
  TrendingUp,
  Sprout,
  Mountain,
  TrendingDown,
  RefreshCw,
  Link2,
  Check,
  Plus,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
} from "recharts";
import { audience } from "../data/mockData";
import type {
  Opportunity,
  Trend,
  Campaign,
  CampaignStatus,
  Integration,
  AgentActivity,
} from "../types";
import {
  OpportunityCard,
  EmptyState,
  SectionTitle,
  Badge,
  ActivityFeed,
} from "../components/ui";
export function Opportunities({
  items,
  onView,
  onBuild,
  onDismiss,
  onRestore,
}: {
  items: Opportunity[];
  onView: (o: Opportunity) => void;
  onBuild: (o: Opportunity) => void;
  onDismiss: (id: string) => void;
  onRestore: () => void;
}) {
  const [query, setQuery] = useState("");
  const filtered = items.filter((o) =>
    `${o.name} ${o.audience} ${o.platform}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  return (
    <>
      <div className="toolbar">
        <label className="search-field">
          <Search size={16} />
          <input
            placeholder="Search opportunities…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <span className="muted">{items.length} curated opportunities</span>
        {items.length < 3 && (
          <button className="btn compact" onClick={onRestore}>
            Restore dismissed
          </button>
        )}
      </div>
      <div className="opportunity-grid">
        {filtered.map((o) => (
          <OpportunityCard
            key={o.id}
            opportunity={o}
            onView={() => onView(o)}
            onBuild={() => onBuild(o)}
            onDismiss={() => onDismiss(o.id)}
          />
        ))}
      </div>
      {!filtered.length && (
        <EmptyState
          title="You’re all caught up"
          description="Try a different search or restore dismissed opportunities."
        />
      )}
    </>
  );
}
export function Audience() {
  return (
    <>
      <div className="audience-summary">
        <div>
          <div className="eyebrow">THE PEOPLE BEHIND THE PURCHASES</div>
          <h2>Different people. Shared potential.</h2>
          <p>12,838 customers, organized into three meaningful audiences.</p>
        </div>
        <Badge>Mock Shopify insights</Badge>
      </div>
      <div className="audience-grid">
        {audience.map((a, i) => (
          <section className="panel audience-card" key={a.name}>
            <div className="flex justify-between">
              <div className="segment-avatar" style={{ background: a.color }}>
                {["CW", "AP", "SB"][i]}
              </div>
              <Badge tone="neutral">{a.share}% of audience</Badge>
            </div>
            <h3>{a.name}</h3>
            <p className="muted">
              Age {a.age} · {a.customers} customers
            </p>
            <div className="audience-facts">
              <div>
                <span>Best channel</span>
                <strong>{a.channel}</strong>
              </div>
              <div>
                <span>Best content</span>
                <strong>{a.content}</strong>
              </div>
            </div>
            <div className="tags">
              {a.interests.map((x) => (
                <span key={x}>{x}</span>
              ))}
            </div>
          </section>
        ))}
      </div>
      <div className="two-columns">
        <section className="panel">
          <SectionTitle title="Audience distribution" />
          <div className="distribution">
            <div className="pie-chart">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={audience}
                    dataKey="share"
                    nameKey="name"
                    innerRadius={65}
                    outerRadius={90}
                    paddingAngle={4}
                  >
                    {audience.map((a) => (
                      <Cell key={a.name} fill={a.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => `${v}%`} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div>
              {audience.map((a) => (
                <div className="legend" key={a.name}>
                  <i style={{ background: a.color }} />
                  {a.name}
                  <b>{a.share}%</b>
                </div>
              ))}
            </div>
          </div>
        </section>
        <section className="panel">
          <SectionTitle title="Revenue by segment">
            <Badge tone="neutral">Last 30 days</Badge>
          </SectionTitle>
          <div className="chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={audience}
                layout="vertical"
                margin={{ left: 0, right: 20 }}
              >
                <XAxis
                  type="number"
                  tickFormatter={(v) => `$${v / 1000}k`}
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 11 }}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={125}
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 11 }}
                />
                <Tooltip formatter={(v) => `$${Number(v).toLocaleString()}`} />
                <Bar dataKey="revenue" radius={[0, 5, 5, 0]} barSize={28}>
                  {audience.map((a) => (
                    <Cell key={a.name} fill={a.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>
    </>
  );
}
export function Trends({
  items,
  onScan,
  scanned,
  onView,
}: {
  items: Trend[];
  onScan: () => void;
  scanned: boolean;
  onView: () => void;
}) {
  const [filter, setFilter] = useState("All trends");
  const [source, setSource] = useState("TikTok");
  return (
    <>
      <div className="platform-widgets" role="group" aria-label="Trend research sources">
        {[{name:'TikTok',slug:'tiktok',detail:'Creator videos'}, {name:'Google',slug:'google',detail:'Search interest'}, {name:'Reddit',slug:'reddit',detail:'Community conversations'}, {name:'Instagram',slug:'instagram',detail:'Reels and visual culture'}].map(p => <button key={p.slug} aria-pressed={source===p.name} className={source===p.name?'selected':''} onClick={()=>setSource(p.name)}><img src={`/brands/${p.slug}.svg`} alt="" width="40" height="40"/><strong>{p.name}</strong><span>{p.detail}</span></button>)}
      </div>
      <p className="trend-source-note">{source} research preview · Simulated source connection. The radar below combines all demo trends.</p>
      <section className="panel">
        <SectionTitle
          eyebrow="CULTURE MOVES. PULSE LISTENS."
          title="Your trend radar"
        >
          <button
            className="btn primary compact"
            onClick={onScan}
            disabled={scanned}
          >
            <RefreshCw size={14} />
            {scanned ? "Scan complete" : "Scan trends"}
          </button>
        </SectionTitle>
        <div className="toolbar">
          <div className="tabs" aria-label="Filter trends by stage">{['All trends','Rising','Emerging','Peak','Declining'].map(stage=><button key={stage} className={filter===stage?'active':''} onClick={()=>setFilter(stage)}>{stage}</button>)}</div>
          <span className="muted">
            {scanned ? "Updated just now" : "Last scanned at 10:40 AM"} ·
            Simulated sources
          </span>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                {[
                  "Trend",
                  "Growth",
                  "Volume",
                  "Audience fit",
                  "Brand fit",
                  "Stage",
                  "",
                ].map((x, i) => (
                  <th key={i}>{x}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items
                .filter((t) => filter === "All trends" || t.stage === filter)
                .map((t) => (
                  <tr key={t.name}>
                    <td>
                      <strong>{t.name}</strong>
                    </td>
                    <td className={t.growth > 0 ? "green-text" : "muted"}>
                      {t.growth > 0 ? "+" : ""}
                      {t.growth}%
                    </td>
                    <td>{t.volume}</td>
                    <td>{t.match}%</td>
                    <td>{t.relevance}%</td>
                    <td>
                      <Badge
                        tone={
                          t.stage === "Declining"
                            ? "neutral"
                            : t.stage === "Peak"
                              ? "amber"
                              : "green"
                        }
                      >
                        {t.stage}
                      </Badge>
                    </td>
                    <td>
                      {t.name === "Sunday Reset" && (
                        <button
                          className="icon-button"
                          aria-label="View Sunday Reset opportunity"
                          onClick={onView}
                        >
                          <ArrowRight size={17} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>
      <div className="insight mt-5">
        <Radar size={20} />
        <p>
          Pulse compares cultural momentum with your customer interests. High
          growth matters most when the audience and brand fit are right.
        </p>
      </div>
    </>
  );
}
export function Campaigns({
  items,
  tab,
  setTab,
  onOpen,
  onNew,
}: {
  items: Campaign[];
  tab: CampaignStatus;
  setTab: (s: CampaignStatus) => void;
  onOpen: (c: Campaign) => void;
  onNew: () => void;
}) {
  return (
    <>
      <div className="toolbar">
        <div className="tabs">
          {(
            [
              "Draft",
              "Approved",
              "Active",
              "Completed",
              "Rejected",
            ] as CampaignStatus[]
          ).map((t) => (
            <button
              key={t}
              className={tab === t ? "active" : ""}
              onClick={() => setTab(t)}
            >
              {t}
              <span>{items.filter((c) => c.status === t).length}</span>
            </button>
          ))}
        </div>
        <button className="btn primary compact" onClick={onNew}>
          <Plus size={15} />
          New campaign
        </button>
      </div>
      <div className="campaign-list">
        {items
          .filter((c) => c.status === tab)
          .map((c) => (
            <section className="panel campaign-row" key={c.id}>
              <div className="flex gap-4 items-start">
                <div className="campaign-icon">
                  <Link2 size={22} />
                </div>
                <div>
                  <Badge
                    tone={
                      c.status === "Draft"
                        ? "amber"
                        : c.status === "Rejected"
                          ? "red"
                          : "green"
                    }
                  >
                    {c.status}
                  </Badge>
                  <h3>{c.name}</h3>
                  <p className="muted">
                    {c.platform} · {c.format} · {c.audience}
                  </p>
                </div>
                <button
                  className="btn compact ml-auto"
                  onClick={() => onOpen(c)}
                >
                  {c.status === "Draft" ? "Review campaign" : "View campaign"}
                  <ArrowRight size={14} />
                </button>
              </div>
              <div className="performance">
                {[
                  ["CTR", c.ctr],
                  ["Conversions", c.conversions],
                  ["CPA", c.cpa],
                  ["Engagement", c.engagement],
                  ["ROAS", c.roas],
                ].map(([l, v]) => (
                  <div key={l}>
                    <span>{l}</span>
                    <strong>{v ?? "—"}</strong>
                  </div>
                ))}
              </div>
              {!c.ctr && (
                <small className="muted">
                  Performance will appear after a future launch. This demo does
                  not publish campaigns.
                </small>
              )}
            </section>
          ))}
      </div>
      {!items.some((c) => c.status === tab) && (
        <EmptyState
          title={`No ${tab.toLowerCase()} campaigns yet`}
          description={
            tab === "Approved"
              ? "Build a campaign from an opportunity and approve it to see it here."
              : "Your campaigns will appear here as their status changes."
          }
        >
          <button className="btn primary" onClick={onNew}>
            Explore opportunities
            <ArrowRight size={15} />
          </button>
        </EmptyState>
      )}
    </>
  );
}
export function AgentActivityPage({ items }: { items: AgentActivity[] }) {
  const [filter, setFilter] = useState("All activity");
  return (
    <>
      <div className="agent-banner">
        <div className="banner-icon">
          <Radar />
        </div>
        <div>
          <strong>A little less busywork. A lot more possibility.</strong>
          <p>
            See what Pulse discovered, how it reasoned, and what it recommends
            next.
          </p>
        </div>
        <Badge>Simulated activity</Badge>
      </div>
      <div className="tabs mb-5">
        {["All activity", "Research", "Analysis", "Decision", "Action"].map(
          (x) => (
            <button
              key={x}
              className={x === filter ? "active" : ""}
              onClick={() => setFilter(x)}
            >
              {x}
            </button>
          ),
        )}
      </div>
      <section className="panel activity-page">
        <div className="eyebrow mb-5">TODAY · DEMO SESSION</div>
        <ActivityFeed
          items={items.filter(
            (a) => filter === "All activity" || a.category === filter,
          )}
        />
      </section>
    </>
  );
}
export function Integrations({
  items,
  onToggle,
}: {
  items: Integration[];
  onToggle: (name: string) => void;
}) {
  return (
    <>
      <div className="integration-banner">
        <Link2 size={21} />
        <div>
          <strong>Your tools. One connected picture.</strong>
          <p>
            Preview how Pulse will connect your customer insights, trends, and
            creative. All connections below are simulated.
          </p>
        </div>
        <Badge tone="neutral">Demo mode</Badge>
      </div>
      {["Customer Data", "Trend Intelligence", "Creative", "Distribution"].map(
        (group) => (
          <section className="integration-group" key={group}>
            <SectionTitle title={group} />
            <div className="integration-grid">
              {items
                .filter((i) => i.category === group)
                .map((i) => (
                  <article className="panel integration-card" key={i.name}>
                    <div className="flex justify-between items-center">
                      <span
                        className="integration-logo"
                        style={{ background: i.color }}
                      >
                        {i.letter}
                      </span>
                      <Badge tone={i.connected ? "green" : "neutral"}>
                        {i.connected ? "Connected" : "Not Connected"}
                      </Badge>
                    </div>
                    <h3>{i.name}</h3>
                    <p>{i.description}</p>
                    <button
                      className={`btn w-full ${i.connected ? "" : "connect"}`}
                      onClick={() => onToggle(i.name)}
                    >
                      {i.connected ? <Check size={14} /> : <Plus size={14} />}{" "}
                      {i.connected
                        ? `Disconnect ${i.name}`
                        : `Connect ${i.name}`}
                    </button>
                  </article>
                ))}
            </div>
          </section>
        ),
      )}
    </>
  );
}
