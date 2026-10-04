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

const registerLabels = { decisions: "Décisions importantes", responsables: "Responsables", engagements: "Engagements", echeances: "Échéances", risques: "Risques" };
const registerStatuses = { approved: "Approuvé", conditional: "Conditionnel", not_approved: "Non approuvé", proposed: "Proposé", documented: "Documenté", assigned: "Attribué", historical: "Historique", planned: "Planifié", superseded: "Périmé", open: "Ouvert", in_review: "En validation", completed: "Fermé" };

function shortTitle(item) {
  const plain = item.title.replace(/\*\*/g, "");
  if (/Le 22 devient la date officielle/i.test(plain)) return "Date officielle fixée au 22 octobre 2026";
  if (/On doit mettre les plans et communications à jour/i.test(plain)) return "Mettre à jour les plans et communications du projet";
  const documentTitles = [
    [/Transcript.*Comite.*direction.*10sept/i, "Report de la mise en production au 22 octobre"],
    [/Transcript.*Comite.*26sept/i, "Trois conditions à lever avant la mise en production"],
    [/Decision.*Portee.*Phase2/i, "Optimisations mobiles CR-04 : report en phase 2"],
    [/ADR-007/i, "Localisation des données de production au Canada"],
    [/Transition.*charge.*projet|Note.*transition|Teams.*Transition/i, "Transition de la responsabilité du projet"],
    [/Rappel.*mise.*production/i, "Cible du 22 octobre et validations restantes"],
    [/CR.*Demarrage/i, "Cadrage initial : portée, budget et gouvernance"],
    [/Facture.*003/i, "Facture INV-003 : vérifier les dépenses CR-04"],
    [/Fonction.*mobile|Teams.*Mobile/i, "CR-04 : clarifier la portée et l’autorisation"],
    [/Communication.*statut/i, "Statut du projet et validations à confirmer"],
  ];
  for (const [pattern, summary] of documentTitles) {
    if (pattern.test(item.title)) return summary;
  }
  const title = item.title
    .replace(/\*\*/g, "")
    .replace(/^\d{2}:\d{2}\s*(?:[-–]\s*)?[^:]+:\s*/, "")
    .replace(/^(?:-\s*|Action\s*:\s*)/, "")
    .replace(/^(?:E\d+|M\d+|Teams|Transcript|CR_Comite|CR_Suivi)[_\s-]+/i, "")
    .replace(/_/g, " ")
    .replace(/\s+/g, " ").trim();
  const sentence = title.split(/(?<=[.!?])\s/)[0];
  if (sentence.length <= 105) return sentence;
  return `${sentence.slice(0, 102).replace(/\s+\S*$/, "")}…`;
}

function sourceContext(item) {
  const supports = new Set();
  const people = new Map();
  if (item.owner) people.set(item.owner, item.owner_role || "Responsable désigné");
  for (const proof of item.evidence) {
    if (/Teams_/i.test(proof.path)) supports.add("Microsoft Teams");
    else if (/\.eml$/i.test(proof.path)) supports.add("Courriel (application non précisée)");
    else if (/\.xlsx$/i.test(proof.path)) supports.add("Classeur Excel");
    else if (/\.pdf$/i.test(proof.path)) supports.add("Document PDF");
    else if (/Transcript/i.test(proof.path)) supports.add("Transcription de réunion");
    else supports.add("Document texte");
    const author = proof.excerpt.match(/^From:\s*([^<\n]+)/m);
    const speaker = proof.excerpt.match(/^\d{2}:\d{2}\s*(?:[-–]\s*)?([^:]+):/m);
    const name = (author?.[1] || speaker?.[1])?.trim();
    if (name && !people.has(name)) people.set(name, author ? "Auteur du courriel" : "Intervenant cité");
  }
  return { supports: [...supports], people: [...people] };
}

function professionalHeading(item, group) {
  const text = item.title.replace(/\*\*/g, "");
  if (/Le 22 devient la date officielle|date cible.*déplacée/i.test(text)) return "NOVA — Nouvelle date de lancement";
  if (/plans et communications.*jour/i.test(text)) return "NOVA — Actualisation du calendrier";
  if (/charge du projet|transition|reprend officiellement/i.test(text)) return "NOVA — Transition du pilotage";
  if (/CR-04|mobile/i.test(text)) return "NOVA — Portée des optimisations mobiles";
  if (/Canada Central|ADR-007/i.test(text)) return "NOVA — Hébergement de production";
  const ticket = text.match(/\b(?:SEC|ACC|OPS|INT|DATA|PERF)-\d+\b/)?.[0];
  const topics = { governance: "Pilotage du projet", schedule: "Calendrier de lancement", security: "Validation de sécurité", accessibility: "Accessibilité", operations: "Préparation à l’exploitation", architecture: "Architecture de production", data: "Migration des données", integration: "Connecteur interne", performance: "Performance", scope: "Portée du projet", finance: "Suivi financier", delivery: "Suivi des livrables" };
  const types = { decisions: "Décision", responsables: "Responsabilité", engagements: "Action", echeances: "Échéance", risques: "Risque" };
  return `${ticket || "NOVA"} — ${types[group]} : ${topics[item.topic] || "Suivi du projet"}`;
}

function professionalSubject(item, group) {
  const plain = item.title.replace(/\*\*/g, "");
  if (/Le 22 devient la date officielle/i.test(plain)) {
    return "Confirmer le 22 octobre 2026 comme date officielle de mise en production de NOVA et actualiser les plans et les communications.";
  }
  let subject = plain
    .replace(/^\d{2}:\d{2}\s*(?:[-–]\s*)?[^:]+:\s*/, "")
    .replace(/^(?:-\s*|Action\s*:\s*)/, "")
    .replace(/^Donc\s+approuvé[.!]?\s*/i, "")
    .replace(/^Subject:\s*/i, "")
    .replace(/\s+/g, " ").trim();
  if (/^(?:E\d+|M\d+|Teams_|ADR-007|Decision_Portee|Note_transition)/i.test(subject)) subject = shortTitle(item);
  if (group === "responsables") return `${item.owner || "Responsable non précisé"} — responsabilité documentée : ${subject}.`;
  if (group === "echeances") return `${subject.replace(/\.$/, "")} : ${item.due ? `échéance au ${item.due}` : "échéance non précisée"}${item.status === "superseded" ? ", date du plan remplacée par une décision ultérieure" : item.status === "conditional" ? ", sous réserve des validations restantes" : ", selon le calendrier documenté"}.`;
  const prefixes = { decisions: "Objet de la décision", engagements: "Action attendue", risques: "Point de vigilance" };
  return `${prefixes[group]} : ${subject}`;
}

export default function Dossier() {
  const [dossier, setDossier] = useState(null);
  const [activeSection, setActiveSection] = useState("all");
  const [error, setError] = useState("");
  const [sourceDocument, setSourceDocument] = useState(null);
  const [sourceError, setSourceError] = useState("");
  const [busy, setBusy] = useState(false);

  async function openSource(id) {
    setSourceError(""); setSourceDocument(null);
    try {
      const response = await fetch(`/api/documents/${encodeURIComponent(id)}`);
      if (!response.ok) throw new Error("Document introuvable.");
      setSourceDocument(await response.json());
    } catch (err) { setSourceError(err.message); }
  }

  async function reanalyze() {
    setBusy(true); setError("");
    try {
      const ingestion = await fetch("/api/ingest", { method: "POST" });
      const result = await ingestion.json();
      if (!ingestion.ok || !result.ok) throw new Error(result.message || "Analyse impossible.");
      const response = await fetch("/api/dossier");
      if (!response.ok) throw new Error("Impossible de charger le dossier.");
      setDossier(await response.json());
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  function exportDossier() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(dossier, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url; link.download = "nova-dossier.json"; link.click(); URL.revokeObjectURL(url);
  }

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

  if (error && !dossier) {
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
          <p>Décisions, responsables, engagements, échéances et risques sont regroupés par catégorie du projet. État des preuves au {dossier.evidence_as_of || "non précisé"}.</p>
        </div>
        <div className="brief-grid">
          <BriefItem label="Responsable" value={dossier.summary.owner} />
          <BriefItem label="Budget" value={dossier.summary.budget} />
          <BriefItem label="Regle de lecture" value={dossier.summary.principle} />
          <BriefItem label="Etat au" value={dossier.as_of} />
        </div>
      </div>

      <div className="section-tabs">
        <button onClick={reanalyze} disabled={busy}>{busy ? "Analyse en cours…" : "Ré-analyser le corpus"}</button>
        <button onClick={exportDossier} disabled={busy}>Exporter le dossier JSON</button>
      </div>
      {error && <p className="error-text" role="alert">{error}</p>}

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
          <DossierSection key={section.id} section={section} onOpenSource={openSource} />
        ))}
      </div>
      {sourceError && <p role="alert">{sourceError}</p>}
      {sourceDocument && <section className="panel" aria-label="Document source"><button onClick={() => setSourceDocument(null)}>Fermer le document</button><h3>{sourceDocument.path}</h3><pre className="dossier-document">{sourceDocument.text}</pre></section>}
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

function DossierSection({ section, onOpenSource }) {
  const StatusIcon = statusIcons[section.status] ?? FileText;
  const [activeType, setActiveType] = useState("decisions");
  const items = section.registers?.[activeType] || [];

  return (
    <details className="panel dossier-section dossier-category">
      <summary className="dossier-section-header">
        <div>
          <h3>{section.title}</h3>
          <p>{section.purpose}</p>
          <span className="dossier-expand-hint">Ouvrir les informations et le suivi par type</span>
        </div>
        <span className="section-status">
          <StatusIcon size={15} />
          {section.status}
        </span>
      </summary>

      <div className="dossier-category-content">

      <div className="dossier-column">
        <p className="section-label">Informations pertinentes</p>
        <ul className="clean-list">
          {section.facts.map((fact) => (
            <li key={fact}>{fact}</li>
          ))}
        </ul>
      </div>

      <div className="dossier-column">
        <p className="section-label">Actions / points ouverts du dossier</p>
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

      <div className="dossier-type-filters" role="group" aria-label={`Types d’information — ${section.title}`}>
        {Object.entries(registerLabels).map(([key, label]) => <button key={key} type="button" aria-pressed={activeType === key} className={activeType === key ? "active" : ""} onClick={() => setActiveType(key)}>{label}<span>{section.registers?.[key]?.length || 0}</span></button>)}
      </div>
      <div className="dossier-column dossier-register">
        <h4 className="section-label">{registerLabels[activeType]}</h4>
        {!items.length && <p>Aucun élément explicitement identifié dans les sources de cette catégorie.</p>}
        {items.map(item => <RegisterItem key={`${activeType}-${item.id}`} item={item} category={section.title} group={activeType} onOpenSource={onOpenSource} />)}
      </div>

      {section.alerts?.length > 0 && <div className="dossier-column dossier-register"><h4 className="section-label">Divergences à vérifier</h4>{section.alerts.map(alert => <details key={alert.id}><summary>{alert.title}</summary><p>{alert.description}</p><Evidence proofs={alert.evidence} onOpenSource={onOpenSource} /></details>)}</div>}

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
      </div>
    </details>
  );
}

function Evidence({ proofs, onOpenSource }) {
  return proofs.map((proof, index) => <div className="dossier-proof" key={`${proof.document_id}-${index}`}>
    <p className="dossier-proof-heading"><FileText size={15} /><strong>{proof.path.split('/').at(-1)}</strong></p>
    <p className="dossier-proof-meta">{proof.locator} · Publication : {proof.published_on || "non précisée"}</p>
    <details className="dossier-excerpt"><summary>Voir l’extrait justificatif</summary><blockquote>{proof.excerpt}</blockquote></details>
    <button onClick={() => onOpenSource(proof.document_id)}>Lire le document complet</button>
  </div>);
}

function RegisterItem({ item, category, group, onOpenSource }) {
  const { supports, people } = sourceContext(item);
  const status = registerStatuses[item.status] || item.status;
  const title = professionalHeading(item, group);
  const subject = professionalSubject(item, group);
  const normalize = value => value.replace(/\*\*/g, "").replace(/\s+/g, " ").trim();
  const noteRepeatsSource = item.note && item.evidence.some(proof => normalize(proof.excerpt) === normalize(item.note));
  const contentLabel = { decisions: "Décision / position documentée", responsables: "Responsabilité", engagements: "Engagement / action", echeances: "Jalon prévu", risques: "Risque identifié" }[group];
  return <details className="dossier-item">
    <summary className="dossier-item-summary">
      <span className="dossier-item-heading"><strong>{title}</strong><span className="dossier-item-preview">{item.owner || "Responsable non précisé"}{item.due ? ` · Échéance : ${item.due}` : item.date ? ` · ${item.date}` : ""}</span></span>
      <span className={`dossier-item-status status-${item.status}`}>{status}</span>
    </summary>
    <div className="dossier-item-content">
      <dl className="dossier-item-fields">
        <div><dt>Catégorie du projet</dt><dd>{category}</dd></div>
        <div><dt>Type d’information</dt><dd>{registerLabels[group]}</dd></div>
        <div><dt>Statut</dt><dd>{status}</dd></div>
        <div><dt>Plateforme / support de communication</dt><dd>{supports.join(" · ") || "Non précisé"}</dd></div>
        <div className="dossier-field-wide"><dt>{contentLabel}</dt><dd>{subject}</dd></div>
        <div className="dossier-field-wide"><dt>Personnes / équipes concernées</dt><dd>{people.length ? people.map(([name, role]) => <span className="dossier-person" key={name}><strong>{name}</strong><span>{role}</span></span>) : "Non précisées dans cet élément"}</dd></div>
        <div><dt>Date documentée / début prévu</dt><dd>{item.date || "Non précisée"}</dd></div>
        <div><dt>Échéance</dt><dd>{item.due || "Non précisée — consulter l’extrait pour les délais relatifs"}</dd></div>
      </dl>
      {item.note && !noteRepeatsSource && <div className="dossier-item-context"><h5>Contexte et points de vigilance</h5><p>{item.note.replace(/\*\*/g, "")}</p></div>}
      <div className="dossier-item-evidence"><h5>Sources et preuves</h5><Evidence proofs={item.evidence} onOpenSource={onOpenSource} /></div>
    </div>
  </details>;
}
