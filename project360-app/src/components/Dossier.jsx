import { useEffect, useMemo, useRef, useState } from "react";
import { FileText, RotateCcw, ArrowUpRight, X, Folder, ArrowLeft } from "lucide-react";
import { groupDossierDocuments } from './dossierDocuments.js';

const registerLabels = { decisions: "Décisions importantes", responsables: "Responsables", engagements: "Engagements", echeances: "Échéances", risques: "Risques", documents: "Documents et informations" };
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
    else if (/\.(png|jpe?g|webp)$/i.test(proof.path)) supports.add("Image / capture");
    else if (/Transcript/i.test(proof.path)) supports.add("Transcription de réunion");
    else supports.add("Document texte");
    const author = proof.excerpt.match(/^From:\s*([^<\n]+)/m);
    const speaker = proof.excerpt.match(/^\d{2}:\d{2}\s*(?:[-–]\s*)?([^:]+):/m);
    const name = (author?.[1] || speaker?.[1])?.trim();
    if (name && !people.has(name)) people.set(name, author ? "Auteur du courriel" : "Intervenant cité");
  }
  return { supports: [...supports], people: [...people] };
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
  const [filters, setFilters] = useState({ category: "", group: "", person: "", support: "", status: "", from: "", to: "" });
  const [error, setError] = useState("");
  const [sourceDocument, setSourceDocument] = useState(null);
  const [sourceError, setSourceError] = useState("");
  const [sourceOpen, setSourceOpen] = useState(false);
  const [sourceLoading, setSourceLoading] = useState(false);
  const sourceRequest = useRef(null);
  const [busy, setBusy] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [archiveView, setArchiveView] = useState(false);
  const [categoryTabs, setCategoryTabs] = useState([]);
  const [activeCategoryTab, setActiveCategoryTab] = useState(null);
  function openCategory(id) {
    setCategoryTabs(previous => previous.includes(id) ? previous : [...previous, id]);
    setActiveCategoryTab(id);
    setFilters(previous => ({ ...previous, category: '' }));
  }
  function closeCategory(id) {
    const remaining = categoryTabs.filter(tab => tab !== id);
    setCategoryTabs(remaining);
    if (activeCategoryTab === id) setActiveCategoryTab(remaining.at(-1) || null);
  }

  async function openSource(id) {
    sourceRequest.current?.abort();
    const controller = new AbortController();
    sourceRequest.current = controller;
    setSourceError(""); setSourceDocument(null); setSourceOpen(true); setSourceLoading(true);
    try {
      const response = await fetch(`/api/documents/${encodeURIComponent(id)}`, { signal: controller.signal });
      if (!response.ok) throw new Error("Document introuvable.");
      setSourceDocument(await response.json());
    } catch (err) { if (err.name !== 'AbortError') setSourceError(err.message); }
    finally { if (sourceRequest.current === controller) setSourceLoading(false); }
  }

  function closeSource() { sourceRequest.current?.abort(); setSourceOpen(false); }
  useEffect(() => () => sourceRequest.current?.abort(), []);

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
  const entries = useMemo(() => {
    return groupDossierDocuments(dossier?.sections || [], dossier?.completed_documents || []).map(entry => {
      const people = new Map();
      for (const point of entry.points) for (const [name, role] of sourceContext(point.item).people) {
        if (!people.has(name)) people.set(name, new Set());
        people.get(name).add(role);
      }
      return { ...entry, context: { people: [...people].map(([name, roles]) => [name, [...roles].join(' · ')]), supports: [entry.support] } };
    });
  }, [dossier]);
  const people = [...new Set(entries.flatMap(entry => entry.context.people.map(([name]) => name)))].sort((a, b) => a.localeCompare(b, 'fr'));
  const supports = [...new Set(entries.flatMap(entry => entry.context.supports))].sort();
  const statuses = [...new Set(entries.flatMap(entry => entry.statuses))].sort();
  const activeEntries = entries.filter(entry => Boolean(entry.completion) === archiveView);
  const visibleEntries = activeEntries.filter(entry => {
    const dates = [entry.date, ...entry.points.flatMap(point => [point.item.date, point.item.due])].filter(Boolean);
    return (!filters.category || entry.categories.some(c => c.id === filters.category))
      && (!filters.group || entry.groups.includes(filters.group))
      && (!filters.person || entry.context.people.some(([name]) => name === filters.person))
      && (!filters.support || entry.context.supports.includes(filters.support))
      && (!filters.status || entry.statuses.includes(filters.status))
      && ((!filters.from && !filters.to) || dates.some(date => (!filters.from || date >= filters.from) && (!filters.to || date <= filters.to)));
  });
  const changeFilter = (name, value) => setFilters(previous => ({ ...previous, [name]: value }));
  const availableCategoryIds = new Set(visibleEntries.flatMap(entry => entry.categories.map(category => category.id)));
  const activeCategoryHasFiles = !activeCategoryTab || availableCategoryIds.has(activeCategoryTab);
  useEffect(() => {
    if (!activeCategoryHasFiles) setActiveCategoryTab(null);
  }, [activeCategoryHasFiles]);

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
          <p>Tous les éléments du projet sont réunis ici. Filtrez les décisions, responsables, engagements, échéances et risques. État des preuves au {dossier.evidence_as_of || "non précisé"}.</p>
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
        {dossier.verification_tasks?.length > 0 && <div className="dossier-task-bubbles" aria-label="Tâches à vérifier"><span className="dossier-task-label">Tâches à vérifier</span>{dossier.verification_tasks.map(task => <button key={task.id} className={`dossier-task-chip priority-${task.priority}`} aria-pressed={selectedTask === task.id} title={`${task.priority === 'urgent' ? 'Urgent' : 'Important'} : ${task.title}`} onClick={() => setSelectedTask(selectedTask === task.id ? null : task.id)}><span className="dossier-task-dot" aria-hidden="true" /><span>{task.priority === 'urgent' ? 'Urgent' : 'Important'} · {task.label}</span></button>)}</div>}
      </div>
      {dossier.verification_tasks?.filter(task => task.id === selectedTask).map(task => <section className={`panel dossier-task-detail priority-${task.priority}`} key={task.id}><div className="dossier-task-detail-header"><h3>{task.title}</h3><button className="dossier-button dossier-button-secondary" onClick={() => setSelectedTask(null)}><X size={16} aria-hidden="true" />Fermer</button></div><p>{task.description}</p><p className="dossier-proof-meta">{task.priority === 'urgent' ? 'Urgent : condition bloquante de mise en production.' : 'Important : divergence documentaire à vérifier.'}</p><Evidence proofs={task.evidence} /></section>)}
      {error && <p className="error-text" role="alert">{error}</p>}

      <div className="section-tabs" aria-label="Classement des dossiers">
        <button className={!archiveView ? 'active' : ''} aria-pressed={!archiveView} onClick={() => setArchiveView(false)}>Dossiers à suivre ({entries.filter(entry => !entry.completion).length})</button>
        <button className={archiveView ? 'active' : ''} aria-pressed={archiveView} onClick={() => setArchiveView(true)}>Dossiers terminés ({entries.filter(entry => entry.completion).length})</button>
      </div>
      {archiveView && <p className="dossier-proof-meta">Documents dont la clôture est explicitement confirmée dans les sources. Les décisions approuvées et les dates planifiées restent dans les dossiers à suivre.</p>}

      <div className="panel dossier-filters" aria-label="Filtres du dossier">
        <DossierFilter label="Type d’information" value={filters.group} onChange={value => changeFilter('group', value)} options={Object.entries(registerLabels)} />
        <DossierFilter label="Personne / équipe" value={filters.person} onChange={value => changeFilter('person', value)} options={people.map(name => [name, name])} />
        <DossierFilter label="Plateforme / support" value={filters.support} onChange={value => changeFilter('support', value)} options={supports.map(support => [support, support])} />
        <DossierFilter label="Catégorie du projet" value={filters.category} onChange={value => changeFilter('category', value)} options={sections.map(section => [section.id, section.title])} />
        <DossierFilter label="Statut" value={filters.status} onChange={value => changeFilter('status', value)} options={statuses.map(status => [status, registerStatuses[status] || status])} />
        <label>Date de début<input type="date" value={filters.from} onChange={event => changeFilter('from', event.target.value)} /></label>
        <label>Date de fin<input type="date" value={filters.to} onChange={event => changeFilter('to', event.target.value)} /></label>
        <button className="dossier-button dossier-button-secondary" onClick={() => setFilters({ category: '', group: '', person: '', support: '', status: '', from: '', to: '' })}><RotateCcw size={16} aria-hidden="true" />Réinitialiser les filtres</button>
        <p className="dossier-filter-help">La période couvre les dates documentées et les échéances. Les éléments sans date sont exclus lorsqu’une période est sélectionnée.</p>
      </div>

      <div className="dossier-explorer-tabs" aria-label="Onglets des catégories">
        <button className={!activeCategoryTab ? 'active' : ''} aria-pressed={!activeCategoryTab} onClick={() => setActiveCategoryTab(null)}><Folder size={16} />Tous les dossiers</button>
        {categoryTabs.filter(id => availableCategoryIds.has(id)).map(id => <div className={`dossier-explorer-tab ${activeCategoryTab === id ? 'active' : ''}`} key={id}><button aria-pressed={activeCategoryTab === id} onClick={() => { setActiveCategoryTab(id); setFilters(previous => ({ ...previous, category: '' })); }}><Folder size={15} />{sections.find(section => section.id === id)?.title}</button><button className="dossier-tab-close" aria-label={`Fermer ${sections.find(section => section.id === id)?.title}`} onClick={() => closeCategory(id)}><X size={14} /></button></div>)}
      </div>
      <div className={`panel dossier-register dossier-main-list ${activeCategoryTab ? '' : 'dossier-category-grid'}`}>
        <p role="status">{visibleEntries.length} documents affichés sur {activeEntries.length} · {archiveView ? 'Dossiers terminés' : 'Dossiers à suivre'}</p>
        {!activeCategoryTab && sections.filter(section => !filters.category || section.id === filters.category).map(section => {
          const linkedDocuments = visibleEntries.filter(entry => entry.categories.some(category => category.id === section.id));
{!activeCategoryTab && sections.filter(section => !filters.category || section.id === filters.category).map(section => {
  const linkedDocuments = visibleEntries.filter(entry => entry.categories.some(category => category.id === section.id));
  if (!linkedDocuments.length) return null;
  return <button className="dossier-folder-card" key={section.id} onClick={() => openCategory(section.id)}><Folder size={24} aria-hidden="true" /><span className="dossier-item-heading"><strong>{section.title}</strong><span className="dossier-item-preview">{section.purpose}</span></span><span className="dossier-item-status">{linkedDocuments.length} document{linkedDocuments.length > 1 ? 's' : ''}</span></button>;
})}
{activeCategoryTab && sections.filter(section => section.id === activeCategoryTab).map(section => {
  const documents = visibleEntries.filter(entry => entry.categories.some(category => category.id === section.id));
  return <section key={`${archiveView}-${section.id}`} className="dossier-open-folder">
    <div className="dossier-folder-header"><button className="dossier-button dossier-button-secondary" onClick={() => setActiveCategoryTab(null)}><ArrowLeft size={16} />Tous les dossiers</button><h3><Folder size={20} />{section.title}</h3><p className="dossier-proof-meta">{documents.length} documents · du plus récent au plus ancien</p></div>
    <div className="dossier-folder-content">
      <div className="dossier-column"><h4 className="section-label">Informations pertinentes</h4><ul className="clean-list">{section.facts.map(fact => <li key={fact}>{fact}</li>)}</ul></div>
      {section.current_statuses?.length > 0 && <div className="dossier-column"><h4 className="section-label">Statuts documentés actuels</h4>{section.current_statuses.map(item => <p key={item.id}><strong>{item.id}</strong> · {registerStatuses[item.status] || item.status} · {item.date || "Date non précisée"}</p>)}</div>}
      {section.open_items.length > 0 && <div className="dossier-column"><h4 className="section-label">Actions / points ouverts</h4>{section.open_items.map(item => <p key={item.label}>{item.label}<br /><span className="dossier-item-preview">{item.owner} · {item.due}</span></p>)}</div>}
      <details className="dossier-column"><summary className="section-label">Repères du dossier initial — historique conservé</summary><ul className="clean-list">{section.facts.map(fact => <li key={fact}>{fact}</li>)}</ul></details>
      {documents.map(entry => <DocumentItem key={entry.key} entry={entry} onOpenSource={openSource} />)}
      {!documents.length && <p>Aucun document ne correspond aux filtres actuels dans cette catégorie.</p>}
    </div>
  </section>;
})}
              {documents.map(entry => <DocumentItem key={entry.key} entry={entry} onOpenSource={openSource} />)}
              {!documents.length && <p>Aucun document ne correspond aux filtres actuels dans cette catégorie.</p>}
            </div>
          </section>;
        })}
        {!visibleEntries.length && <p>Aucun élément ne correspond aux filtres sélectionnés.</p>}
      </div>
      {sourceOpen && <SourceReader document={sourceDocument} loading={sourceLoading} error={sourceError} onClose={closeSource} />}
    </section>
  );
}

function SourceReader({ document, loading, error, onClose }) {
  const dialog = useRef(null);
  useEffect(() => {
    const element = dialog.current;
    element.showModal();
    return () => { if (element.open) element.close(); };
  }, []);
  return <dialog ref={dialog} className="dossier-source-dialog" aria-labelledby="dossier-source-heading" onCancel={event => { event.preventDefault(); onClose(); }}>
    <header className="dossier-source-header">
      <div><p className="eyebrow">Pièce justificative · texte extrait</p><h2 id="dossier-source-heading">{document?.path.split('/').at(-1) || 'Lecture du document'}</h2>{document && <p className="dossier-proof-meta">{document.path}</p>}</div>
      <button autoFocus className="dossier-button dossier-button-secondary" onClick={onClose}><X size={16} aria-hidden="true" />Fermer</button>
    </header>
    <div className="dossier-source-body" aria-busy={loading}>
      {loading && <p role="status">Chargement du document…</p>}
      {error && <p role="alert">{error}</p>}
      {document && <pre className="dossier-source-text">{document.text || 'Aucun texte extrait disponible.'}</pre>}
    </div>
  </dialog>;
}

function DossierFilter({ label, value, onChange, options }) {
  return (
    <label>
      {label}
      <select value={value} onChange={event => onChange(event.target.value)}>
        <option value="">Tous</option>
        {options.map(([key, text]) => <option key={key} value={key}>{text}</option>)}
      </select>
    </label>
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

function Evidence({ proofs }) {
  const files = new Map();
  for (const proof of proofs) {
    const key = proof.path || proof.document_id;
    if (!files.has(key)) files.set(key, { source: proof, excerpts: new Map() });
    files.get(key).excerpts.set(JSON.stringify([proof.locator, proof.excerpt]), proof);
  }
  return [...files].map(([key, { source, excerpts }]) => <div className="dossier-proof" key={key}>
    <p className="dossier-proof-heading"><FileText size={15} /><strong>{source.path.split('/').at(-1)}</strong></p>
    {[...excerpts.values()].map((proof, index) => <div key={index}>
      <p className="dossier-proof-meta">{proof.locator} · Publication : {proof.published_on || "non précisée"}</p>
      <details className="dossier-excerpt"><summary>Voir l’extrait justificatif · {proof.locator}</summary><blockquote>{proof.excerpt}</blockquote></details>
    </div>)}
    <a className="dossier-button dossier-button-primary" href={`/api/documents/${encodeURIComponent(source.document_id)}/original?download=true`} download><FileText size={16} aria-hidden="true" />Télécharger l’original ({source.path.split('/').at(-1)})<ArrowUpRight size={16} aria-hidden="true" /></a>
  </div>);
}

function DocumentItem({ entry, onOpenSource }) {
  const title = shortTitle({ title: entry.path.split('/').at(-1).replace(/\.[^.]+$/, '') });
  const subjects = [...new Set(entry.points.map(point => professionalSubject(point.item, point.group)))];
  const deadlines = [...new Set(entry.points.map(point => point.item.due).filter(Boolean))];
  return <details className="dossier-item">
    <summary className="dossier-item-summary">
      <span className="dossier-item-heading"><strong>{title}</strong><span className="dossier-item-preview">{entry.support} · {entry.date || 'Date non précisée'} · {entry.groups.map(group => registerLabels[group]).join(' / ')}</span></span>
      <span className="dossier-item-status">{entry.points.length} points</span>
    </summary>
    <div className="dossier-item-content">
      {entry.completion && <p className="dossier-completion-note">Terminé · {entry.completion.reason}{entry.completion.completed_on ? ` · ${entry.completion.completed_on}` : ''}</p>}
      <div className="dossier-item-context"><h5>Objet général du document</h5><p>{subjects.slice(0, 2).join(' ')}{subjects.length > 2 ? ' Les autres points sont détaillés ci-dessous.' : ''}</p></div>
      <dl className="dossier-item-fields">
        <div className="dossier-field-wide"><dt>Catégories du projet</dt><dd>{entry.categories.map(category => category.title).join(' · ')}</dd></div>
        <div><dt>Types d’information</dt><dd>{entry.groups.map(group => registerLabels[group]).join(' · ')}</dd></div>
        <div><dt>Plateforme / support</dt><dd>{entry.support}</dd></div>
        <div><dt>Date du document</dt><dd>{entry.date || 'Non précisée'}</dd></div>
        <div><dt>Échéances citées</dt><dd>{deadlines.join(' · ') || 'Non précisées'}</dd></div>
        <div className="dossier-field-wide"><dt>Personnes / équipes concernées</dt><dd>{entry.context.people.length ? entry.context.people.map(([name, role]) => <span className="dossier-person" key={name}><strong>{name}</strong><span>{role}</span></span>) : 'Non précisées'}</dd></div>
      </dl>
      {Object.entries(registerLabels).filter(([group]) => entry.groups.includes(group)).map(([group, label]) => <section className="dossier-document-points" key={group}><h5>{label}</h5><ul>{entry.points.filter(point => point.group === group).map(point => <li key={point.item.id}><p>{professionalSubject(point.item, group)}</p><span className={`dossier-item-status status-${point.item.status}`}>{registerStatuses[point.item.status] || point.item.status}</span>{point.item.owner && <span className="dossier-point-owner">{point.item.owner} · {point.item.owner_role}</span>}</li>)}</ul></section>)}
      <div className="dossier-item-evidence"><h5>Sources et preuves</h5><Evidence proofs={entry.evidence} onOpenSource={onOpenSource} /></div>
    </div>
  </details>;
}
