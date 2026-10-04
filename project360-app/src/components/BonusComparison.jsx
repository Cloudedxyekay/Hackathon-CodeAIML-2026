import { useEffect, useState } from 'react';

const aspects = {scope:'Fonctionnalités', decisions:'Décisions', owners:'Responsables', commitments:'Engagements', schedule:'Échéances', finance:'Budget et contrats', risks:'Risques et blocages', quality:'Points à clarifier'};
async function api(path, body) {
 const response = await fetch('/api/comparison'+path, body === undefined ? undefined : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const data=await response.json();
 if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:'Demande impossible.');
 return data;
}
export default function BonusComparison() {
 const [projects,setProjects]=useState([]),[selected,setSelected]=useState(['nova']),[name,setName]=useState(''),[files,setFiles]=useState([]),[result,setResult]=useState(null),[aspect,setAspect]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[brief,setBrief]=useState(null);
 async function refresh(){setProjects(await api('/projects'));}
 useEffect(()=>{refresh().catch(e=>setError(e.message));},[]);
 async function run(action){setBusy(true);setError('');setNotice('');try{await action();}catch(e){setError(e.message);}finally{setBusy(false);}}
 async function upload(){
  if(!name.trim()||!files.length) throw new Error('Indiquez le nom du projet et choisissez ses documents.');
  if(files.length>100||files.reduce((sum,f)=>sum+f.size,0)>20*1024*1024) throw new Error('Maximum : 100 fichiers et 20 Mo.');
  const encoded=await Promise.all(files.map(file=>new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve({name:file.name,content:String(r.result).split(',')[1]});r.onerror=()=>reject(new Error('Lecture impossible.'));r.readAsDataURL(file);}))); 
  const imported=await api('/projects',{name:name.trim(),files:encoded});await refresh();setSelected(p=>[...p,imported.id]);setResult(null);setNotice(imported.warnings.join(' · ')||'Projet importé. Lancez la comparaison.');
 }
 function exportResult(){const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='comparaison-projets.json';a.click();URL.revokeObjectURL(url);}
 async function downloadBrief(){
  const response=await fetch('/api/brief/pdf');
  if(!response.ok){const data=await response.json();throw new Error(data.detail||'Le briefing n’a pas pu être généré.');}
  const url=URL.createObjectURL(await response.blob());
  const link=document.createElement('a');link.href=url;link.download='NOVA-briefing-executif.pdf';document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  setNotice('Ton briefing PDF est prêt : regarde dans les téléchargements.');
 }
 return <section className="stack bonus-comparison">
  <div className="panel"><p className="eyebrow">Bonus</p><h2>Comparaison de projets</h2><p>Comparez les faits documentés, découvrez des pratiques réutilisables et préparez les prochaines actions. NOVA reste en lecture seule.</p></div>
  <div className="panel bonus-pdf-card"><div><p className="eyebrow">Briefing exécutif NOVA</p><h3>Tout ce qu’il faut savoir, dans un PDF</h3><p>Ce qui s’est passé, les grandes décisions, qui les a annoncées et ce qui reste à faire. Les preuves sont regroupées à la fin.</p></div><button className="dossier-button dossier-button-primary" disabled={busy} onClick={()=>run(downloadBrief)}>{busy?'Traitement en cours…':'Générer le briefing PDF'}</button></div>
  <details className="panel"><summary>Ajouter un autre projet</summary><div className="bonus-actions"><label>Nom du projet<input value={name} onChange={e=>setName(e.target.value)} /></label><label>Documents<input type="file" multiple accept=".pdf,.xlsx,.eml,.txt,.md,.csv" onChange={e=>setFiles([...e.target.files])}/></label><button className="dossier-button dossier-button-primary" disabled={busy} onClick={()=>run(upload)}>Importer</button></div><p className="dossier-proof-meta">PDF, Excel, courriel, texte, Markdown et CSV · 100 fichiers / 20 Mo maximum · stockage séparé de NOVA.</p><button className="dossier-button dossier-button-secondary" disabled={busy} onClick={()=>run(async()=>{const demo=await api('/demo',{});await refresh();setSelected(p=>[...p,demo.id]);setResult(null);setNotice('ATLAS est fictif et sert uniquement à la démonstration.');})}>Ajouter ATLAS — démonstration fictive</button></details>
  <div className="panel"><h3>Choisir les projets</h3><div className="bonus-projects">{projects.map(p=><label key={p.id}><input type="checkbox" disabled={busy} checked={selected.includes(p.id)} onChange={e=>{setSelected(previous=>e.target.checked?[...previous,p.id]:previous.filter(id=>id!==p.id));setResult(null);}}/><span><strong>{p.name}</strong><small>{p.documents} documents{p.demo?' · FICTIF':''}</small></span></label>)}</div><button className="dossier-button dossier-button-primary" disabled={busy||selected.length<2||selected.length>6} onClick={()=>run(async()=>setResult(await api('/compare',{projects:selected})))}>{busy?'Traitement en cours…':'Comparer les projets'}</button><p className="dossier-proof-meta">Sélectionnez de 2 à 6 projets.</p></div>
  {error&&<p className="memory-error" role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}
  {result&&<>
   <SimpleComparison result={result} aspect={aspect} setAspect={setAspect} onExport={exportResult} />
   <div className="panel"><h3>Suggestions</h3><p>Actions proposées à valider. Rouge : condition de lancement ouverte. Jaune : vérification ou adaptation importante.</p>{result.suggestions.length?result.suggestions.map((item,index)=><Recommendation key={index} item={item}/>):<p>Aucune suggestion étayée par les sources disponibles.</p>}</div>
  </>}
  <details className="panel"><summary>Briefing exécutif NOVA</summary><button className="dossier-button dossier-button-secondary" disabled={busy} onClick={()=>run(async()=>{const response=await fetch('/api/brief');if(!response.ok)throw new Error('Briefing indisponible.');setBrief(await response.json());})}>Afficher le briefing existant</button>{brief&&<><h3>{brief.title}</h3><p>{brief.status}</p><ul>{brief.top_points.map(p=><li key={p}>{p}</li>)}</ul><h4>Risques</h4><ul>{brief.risks.map(p=><li key={p}>{p}</li>)}</ul></>}</details>
 </section>;
}
function shortFact(item) {
 const lines=item.text.replace(/\*\*/g,'').split('\n').map(line=>line.trim()).filter(line=>line && !/^(Date\s*:|Subject:|From:|To:|Participants\s*:|\[page|\[sheet)/i.test(line));
 const meaningful=lines.find(line=>/^(Décision|Budget|Cible|Action|Points à vérifier)/i.test(line)) || lines.find(line=>line.length>25) || lines[0] || item.text;
 return meaningful.replace(/^Décision\s*:\s*/i,'').replace(/\bapproved\b/g,'approuvé').replace(/\bconditional\b/g,'sous conditions').replace(/\bopen\b/g,'ouvert').replace(/\bin_review\b/g,'en validation').replace(/\breported\b/g,'à confirmer').replace(/\bplanned\b/g,'prévu').replace(/\bsuperseded\b/g,'ancienne date');
}
function SimpleComparison({result,aspect,setAspect,onExport}) {
 const mainAspects=['schedule','owners','finance','risks'];
 return <div className="panel"><div className="bonus-actions"><h3>Les différences en un coup d’œil</h3><label>Que voulez-vous comparer ?<select value={aspect} onChange={e=>setAspect(e.target.value)}><option value="">L’essentiel</option>{Object.entries(aspects).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label><button className="dossier-button dossier-button-secondary" onClick={onExport}>Exporter</button></div>
  {result.projects.some(p=>p.demo)&&<p className="bonus-demo-note">ATLAS est un exemple fictif pour illustrer la comparaison.</p>}
  {result.observations?.length>0&&<div className="bonus-observations"><h4>Ce que je remarque</h4>{result.observations.map((item,index)=><div key={index}><p>{item.text}</p><details><summary>Sur quoi je m’appuie</summary><Proofs evidence={item.evidence}/></details></div>)}</div>}
  <div className="bonus-simple-grid">{result.projects.map(project=><article className="bonus-project-card" key={project.id}><h3>{project.demo?'ATLAS · exemple':project.name}</h3><p className="dossier-proof-meta">Mis à jour au {project.as_of||'date à confirmer'}</p>{(aspect?[aspect]:mainAspects).map(key=>{
   const items=project.axes[key];
   const facts=[...new Set(items.map(shortFact))];
   const reusable=(result.knowledge||[]).filter(item=>item.target_project===project.id && ['risks','commitments'].includes(key));
   return <section className="bonus-fact" key={key}><h4>{aspects[key]}</h4>{facts.length?<ul>{facts.slice(0,2).map((text,index)=><li key={index}>{text.length>220?text.slice(0,217)+'…':text}</li>)}</ul>:<p className="dossier-proof-meta">À confirmer</p>}{reusable.map((item,index)=><div className="bonus-reuse-note" key={index}><p><strong>Une piste pour ce projet :</strong> s’inspirer de {item.source_name} pour {item.practice.toLocaleLowerCase('fr')}.</p><details><summary>Pourquoi cette pratique peut aider</summary><p>{item.reason}</p><p>{item.adaptation}</p><Proofs evidence={item.evidence}/></details></div>)}{items.length>0&&<details><summary>Voir les détails et les preuves{facts.length>2?` (${facts.length} points)`:''}</summary>{items.map((item,index)=><div key={index}><p>{shortFact(item)}</p><Proofs evidence={item.evidence}/></div>)}</details>}</section>;
  })}</article>)}</div>
  <details className="bonus-method"><summary>Comment lire cette comparaison ?</summary><p>Les dates approuvées sont distinguées des prévisions. Une livraison ne signifie pas une validation. Les informations manquantes restent à confirmer. Les recommandations sont à adapter à chaque projet.</p></details>
 </div>;
}
function Proofs({evidence}){return evidence.map((p,index)=><details className="bonus-proof" key={index}><summary>Source : {p.path.split('/').at(-1)}</summary><p>{p.published_on||'Date inconnue'} · {p.locator}</p><blockquote>{p.excerpt}</blockquote><a className="dossier-button dossier-button-secondary" href={`/api/comparison/projects/${encodeURIComponent(p.project_id)}/documents/${encodeURIComponent(p.document_id)}/original`} download>Télécharger l’original</a></details>);}
function Recommendation({item}){return <details className={`bonus-recommendation priority-${item.priority||'knowledge'}`}><summary>{item.priority&&<span className="dossier-item-status">{item.priority==='urgent'?'Urgent':'Important'}</span>} {item.title}</summary><dl><dt>Ce que je te propose</dt><dd>{item.action}</dd><dt>Ce qui me fait dire ça</dt><dd>{item.reason}</dd>{item.adaptation&&<><dt>Avant de te lancer</dt><dd>{item.adaptation}</dd></>}</dl><Proofs evidence={item.evidence}/></details>;}
