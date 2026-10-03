import { useEffect, useState } from "react";
import {
  Activity,
  Bot,
  CalendarDays,
  FileSearch,
  GitCompare,
  History,
  LayoutDashboard,
  ListChecks,
  RefreshCw,
  Search,
} from "lucide-react";
import Dashboard from "./components/Dashboard.jsx";
import AskAgent from "./components/AskAgent.jsx";
import EvidenceSearch from "./components/EvidenceSearch.jsx";
import QuestionAnswers from "./components/QuestionAnswers.jsx";
import Timeline from "./components/Timeline.jsx";
import UpdateSimulator from "./components/UpdateSimulator.jsx";
import BonusComparison from "./components/BonusComparison.jsx";

const tabs = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "ask", label: "Ask Agent", icon: Bot },
  { id: "search", label: "Evidence", icon: Search },
  { id: "questions", label: "Questions", icon: ListChecks },
  { id: "timeline", label: "Mémoire du projet", icon: History },
  { id: "calendar", label: "Calendrier", icon: CalendarDays },
  { id: "updates", label: "Updates", icon: RefreshCw },
  { id: "bonus", label: "Bonus", icon: GitCompare },
];

export default function App() {
  const [active, setActive] = useState("timeline");
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function loadDashboard() {
    setError("");
    return fetch("/api/dashboard")
      .then((response) => {
        if (!response.ok)
          throw new Error(
            "Le serveur Python est indisponible. Démarrez-le sur le port 8000.",
          );
        return response.json();
      })
      .then(setDashboard)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }
  useEffect(() => {
    loadDashboard();
  }, []);

  const ActiveComponent = {
    dashboard: Dashboard,
    ask: AskAgent,
    search: EvidenceSearch,
    questions: QuestionAnswers,
    timeline: Timeline,
    calendar: Timeline,
    updates: UpdateSimulator,
    bonus: BonusComparison,
  }[active];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Activity size={22} />
          </div>
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
        <div className="sidebar-project">
          <span className="sidebar-project-dot" />
          <div>
            <strong>Projet NOVA</strong>
            <span>Phase 1 · espace documentaire</span>
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div>
            <p className="eyebrow">NOVA / ESPACE PROJET</p>
            <h1>{tabs.find((tab) => tab.id === active)?.label}</h1>
          </div>
          <div className="status-pill">
            <FileSearch size={16} />
            {loading
              ? "Lecture du corpus…"
              : dashboard?.memory
                ? `${dashboard.memory.stats.documents} documents · sources reliées`
                : "API à connecter"}
          </div>
        </header>
        {error && active !== "timeline" && active !== "calendar" && (
          <p className="memory-error" role="alert">
            {error}
          </p>
        )}
        <ActiveComponent
          dashboard={dashboard}
          initialView={active === "calendar" ? "calendar" : "timeline"}
          onRefresh={loadDashboard}
          onNavigate={setActive}
        />
      </main>
    </div>
  );
}
