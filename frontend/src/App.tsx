import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  Bell,
  ChevronDown,
  CircleHelp,
  Command,
  LayoutDashboard,
  Leaf,
  Menu,
  MessageSquare,
  Plus,
  Radio,
  Search,
  Send,
  Settings,
  Users,
  X,
  Zap,
  Link2,
  Layers,
  CheckCircle2,
} from "lucide-react";
import type {
  Page,
  Opportunity,
  Campaign,
  CampaignStatus,
  AgentActivity,
} from "./types";
import {
  opportunities as initialOpportunities,
  initialActivity,
  initialCampaigns,
  integrations as initialIntegrations,
  trends as initialTrends,
  scanTrend,
  createCampaign,
  promptSuggestions,
  mockReply,
  alternateHooks,
} from "./data/mockData";
import { Modal } from "./components/ui";
import { Overview } from "./pages/Overview";
import { OpportunityDetail, CampaignBuilder } from "./pages/CampaignFlow";
import {
  Opportunities,
  Audience,
  Trends,
  Campaigns,
  AgentActivityPage,
  Integrations,
} from "./pages/WorkspacePages";
const navigation = [
  { name: "Overview", icon: LayoutDashboard },
  { name: "Opportunities", icon: Zap },
  { name: "Audience", icon: Users },
  { name: "Trends", icon: Radio },
  { name: "Campaigns", icon: Layers },
  { name: "Agent Activity", icon: Activity },
  { name: "Integrations", icon: Link2 },
] as const;
const subtitles: Record<string, string> = {
  Overview: "Pulse is monitoring your market.",
  Opportunities: "The right moment. The right audience. Your next move.",
  Audience: "Get to know the people who make your brand grow.",
  Trends: "Stay close to what your audience cares about next.",
  Campaigns: "From promising idea to your next great campaign.",
  "Agent Activity": "A transparent look at your marketing agent at work.",
  Integrations: "Bring your marketing world together.",
};
export default function App() {
  const [page, setPage] = useState<Page>("Overview"),
    [opportunities, setOpportunities] = useState(initialOpportunities),
    [selected, setSelected] = useState(initialOpportunities[0]),
    [campaigns, setCampaigns] = useState(initialCampaigns),
    [campaignId, setCampaignId] = useState(""),
    [activities, setActivities] = useState(initialActivity),
    [integrations, setIntegrations] = useState(initialIntegrations),
    [trends, setTrends] = useState(initialTrends),
    [scanned, setScanned] = useState(false),
    [tab, setTab] = useState<CampaignStatus>("Draft"),
    [editing, setEditing] = useState(false),
    [regenerations, setRegenerations] = useState(0),
    [modal, setModal] = useState<"ask" | "settings" | "profile" | null>(null),
    [mobile, setMobile] = useState(false),
    [toast, setToast] = useState(""),
    [question, setQuestion] = useState(""),
    [messages, setMessages] = useState<
      { role: "user" | "pulse"; text: string }[]
    >([]),
    [notifications, setNotifications] = useState(true);
  const closeModal = useCallback(() => setModal(null), []);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 4500);
    return () => clearTimeout(timer);
  }, [toast]);
  function navigate(p: Page) {
    setPage(p);
    setMobile(false);
    window.scrollTo({ top: 0, behavior: "instant" });
  }
  function record(
    title: string,
    description: string,
    category: AgentActivity["category"] = "Action",
  ) {
    setActivities((a) => [
      {
        id: crypto.randomUUID(),
        time: "Just now",
        category,
        title,
        description,
      },
      ...a,
    ]);
  }
  function view(o: Opportunity) {
    setSelected(o);
    navigate("Opportunity Detail");
  }
  function build(o: Opportunity) {
    const id = `campaign-${o.id}`;
    if (!campaigns.some((c) => c.id === id)) {
      setCampaigns((c) => [createCampaign(o), ...c]);
      record(
        "Generated campaign creative",
        `${o.platform} ${o.format} for ${o.audience}. Ready for your review.`,
      );
    }
    setCampaignId(id);
    setEditing(false);
    navigate("Campaign Builder");
  }
  const campaign = campaigns.find((c) => c.id === campaignId);
  function updateCampaign(c: Campaign) {
    setCampaigns((cs) => cs.map((x) => (x.id === c.id ? c : x)));
  }
  function approve() {
    if (!campaign) return;
    updateCampaign({ ...campaign, status: "Approved" });
    setEditing(false);
    setTab("Approved");
    record(
      "Campaign approved",
      `${campaign.name} is approved. No publishing action was taken.`,
    );
    setToast("Campaign approved. Find it in Campaigns / Approved.");
  }
  function ask(text: string) {
    if (!text.trim()) return;
    setMessages((m) => [
      ...m,
      { role: "user", text: text.trim() },
      { role: "pulse", text: mockReply(text) },
    ]);
    setQuestion("");
  }
  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="global-bar"><div className="global-inner">
          <button className="pulse-wordmark" onClick={() => navigate("Overview")} aria-label="Pulse home"><img className="pulse-logo" src="/pulse-logo.webp" alt="" width="40" height="40" />Pulse</button>



          <button className="icon-button nav-toggle" aria-label={mobile ? "Close navigation" : "Open navigation"} aria-expanded={mobile} aria-controls="primary-navigation" onClick={() => setMobile(!mobile)}>{mobile ? <X size={20} /> : <Menu size={20} />}</button>
          <nav id="primary-navigation" aria-label="Primary navigation" className={mobile ? "top-navigation expanded" : "top-navigation"}>
            {navigation.map(n => {
              const active = page === n.name || (page === "Opportunity Detail" && n.name === "Opportunities") || (page === "Campaign Builder" && n.name === "Campaigns");
              return <button key={n.name} onClick={() => navigate(n.name)} className={active ? "active" : ""} aria-current={active ? "page" : undefined}>{n.name}</button>;
            })}
          </nav>
          <div className="global-actions">
            <button className="icon-button" aria-label="View recent agent activity" onClick={() => navigate("Agent Activity")}><Bell size={17} />{notifications && <span className="notification-dot" />}</button>
            <button className="icon-button" aria-label="Settings" onClick={() => setModal("settings")}><Settings size={17} /></button>
            <button className="account-link" onClick={() => setModal("profile")}>Hydra</button>
          </div>
        </div></div>
      </header>
      <div className="main-shell">
        <main>
          {!["Overview", "Opportunity Detail", "Campaign Builder"].includes(page) && (
            <div className={page === "Overview" ? "page-heading overview-hero" : "page-heading"}>
              <div>
                <h1>{page === "Overview" ? "Pulse Marketing for you" : page === "Opportunities" ? "Marketing opportunities" : page}</h1>
                <p>{page === "Overview" ? "Understand your audience. Discover what matters. Create your next campaign, all in one place." : subtitles[page]}</p>
              </div>
              {page !== "Overview" && <button className="text-button" onClick={() => setModal("ask")}>Ask Pulse<ArrowRight size={15}/></button>}
            </div>
          )}
          {page === "Overview" && (
            <Overview
              opportunities={opportunities}
              activities={activities}
              integrations={integrations}
              messages={messages}
              onAsk={ask}
              onBuild={build}
              onView={view}
              onNavigate={navigate}
            />
          )}
          {page === "Opportunities" && (
            <Opportunities
              items={opportunities}
              onView={view}
              onBuild={build}
              onDismiss={(id) => {
                setOpportunities((os) => os.filter((o) => o.id !== id));
                setToast("Opportunity dismissed. You can restore it anytime.");
                record(
                  "Opportunity dismissed",
                  `${initialOpportunities.find((o) => o.id === id)?.name} removed from your shortlist.`,
                );
              }}
              onRestore={() => {
                setOpportunities(initialOpportunities);
                setToast("All opportunities restored.");
              }}
            />
          )}
          {page === "Opportunity Detail" && (
            <OpportunityDetail
              opportunity={selected}
              onBack={() => navigate("Opportunities")}
              onBuild={() => build(selected)}
            />
          )}
          {page === "Audience" && <Audience />}
          {page === "Trends" && (
            <Trends
              items={trends}
              scanned={scanned}
              onScan={() => {
                setScanned(true);
                setTrends((t) => [...t, scanTrend]);
                record(
                  "Completed a trend scan",
                  "Found Desk-to-Gym Ritual: +76% growth, 86% audience fit.",
                  "Research",
                );
                setToast("Scan complete. 1 new mock trend discovered.");
              }}
              onView={() => view(initialOpportunities[0])}
            />
          )}
          {page === "Campaign Builder" && campaign && (
            <CampaignBuilder
              campaign={campaign}
              editing={editing}
              onEdit={() => {
                if (!editing) updateCampaign({ ...campaign, status: "Draft" });
                else setToast("Campaign edits saved.");
                setEditing(!editing);
              }}
              onChange={updateCampaign}
              onBack={() => navigate("Campaigns")}
              onApprove={approve}
              onReject={() => {
                updateCampaign({ ...campaign, status: "Rejected" });
                setEditing(false);
                setTab("Rejected");
                record("Campaign rejected", campaign.name);
                setToast("Campaign moved to Rejected.");
                navigate("Campaigns");
              }}
              onRegenerate={() => {
                const base = createCampaign(
                  initialOpportunities.find(
                    (o) => o.id === campaign.opportunityId,
                  )!,
                );
                const hook =
                  alternateHooks[regenerations % alternateHooks.length];
                updateCampaign({
                  ...campaign,
                  hook,
                  script: base.script.replace(base.hook, hook),
                  caption: `${hook} Find your daily hydration ritual with Hydra.`,
                  status: "Draft",
                });
                setRegenerations((n) => n + 1);
                record(
                  "Regenerated campaign creative",
                  "Created an alternate mock hook and script for review.",
                );
                setToast("Fresh creative generated. Ready for review.");
              }}
            />
          )}
          {page === "Campaigns" && (
            <Campaigns
              items={campaigns}
              tab={tab}
              setTab={setTab}
              onOpen={(c) => {
                setCampaignId(c.id);
                setEditing(false);
                navigate("Campaign Builder");
              }}
              onNew={() => navigate("Opportunities")}
            />
          )}
          {page === "Agent Activity" && (
            <AgentActivityPage items={activities} />
          )}
          {page === "Integrations" && (
            <Integrations
              items={integrations}
              onToggle={(name) => {
                const item = integrations.find((i) => i.name === name)!;
                setIntegrations((xs) =>
                  xs.map((x) =>
                    x.name === name ? { ...x, connected: !x.connected } : x,
                  ),
                );
                setToast(
                  `${name} ${item.connected ? "disconnected" : "connected"} in demo mode.`,
                );
                record(
                  "Updated demo connection",
                  `${name}: ${item.connected ? "Not Connected" : "Connected"}. Visual state only.`,
                );
              }}
            />
          )}
        </main>
      </div>
      {toast && (
        <div className="toast" role="status">
          <CheckCircle2 size={19} />
          {toast}
          <button
            aria-label="Dismiss notification"
            onClick={() => setToast("")}
          >
            <X size={16} />
          </button>
        </div>
      )}
      {modal === "ask" && (
        <Modal title="Ask Pulse" onClose={closeModal} drawer>
          <div className="drawer-content">
            <div className="ask-intro">
              <div className="ask-orb">
                <MessageSquare size={28} />
              </div>
              <div className="eyebrow">YOUR MARKETING CO-PILOT</div>
              <h2>What’s our next move?</h2>
              <p>
                Explore an idea, understand your audience, or turn a signal into
                a campaign.
              </p>
              <small>Demo responses · No AI or external services</small>
            </div>
            <div className="suggestions">
              {promptSuggestions.map((p) => (
                <button key={p} onClick={() => ask(p)}>
                  {p}
                  <ArrowRight size={15} />
                </button>
              ))}
            </div>
            <div className="messages" aria-live="polite">
              {messages.map((m, i) => (
                <div key={i} className={`message ${m.role}`}>
                  <strong>{m.role === "pulse" ? "Pulse" : "You"}</strong>
                  <p>{m.text}</p>
                </div>
              ))}
            </div>
            {messages.length > 0 && (
              <button
                className="btn primary"
                onClick={() => {
                  closeModal();
                  view(initialOpportunities[0]);
                }}
              >
                Explore Sunday Reset
                <ArrowRight size={15} />
              </button>
            )}
          </div>
          <form
            className="ask-form"
            onSubmit={(e) => {
              e.preventDefault();
              ask(question);
            }}
          >
            <label className="sr-only" htmlFor="ask-input">
              Ask Pulse
            </label>
            <textarea
              id="ask-input"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask Pulse to research an audience, find an opportunity, or build a campaign…"
            />
            <button
              className="icon-button"
              type="submit"
              aria-label="Send message"
              disabled={!question.trim()}
            >
              <Send size={19} />
            </button>
          </form>
        </Modal>
      )}
      {modal === "settings" && (
        <Modal title="Settings" onClose={closeModal}>
          <div className="modal-body">
            <div className="setting-row">
              <div>
                <strong>Agent notifications</strong>
                <p>Show the agent’s notification indicator.</p>
              </div>
              <button
                role="switch"
                aria-checked={notifications}
                aria-label="Agent notifications"
                className={`switch ${notifications ? "on" : ""}`}
                onClick={() => {
                  setNotifications(!notifications);
                  document.documentElement.dataset.notifications =
                    String(!notifications);
                }}
              >
                <span />
              </button>
            </div>
            <div className="insight">
              <Leaf size={18} />
              <p>
                This is a local demo. Changes last until you refresh
                the page.
              </p>
            </div>
          </div>
        </Modal>
      )}
      {modal === "profile" && (
        <Modal title="About Hydra" onClose={closeModal}>
          <div className="modal-body">
            <div className="profile-detail">
              <span className="avatar">PG</span>
              <div>
                <h3>Patrick Graham</h3>
                <p>Brand owner · Hydra</p>
              </div>
            </div>
            <p className="muted">
              Electrolyte drink mixes for everyday rituals. This demo
              includes customer segments, trends, and campaigns.
            </p>
            <button
              className="btn primary mt-5"
              onClick={() => {
                closeModal();
                navigate("Integrations");
              }}
            >
              Manage integrations
              <ArrowRight size={15} />
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
