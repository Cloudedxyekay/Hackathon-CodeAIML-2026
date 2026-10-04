import { useEffect, useRef, useState } from "react";
import { Upload, FileText, CheckCircle2, ArrowRight, RefreshCw, History } from "lucide-react";
import "../updates.css";

const ACCEPT = ".eml,.txt,.md,.csv,.xlsx,.pdf,.png,.jpg,.jpeg,.webp";
async function responseJSON(response) {
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "L'opération n'a pas abouti. Réessayez.");
  return data;
}

export default function UpdateSimulator({ onRefresh, onNavigate }) {
  const [preview, setPreview] = useState(null), [text, setText] = useState(""), [documentDate, setDocumentDate] = useState("");
  const [analysis, setAnalysis] = useState(null), [integrated, setIntegrated] = useState(null), [imports, setImports] = useState([]);
  const [dirty, setDirty] = useState(false), [busy, setBusy] = useState(""), [error, setError] = useState("");
  const inFlight = useRef(false), input = useRef(null);
  async function loadHistory() {
    const data = await fetch("/api/updates").then(responseJSON); setImports(data.imports);
  }
  useEffect(() => { loadHistory().catch(err => setError(err.message)); }, []);
  async function upload(file) {
    if (!file || inFlight.current) return;
    if (file.size > 20 * 1024 * 1024) { setError("Choisissez un fichier de 20 Mo maximum."); return; }
    inFlight.current = true; setBusy("Lecture du fichier et extraction du texte…"); setError("");
    setPreview(null); setAnalysis(null); setIntegrated(null);
    try {
      const form = new FormData(); form.append("file", file);
      const data = await fetch("/api/updates/preview", { method: "POST", body: form }).then(responseJSON);
      setPreview(data); setText(data.extracted_text); setDocumentDate(data.detected_date || ""); setAnalysis(data.analysis); setDirty(false);
    } catch (err) { setError(err.message); }
    finally { inFlight.current = false; setBusy(""); if (input.current) input.current.value = ""; }
  }
  async function review(commit) {
    if (!preview || inFlight.current) return;
    inFlight.current = true; setError(""); setBusy(commit ? "Intégration et actualisation des vues du projet…" : "Comparaison avec l'état actuel…");
    try {
      const data = await fetch(`/api/updates/${preview.id}/${commit ? "integrate" : "analyze"}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reviewed_text: text, document_date: documentDate !== preview.detected_date ? documentDate || null : null })
      }).then(responseJSON);
      setAnalysis(commit ? data.analysis : data); setDirty(false);
      if (commit) { setIntegrated(data); await Promise.all([loadHistory(), onRefresh?.()]); }
    } catch (err) { setError(err.message); }
    finally { inFlight.current = false; setBusy(""); }
  }
  function showHistory(item) { setIntegrated(item); setAnalysis(item.analysis); setPreview(null); setError(""); setDirty(false); }
  async function changeImport(item) {
    if (inFlight.current) return;
    const restore = item.status === 'removed';
    if (!restore && !window.confirm('Retirer cet import et recalculer le projet à partir des sources restantes ? Les fichiers originaux sont conservés et cet import pourra être restauré.')) return;
    inFlight.current = true; setBusy(restore ? 'Restauration de l’import…' : 'Retrait de l’import…'); setError('');
    try {
      await fetch(`/api/updates/${item.id}/${restore ? 'restore' : 'remove'}`, { method: 'POST' }).then(responseJSON);
      setIntegrated(null); setAnalysis(null); setPreview(null);
      await Promise.all([loadHistory(), onRefresh?.()]);
    } catch (err) { setError(err.message); }
    finally { inFlight.current = false; setBusy(''); }
  }
  return <section className="stack update-workspace">
    <div className="panel update-intro"><div><p className="eyebrow">NOUVELLE INFORMATION</p><h2>Faire évoluer la mémoire du projet</h2><p>Ajoutez la pièce reçue pendant la démonstration. NOVA compare son contenu à l'état précédent, puis l'intègre aux vues du projet en conservant l'historique.</p></div><ol className="update-steps"><li>1 · Ajouter</li><li>2 · Vérifier les impacts</li><li>3 · Intégrer</li></ol></div>
    <div className="panel update-dropzone" onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); upload(event.dataTransfer.files[0]); }}>
      <Upload size={30} aria-hidden="true" /><h3>Déposez le nouveau fichier ici</h3><p>Courriel EML, texte, PDF, classeur Excel ou image · 20 Mo maximum</p>
      <input ref={input} type="file" accept={ACCEPT} disabled={!!busy} aria-label="Fichier du nouvel événement" onChange={event => upload(event.target.files[0])} />
      <small>TXT, MD, CSV, XLSX, PDF, PNG, JPG, JPEG et WEBP. Le texte des images est extrait localement et reste à vérifier.</small>
    </div>
    {busy && <p className="update-progress" role="status" aria-live="polite"><RefreshCw size={16} className="update-spinner" />{busy}</p>}
    {error && <p className="memory-error" role="alert">{error}</p>}
    {preview && !integrated && <div className="panel update-review">
      <div className="update-heading"><div><p className="eyebrow">APERÇU · NON ENCORE INTÉGRÉ</p><h3><FileText size={19} /> {preview.filename}</h3></div><a href={`/api/updates/${preview.id}/file`} target="_blank" rel="noreferrer">Ouvrir l'original ↗</a></div>
      {preview.warnings.map(message => <p className="update-notice" key={message}>{message}</p>)}
      <label className="field-label" htmlFor="update-date">Date du document</label><input id="update-date" type="date" value={documentDate} disabled={!!busy} onChange={event => { setDocumentDate(event.target.value); setDirty(true); }} />
      {!documentDate && <p className="update-notice">Aucune date source détectée. Sans date confirmée, le calendrier affichera la réception du fichier, et non la date supposée de l'événement.</p>}
      <label className="field-label" htmlFor="update-text">Texte extrait — vérifiez les dates, montants et statuts</label>
      <textarea id="update-text" value={text} disabled={!!busy} onChange={event => { setText(event.target.value); setDirty(true); }} placeholder="Si le texte n'a pas pu être extrait, saisissez une transcription fidèle de la pièce." />
      <p className="update-help">Toute correction est enregistrée séparément; le fichier original reste inchangé.</p>
      <button className="secondary" disabled={!!busy || !text.trim()} onClick={() => review(false)}><RefreshCw size={16} />Analyser les impacts</button>
      {dirty && <p role="status">Le contenu a été modifié. Analysez à nouveau les impacts avant l'intégration.</p>}
    </div>}
    {integrated && <div className="panel update-success" role="status"><CheckCircle2 size={24} /><div><h3>{integrated.filename} intégré</h3><p>Le document et ses preuves sont disponibles dans le dossier, la recherche et la mémoire du projet.</p><div className="update-links">{[["dossier", "Voir le dossier"], ["calendar", "Voir le calendrier"], ["timeline", "Voir la chronologie"]].map(([tab, label]) => <button key={tab} className="secondary" onClick={() => onNavigate?.(tab)}>{label}<ArrowRight size={15} /></button>)}<a href={`/api/documents/${analysis.document.id}/original`} target="_blank" rel="noreferrer">Télécharger l'original</a></div></div></div>}
    {analysis && <div className={`update-analysis ${dirty ? "update-stale" : ""}`}>
      <div className="panel"><p className="eyebrow">01 · CE QUI CHANGE</p><h3>Qu'est-ce qui vient de changer ?</h3>
        {analysis.changes.map((change, index) => <article className="update-change" key={`${change.title}-${index}`}><strong>{change.title}</strong><span className={`update-kind ${change.kind}`}>{change.kind === "confirmed" ? "Évolution documentée" : change.kind === "proposal" ? "Proposition / à confirmer" : "Information reçue"}</span><dl><div><dt>Avant</dt><dd>{change.before}</dd></div><div><dt>Après</dt><dd>{change.after}</dd></div></dl><details><summary>Consulter les preuves</summary>{change.evidence.map((proof, index) => <div key={`${proof.document_id}-${index}`}><p>{proof.path} · {proof.locator}</p><blockquote>{proof.excerpt}</blockquote></div>)}</details></article>)}
      </div>
      <div className="panel"><p className="eyebrow">02 · INFORMATIONS AFFECTÉES</p><h3>Tâches et événements directement concernés</h3>
        {analysis.affected_information.filter(item => item.event_id).length ? <ul className="update-affected">{analysis.affected_information.filter(item => item.event_id).map(item => <li key={item.id}><button className="secondary" onClick={() => onNavigate?.("timeline", integrated ? item.event_id : item.previous_event_id || item.event_id)}>{item.title}<ArrowRight size={16} /></button></li>)}</ul> : <p>Aucune tâche ou événement directement lié n'a été identifié.</p>}
      </div>
      <div className="panel"><p className="eyebrow">03 · SUITE À DONNER</p><h3>Quelles actions devraient être prises ?</h3><ol className="update-actions">{analysis.actions.map(action => <li key={action}>{action}</li>)}</ol><p className="update-notice">{analysis.notice}</p><details><summary>{analysis.events.length} événement(s) associé(s) au calendrier et à la chronologie</summary><ul>{analysis.events.map(item => <li key={item.id}>{item.date} · {item.title} {item.date_kind === "received" ? "(réception — date source inconnue)" : item.date_kind === "planned" ? "(planifié)" : ""}</li>)}</ul></details></div>
      {preview && !integrated && <div className="panel update-commit"><div><strong>Intégrer cette source au projet</strong><p>L'état précédent est conservé dans l'historique des imports.</p></div><button className="primary" disabled={!!busy || dirty || !text.trim()} onClick={() => review(true)}><CheckCircle2 size={18} />Intégrer au projet</button></div>}
    </div>}
    <div className="panel"><div className="update-heading"><h3><History size={19} /> Historique des imports</h3><span>{imports.length} import(s)</span></div>{!imports.length ? <p>Aucun nouvel événement intégré pour le moment.</p> : <ul className="update-history">{imports.map(item => <li key={item.id}><button onClick={() => item.status !== "removed" && showHistory(item)} disabled={!!busy || item.status === "removed"}><FileText size={17} /><span><strong>{item.filename}</strong><small>{new Date(item.integrated_at).toLocaleString("fr-CA")}</small></span><ArrowRight size={17} /></button><button className="secondary" disabled={!!busy} onClick={() => changeImport(item)}>{item.status === "removed" ? "Restaurer cet import" : "Retirer cet import"}</button></li>)}</ul>}</div>
  </section>;
}
