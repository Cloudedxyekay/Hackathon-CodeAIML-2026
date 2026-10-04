import {
  ArrowRight,
  History,
  CheckCircle2,
  Flag,
  TriangleAlert,
  UserRound,
} from "lucide-react";
import { formatDate } from "./Timeline.jsx";

export default function Dashboard({ dashboard, onNavigate }) {
  const memory = dashboard?.memory;
  const baseline = dashboard?.baseline ?? {};
  const actions = dashboard?.actions ?? [];
  const timeline = dashboard?.timeline ?? [];

  if (memory)
    return (
      <section className="page-grid project-overview">
        <div className="panel wide overview-header">
          <div>
            <p className="eyebrow">ÉTAT DOCUMENTÉ DU PROJET</p>
            <h2>
              {memory.schedule.conditional
                ? "Une cible claire. Des validations à terminer."
                : "La mémoire opérationnelle de NOVA"}
            </h2>
            <p>
              Dernier fait documenté le{" "}
              {formatDate(memory.as_of, {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
              . Retrouvez les décisions, les responsables cités et les preuves
              de l’évolution du projet.
            </p>
          </div>
          <button className="primary" onClick={() => onNavigate?.("timeline")}>
            Ouvrir la mémoire <ArrowRight size={16} />
          </button>
        </div>
        <div className="metric">
          <span>
            <Flag size={16} /> Cible approuvée
          </span>
          <strong>
            {formatDate(memory.schedule.current_target, {
              day: "numeric",
              month: "long",
            })}
          </strong>
          <small>
            {memory.schedule.conditional
              ? "Conditionnelle aux validations restantes"
              : "Date établie par les sources"}
          </small>
        </div>
        <div className="metric">
          <span>
            <CheckCircle2 size={16} /> Tickets fermés
          </span>
          <strong>
            {memory.stats.completed_tickets} / {memory.stats.tickets}
          </strong>
          <small>Fermetures documentées, sans avancement global estimé</small>
        </div>
        <div className="metric">
          <span>
            <UserRound size={16} /> Charge de projet
          </span>
          <strong>{memory.assignments?.at(-1)?.owner || "Non précisée"}</strong>
          <small>Attribution explicite dans les sources</small>
        </div>
        <div className="panel wide">
          <div className="section-heading">
            <div>
              <p className="eyebrow">CONDITIONS AVANT PRODUCTION</p>
              <h3>Les validations qui restent ouvertes</h3>
            </div>
            <button
              className="quiet-button"
              onClick={() => onNavigate?.("timeline")}
            >
              <History size={15} /> Voir la chronologie
            </button>
          </div>
          <div className="overview-gates">
            {memory.gates.map((gate) => (
              <div key={gate.id}>
                <TriangleAlert size={18} />
                <strong>
                  {gate.id} · {memory.topics[gate.topic]}
                </strong>
                <p>{gate.title}</p>
                <span>
                  {gate.owner} ·{" "}
                  {gate.status === "in_review" ? "En validation" : "Ouvert"}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div className="panel wide">
          <p className="eyebrow">ÉCARTS DOCUMENTAIRES</p>
          <div className="overview-alerts">
            {memory.alerts.map((alert) => (
              <article key={alert.id}>
                <h3>{alert.title}</h3>
                <p>{alert.description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>
    );

  return (
    <section className="page-grid">
      <div className="panel wide">
        <p className="eyebrow">Baseline</p>
        <h2>{baseline.status || "Waiting for ingestion"}</h2>
        <p>{baseline.scope}</p>
      </div>
      <div className="metric">
        <span>As of</span>
        <strong>{baseline.as_of || "Unknown"}</strong>
      </div>
      <div className="metric">
        <span>Timeline Events</span>
        <strong>{timeline.length}</strong>
      </div>
      <div className="metric">
        <span>Open Actions</span>
        <strong>
          {actions.filter((item) => item.status !== "done").length}
        </strong>
      </div>
      <div className="panel">
        <h3>Go-live</h3>
        <p>{baseline.go_live}</p>
      </div>
      <div className="panel">
        <h3>Budget</h3>
        <p>{baseline.budget}</p>
      </div>
      <div className="panel wide">
        <h3>Known Risks</h3>
        <ul className="clean-list">
          {(baseline.risks || []).map((risk) => (
            <li key={risk}>{risk}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}
