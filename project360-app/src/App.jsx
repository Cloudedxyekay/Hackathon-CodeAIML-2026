import { useEffect, useState } from "react";
import { Activity, Bot, FileSearch, FolderKanban, GitCompare, History, LayoutDashboard, RefreshCw, Search } from "lucide-react";
import Dashboard from "./components/Dashboard.jsx";
import AskAgent from "./components/AskAgent.jsx";
import Dossier from "./components/Dossier.jsx";
import EvidenceSearch from "./components/EvidenceSearch.jsx";
import Timeline from "./components/Timeline.jsx";
import UpdateSimulator from "./components/UpdateSimulator.jsx";
import BonusComparison from "./components/BonusComparison.jsx";

const tabs = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "dossier", label: "Dossier", icon: FolderKanban },
  { id: "ask", label: "Ask NOVA", icon: Bot },
  { id: "search", label: "Evidence", icon: Search },
  { id: "timeline", label: "Timeline", icon: History },
  { id: "updates", label: "Updates", icon: RefreshCw },
  { id: "bonus", label: "Bonus", icon: GitCompare }
];

export default function App() {
  const [active, setActive] = useState("dashboard");
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/dashboard")
      .then((response) => response.json())
      .then(setDashboard)
      .finally(() => setLoading(false));
  }, []);

  const ActiveComponent = {
    dashboard: Dashboard,
    dossier: Dossier,
    ask: AskAgent,
    search: EvidenceSearch,
    timeline: Timeline,
    updates: UpdateSimulator,
    bonus: BonusComparison
  }[active];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Activity size={22} /></div>
          <div>
            <strong>NOVA</strong>
            <span>Project Memory</span>
          </div>
        </div>
        <nav>
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                className={active === tab.id ? "active" : ""}
                onClick={() => setActive(tab.id)}
                title={tab.label}
              >
                <Icon size={18} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>
      <main>
        <header className="topbar">
          <div>
            <p className="eyebrow">Evidence-grounded AI workspace</p>
            <h1>{tabs.find((tab) => tab.id === active)?.label}</h1>
          </div>
          {active === "dossier" && (
            <div className="status-pill">
              <FileSearch size={16} />
              {loading ? "Loading corpus" : `${dashboard?.documents?.length ?? 0} evidence files`}
            </div>
          )}
        </header>
        <ActiveComponent dashboard={dashboard} />
      </main>
    </div>
  );
}
