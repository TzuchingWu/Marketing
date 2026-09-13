import { useEffect, useState } from "react";
import {
  Activity,
  Bell,
  CheckCircle2,
  Compass,
  Link2,
  Menu,
  Settings,
  X,
} from "lucide-react";
import type { AgentActivityItem, BusinessInput, IntegrationStatus, Page, RecommendResult } from "./types";
import { Home } from "./pages/Home";
import { Results } from "./pages/Results";
import { AgentActivityPage, Integrations } from "./pages/WorkspacePages";
import { Modal } from "./components/ui";
import * as api from "./api";

const navigation = [
  { name: "Home" as Page, icon: Compass },
  { name: "Agent Activity" as Page, icon: Activity },
  { name: "Integrations" as Page, icon: Link2 },
];

const TOOL_CATEGORY: Record<string, AgentActivityItem["category"]> = {
  analyze_business: "Research",
  search_creators: "Research",
  analyze_creator: "Analysis",
  rank_creators: "Analysis",
  generate_campaign: "Decision",
  generate_video_script: "Decision",
  generate_video_ad: "Decision",
  generate_outreach: "Action",
  log_creator_outreach: "Action",
  analyze_online_presence: "Research",
};

function toActivityItems(result: RecommendResult): AgentActivityItem[] {
  return result.activity_log.map((entry, i) => ({
    id: `${entry.tool}-${i}`,
    time: "Just now",
    category: TOOL_CATEGORY[entry.tool] || "Action",
    title: entry.tool,
    description: entry.summary,
  }));
}

export default function App() {
  const [page, setPage] = useState<Page>("Home");
  const [mobile, setMobile] = useState(false);
  const [toast, setToast] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RecommendResult | null>(null);
  const [activities, setActivities] = useState<AgentActivityItem[]>([]);
  const [integrationStatus, setIntegrationStatus] = useState<IntegrationStatus | null>(null);
  const [modal, setModal] = useState<"settings" | null>(null);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 4500);
    return () => clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    api.integrationsStatus().then(setIntegrationStatus).catch(() => setIntegrationStatus(null));
  }, []);

  function navigate(p: Page) {
    setPage(p);
    setMobile(false);
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  async function handleFindCreators(business: BusinessInput) {
    setLoading(true);
    setError(null);
    try {
      const res = await api.recommend(business);
      setResult(res);
      setActivities(toActivityItems(res));
      setPage("Results");
    } catch (err) {
      setError((err as Error).message || "Something went wrong reaching the backend.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="global-bar">
          <div className="global-inner">
            <button className="pulse-wordmark" onClick={() => navigate("Home")} aria-label="OUTTHERE home">
              OUTTHERE
            </button>
            <button
              className="icon-button nav-toggle"
              aria-label={mobile ? "Close navigation" : "Open navigation"}
              aria-expanded={mobile}
              aria-controls="primary-navigation"
              onClick={() => setMobile(!mobile)}
            >
              {mobile ? <X size={20} /> : <Menu size={20} />}
            </button>
            <nav id="primary-navigation" aria-label="Primary navigation" className={mobile ? "top-navigation expanded" : "top-navigation"}>
              {navigation.map((n) => {
                const active = page === n.name;
                return (
                  <button key={n.name} onClick={() => navigate(n.name)} className={active ? "active" : ""} aria-current={active ? "page" : undefined}>
                    {n.name}
                  </button>
                );
              })}
            </nav>
            <div className="global-actions">
              <button className="icon-button" aria-label="View agent activity" onClick={() => navigate("Agent Activity")}>
                <Bell size={17} />
                {activities.length > 0 && <span className="notification-dot" />}
              </button>
              <button className="icon-button" aria-label="Settings" onClick={() => setModal("settings")}>
                <Settings size={17} />
              </button>
            </div>
          </div>
        </div>
      </header>
      <div className="main-shell">
        <main>
          {page !== "Home" && page !== "Results" && (
            <div className="page-heading">
              <div>
                <h1>{page}</h1>
                <p>
                  {page === "Agent Activity"
                    ? "A transparent look at your marketing agent at work."
                    : "Bring your marketing world together."}
                </p>
              </div>
            </div>
          )}
          {page === "Home" && <Home loading={loading} error={error} onSubmit={handleFindCreators} />}
          {page === "Results" && result && (
            <Results
              result={result}
              onNewSearch={() => navigate("Home")}
              onToast={setToast}
            />
          )}
          {page === "Agent Activity" && <AgentActivityPage items={activities} />}
          {page === "Integrations" && <Integrations status={integrationStatus} />}
        </main>
      </div>
      {toast && (
        <div className="toast" role="status">
          <CheckCircle2 size={19} />
          {toast}
          <button aria-label="Dismiss notification" onClick={() => setToast("")}>
            <X size={16} />
          </button>
        </div>
      )}
      {modal === "settings" && (
        <Modal title="About OUTTHERE" onClose={() => setModal(null)}>
          <div className="modal-body">
            <p className="muted">
              An AI-powered marketing agent that finds the right local content creator for your
              business -- ranked by fit, not follower count -- through a live MCP server backend.
            </p>
          </div>
        </Modal>
      )}
    </div>
  );
}
