import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, FileText, FolderKanban, ListChecks } from "lucide-react";

const statusIcons = {
  "A jour": CheckCircle2,
  "Sous controle": CheckCircle2,
  "Decision implementee": CheckCircle2,
  "Conditionnelle": AlertTriangle,
  "Attention requise": AlertTriangle,
  "En validation": AlertTriangle,
  "Bloquant ouvert": AlertTriangle,
  "A surveiller": AlertTriangle
};

export default function Dossier() {
  const [dossier, setDossier] = useState(null);
  const [activeSection, setActiveSection] = useState("all");
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/dossier")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Impossible de charger le dossier.");
        }
        return response.json();
      })
      .then(setDossier)
      .catch((event) => setError(event.message));
  }, []);

  const sections = dossier?.sections ?? [];
  const visibleSections = useMemo(() => {
    if (activeSection === "all") {
      return sections;
    }
    return sections.filter((section) => section.id === activeSection);
  }, [activeSection, sections]);

  if (error) {
    return <p className="error-text">{error}</p>;
  }

  if (!dossier) {
    return <section className="panel">Chargement du dossier...</section>;
  }

  return (
    <section className="stack">
      <div className="panel dossier-brief">
        <div>
          <p className="eyebrow">Dossier organise</p>
          <h2>{dossier.summary.title}</h2>
          <p>{dossier.summary.status}</p>
        </div>
        <div className="brief-grid">
          <BriefItem label="Responsable" value={dossier.summary.owner} />
          <BriefItem label="Budget" value={dossier.summary.budget} />
          <BriefItem label="Regle de lecture" value={dossier.summary.principle} />
          <BriefItem label="Etat au" value={dossier.as_of} />
        </div>
      </div>

      <div className="section-tabs" aria-label="Sections du dossier">
        <button className={activeSection === "all" ? "active" : ""} onClick={() => setActiveSection("all")}>
          <FolderKanban size={16} />
          Toutes
        </button>
        {sections.map((section) => (
          <button
            key={section.id}
            className={activeSection === section.id ? "active" : ""}
            onClick={() => setActiveSection(section.id)}
          >
            {section.title}
          </button>
        ))}
      </div>

      <div className="dossier-grid">
        {visibleSections.map((section) => (
          <DossierSection key={section.id} section={section} />
        ))}
      </div>
    </section>
  );
}

function BriefItem({ label, value }) {
  return (
    <div className="brief-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function DossierSection({ section }) {
  const StatusIcon = statusIcons[section.status] ?? FileText;

  return (
    <article className="panel dossier-section">
      <div className="dossier-section-header">
        <div>
          <h3>{section.title}</h3>
          <p>{section.purpose}</p>
        </div>
        <span className="section-status">
          <StatusIcon size={15} />
          {section.status}
        </span>
      </div>

      <div className="dossier-column">
        <p className="section-label">Informations pertinentes</p>
        <ul className="clean-list">
          {section.facts.map((fact) => (
            <li key={fact}>{fact}</li>
          ))}
        </ul>
      </div>

      <div className="dossier-column">
        <p className="section-label">Actions / points ouverts</p>
        <div className="action-list">
          {section.open_items.map((item) => (
            <div key={item.label} className="action-row">
              <ListChecks size={16} />
              <div>
                <strong>{item.label}</strong>
                <span>{item.owner} | {item.due}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="dossier-column">
        <p className="section-label">Preuves</p>
        <div className="source-grid">
          {section.sources.map((source) => (
            <div key={`${source.file}-${source.locator}`} className="source-chip">
              <FileText size={15} />
              <div>
                <strong>{source.file}</strong>
                <span>{source.locator} | {source.note}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </article>
  );
}
