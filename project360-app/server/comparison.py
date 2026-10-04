"""Isolated, evidence-grounded multi-project comparison. Never writes NOVA data."""
import base64
import json
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .ingest import DEFAULT_CORPUS, READERS
from .intelligence import PROCESSED, build_project_memory, evidence, fold, source_date, dates_in, classify

STORE = PROCESSED.parent / 'comparison'
router = APIRouter(prefix='/api/comparison', tags=['comparison'])

DEMO_TEXTS = {
    'SEC-900.txt': 'TICKET SEC-900\nTitre : Journalisation administrateur\nCréé : 1 septembre 2026\nDemandeur : Alice Martin\nStatut : Fermé\nCommentaires :\n20 sept 10:00 - Alice : Les exports sont maintenant journalisés. Re-test OK. Validé. Je ferme.\n',
    'OPS-901.txt': 'TICKET OPS-901\nTitre : Runbook et rollback\nCréé : 2 septembre 2026\nDemandeur : Paul Roy\nStatut : Fermé\nCommentaires :\n21 sept 10:00 - Paul : Le runbook inclut sauvegarde, rollback et contrôle après déploiement. Rollback testé. Validé. Je ferme.\n',
    'ACC-902.txt': 'TICKET ACC-902\nTitre : Navigation au clavier\nCréé : 3 septembre 2026\nDemandeur : Emma Dubois\nStatut : Fermé\nCommentaires :\n23 sept 10:00 - Emma : Tous les boutons sont accessibles au clavier. Validé. Je ferme.\n',
    'decision.txt': 'Date : 22 septembre 2026\nDécision : la date cible de mise en production est déplacée au 5 novembre 2026. Donc approuvé. Le 5 novembre devient la date officielle.\n',
    'equipe.txt': 'Date : 24 septembre 2026\nChargée de projet : Alice Martin\nResponsable : Paul Roy\nParticipants : Alice Martin, Paul Roy, Emma Dubois\nAlice Martin pilote ATLAS. Paul Roy prépare le lancement. Emma Dubois coordonne les tests.\nActions\n- Paul Roy : fournir le guide de déploiement le 15 octobre 2026.\n- Emma Dubois : confirmer les tests utilisateurs le 20 octobre 2026.\n',
    'fonctionnalites.txt': 'Date : 25 septembre 2026\nDécision : la portée de phase 1 comprend le suivi des demandes, les notifications et un tableau de bord. Les optimisations mobiles sont reportées à la phase 2.\n',
    'budget.txt': 'Date : 26 septembre 2026\nDécision : budget maximal approuvé de 150 000 $ CAD. Un ajout de rapports avancés de 12 000 $ CAD est approuvé séparément. Aucune facture contestée dans ce compte rendu.\n',
    'INT-903.txt': 'TICKET INT-903\nTitre : Synchronisation des notifications\nCréé : 27 septembre 2026\nDemandeur : Paul Roy\nStatut : Ouvert\nDescription : Risque de retard des notifications lors des pics de charge.\nCommentaires :\n28 sept 10:00 - Paul : Le fournisseur doit tester la file de notifications avant le lancement.\n',
    'suivi.txt': 'Date : 29 septembre 2026\nPoints à vérifier : confirmer le test de charge des notifications et publier le guide de déploiement.\n',
}


class ImportedFile(BaseModel):
    name: str
    content: str


class ImportRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    files: list[ImportedFile] = Field(min_length=1, max_length=100)


class CompareRequest(BaseModel):
    projects: list[str] = Field(min_length=2, max_length=6)


def load_project(identifier):
    if identifier == 'nova':
        path = PROCESSED / 'documents.json'
        docs = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
        return {'id': 'nova', 'name': 'NOVA', 'demo': False, 'documents': docs}
    if not re.fullmatch(r'[a-f0-9]{32}', identifier):
        raise HTTPException(404, 'Projet introuvable')
    path = STORE / identifier / 'project.json'
    if not path.is_file():
        raise HTTPException(404, 'Projet introuvable')
    project = json.loads(path.read_text(encoding='utf-8'))
    if project.get('demo') and project.get('demo_version', 0) < 2:
        for index, (name, text) in enumerate(DEMO_TEXTS.items()):
            relative = f'demo-v2/{name}'
            original = path.parent / relative
            original.parent.mkdir(exist_ok=True)
            original.write_text(text, encoding='utf-8')
        project['documents'] = [{'id': f'demo-{index:03d}', 'path': f'demo-v2/{name}', 'extension': '.txt', 'text': text, 'title': Path(name).stem} for index, (name, text) in enumerate(DEMO_TEXTS.items())]
        project['demo_version'] = 2
        path.write_text(json.dumps(project, ensure_ascii=False), encoding='utf-8')
    return project


def summarize(project):
    docs = project['documents']
    memory = build_project_memory(docs)
    def entry(text, proofs):
        return {'text': text, 'evidence': [{**proof, 'project_id': project['id']} for proof in proofs]}
    decisions = [entry(e['summary'], e['evidence']) for e in memory['events'] if e['type'] == 'decision' and e['date_kind'] == 'observed']
    risks = [entry(t['id'] + ' : ' + t['title'] + ' (' + t['status'] + ')', t['evidence']) for t in memory['tickets'] if t['status'] != 'completed']
    risks += [entry(e['summary'], e['evidence']) for e in memory['events'] if e['type'] == 'risk' and e['owner_role'] == 'Propriétaire du risque' and e['status'] != 'completed']
    from .synthesis import build_synthesis
    registers = build_synthesis(docs, memory)['groups']
    axes = {
        'scope': [entry(e['summary'], e['evidence']) for e in memory['events'] if e['topic'] == 'scope'],
        'decisions': decisions,
        'owners': [entry(r['owner'] + ' — ' + r['title'] + ' (' + r['owner_role'] + ')', r['evidence']) for r in registers['responsables'] if r['owner']],
        'commitments': [entry(r['title'], r['evidence']) for r in registers['engagements']],
        'schedule': [entry(r['title'] + ' — ' + (r['due'] or 'Date non précisée') + ' (' + r['status'] + ')', r['evidence']) for r in registers['echeances']],
        'finance': [entry(e['summary'], e['evidence']) for e in memory['events'] if e['topic'] == 'finance'],
        'risks': risks,
        'quality': [entry(a['description'], a['evidence']) for a in memory['alerts']],
    }
    for doc in docs:
        for number, line in enumerate(doc['text'].splitlines(), 1):
            if fold(line).startswith('points a verifier :'):
                axes['quality'].append(entry(line.split(':', 1)[1].strip(), [evidence(doc, line, f'Ligne {number}')]))
    if memory['schedule']['current_target']:
        authority = next(h for h in reversed(memory['schedule']['history']) if h['target'] == memory['schedule']['current_target'] and h['status'] in ('approved', 'conditional'))
        axes['schedule'].insert(0, entry('Cible approuvée : ' + memory['schedule']['current_target'] + (' — conditionnelle' if memory['schedule']['conditional'] else ''), authority['evidence']))
    elif project['id'] != 'nova':
        # The original NOVA extractor specializes October targets. Bonus adds
        # all-month extraction locally, without changing the existing program.
        candidates = []
        for doc in docs:
            published = source_date(doc)
            if not published or doc['path'].startswith('08_Archives'):
                continue
            for number, line in enumerate(doc['text'].splitlines(), 1):
                if not re.search(r'mise en production|lancement|date officielle', fold(line)):
                    continue
                kind, status = classify(line)
                dates = [d['date'] for d in dates_in(line, int(published[:4])) if d['date'] > published]
                if dates and kind == 'decision' and status in ('approved', 'conditional'):
                    candidates.append((published, dates[-1], status, evidence(doc, line, f'Ligne {number}')))
        if candidates:
            published, target, status, proof = sorted(candidates, key=lambda item: item[0])[-1]
            axes['schedule'].insert(0, entry('Cible documentée : ' + target + ' (' + status + ')', [proof]))
    return {**project, 'memory': memory, 'axes': axes}


def compare_projects(projects):
    summaries = [summarize(p) for p in projects]
    suggestions, knowledge = [], []
    for source in summaries:
        validated = [t for t in source['memory']['tickets'] if t['status'] == 'completed' and t['completed_on']]
        for target in summaries:
            if target['id'] == source['id']:
                continue
            for closed in validated:
                matches = [t for t in target['memory']['tickets'] if t['status'] != 'completed' and t['topic'] == closed['topic']]
                for opened in matches:
                    proofs = [{**p, 'project_id': source['id']} for p in closed['evidence']] + [{**p, 'project_id': target['id']} for p in opened['evidence']]
                    item = {'title': f"{source['name']} → {target['name']} : {closed['title']}",
                            'source_project': source['id'], 'target_project': target['id'],
                            'source_name': source['name'], 'target_name': target['name'],
                            'topic': closed['topic'], 'practice': closed['title'],
                            'reason': f"Chez {source['name']}, ce point a été validé le {closed['completed_on']}. Chez {target['name']}, un problème sur le même sujet reste à régler ({opened['id']}). Ça vaut donc la peine de regarder ce qui a fonctionné ailleurs.",
                            'action': f"Je te suggère de regarder la méthode utilisée par {source['name']}. Elle pourrait donner un bon point de départ à l’équipe de {target['name']}.",
                            'adaptation': 'Avant de la reprendre, vérifie que le problème et les outils sont comparables. Adapte ce qui doit l’être, puis fais un test avec ton équipe.',
                            'evidence': proofs}
                    knowledge.append(item)
                    suggestions.append({**item, 'priority': 'important', 'title': f"Pour {target['name']}, la méthode de {source['name']} pourrait aider : {opened['title']}"})
        for gate in source['memory']['gates']:
            suggestions.append({'priority': 'urgent', 'title': source['name'] + ' — ' + gate['title'],
                                'action': 'Je commencerais par faire le point avec l’équipe qui doit valider ce sujet. Il faut son accord avant le lancement.',
                                'reason': 'Les documents montrent que ce point n’est pas encore validé. Mieux vaut le clarifier maintenant pour éviter une mauvaise surprise au lancement.',
                                'evidence': [{**p, 'project_id': source['id']} for p in gate['evidence']]})
        for alert in source['memory']['alerts']:
            if alert['id'] != 'pending-gates':
                suggestions.append({'priority': 'important', 'title': source['name'] + ' — ' + alert['title'],
                                    'action': 'Je te conseille de vérifier quelle version est à jour et de corriger les documents concernés.', 'reason': alert['description'],
                                    'evidence': [{**p, 'project_id': source['id']} for p in alert['evidence']]})
    observations = []
    for project in summaries:
        if project['axes']['schedule']:
            current = project['axes']['schedule'][0]
            match = re.search(r'\d{4}-\d{2}-\d{2}', current['text'])
            if match:
                conditional = 'condition' in current['text']
                observations.append({'text': f"{project['name']} vise le {match[0]}. " + ('La date reste sous conditions : les validations doivent encore être confirmées.' if conditional else 'Cette date est indiquée dans les documents ; les preuves permettent de vérifier les conditions qui l’accompagnent.'), 'evidence': current['evidence']})
    if knowledge:
        item = knowledge[0]
        observations.append({'text': f"Il y a une piste intéressante pour {item['target_name']} : {item['source_name']} a déjà validé une solution sur un sujet similaire. L’équipe pourrait s’en inspirer, après avoir vérifié qu’elle convient à son projet.", 'evidence': item['evidence']})
    return {'projects': [{k: p[k] for k in ('id', 'name', 'demo', 'axes')} | {'as_of': p['memory']['as_of'], 'documents': len(p['documents']), 'undated': len(p['memory']['extraction']['undated_documents'])} for p in summaries],
            'observations': observations,
            'suggestions': suggestions, 'knowledge': knowledge,
            'method': 'Extraction locale fondée sur les sources. Les propositions, validations et dates planifiées restent distinctes. Aucun classement global ni réalisation déduite. Les suggestions nécessitent une validation humaine.'}


@router.get('/projects')
def list_projects():
    projects = [load_project('nova')]
    if STORE.exists():
        projects += [load_project(p.parent.name) for p in STORE.glob('*/project.json')]
    return [{'id': p['id'], 'name': p['name'], 'demo': p['demo'], 'documents': len(p['documents'])} for p in projects]


def import_files(req, demo=False):
    # Validate the whole payload before creating anything on disk.
    if not req.name.strip():
        raise HTTPException(400, 'Le nom du projet est obligatoire')
    decoded, total = [], 0
    for file in req.files:
        name = Path(file.name.replace('\\', '/')).name
        if Path(name).suffix.lower() not in READERS:
            raise HTTPException(400, 'Format non pris en charge : ' + name)
        try:
            content = base64.b64decode(file.content, validate=True)
        except ValueError:
            raise HTTPException(400, 'Fichier encodé invalide') from None
        total += len(content)
        if total > 20 * 1024 * 1024:
            raise HTTPException(413, 'Le corpus doit rester sous 20 Mo')
        decoded.append((name, content))
    identifier = uuid.uuid4().hex
    root = STORE / identifier
    root.mkdir(parents=True)
    docs, warnings = [], []
    for index, (name, content) in enumerate(decoded):
        path = root / f'{index:03d}' / name
        path.parent.mkdir()
        path.write_bytes(content)
        try:
            text = READERS[path.suffix.lower()](path)
        except Exception as exc:
            warnings.append(name + ' : extraction impossible')
            text = 'Extraction failed: ' + type(exc).__name__
        docs.append({'id': f'doc-{index:03d}', 'path': path.relative_to(root).as_posix(), 'extension': path.suffix.lower(), 'text': text, 'title': path.stem})
    project = {'id': identifier, 'name': req.name.strip(), 'demo': demo, 'documents': docs}
    (root / 'project.json').write_text(json.dumps(project, ensure_ascii=False), encoding='utf-8')
    return {'id': identifier, 'warnings': warnings}


@router.post('/projects')
def import_project(req: ImportRequest):
    return import_files(req)


@router.post('/demo')
def create_demo():
    return import_files(ImportRequest(name='ATLAS — démonstration fictive', files=[ImportedFile(name=name, content=base64.b64encode(text.encode()).decode()) for name, text in DEMO_TEXTS.items()]), demo=True)


@router.post('/compare')
def compare(req: CompareRequest):
    if len(set(req.projects)) != len(req.projects):
        raise HTTPException(400, 'Sélectionnez des projets distincts')
    return compare_projects([load_project(identifier) for identifier in req.projects])


@router.get('/projects/{project_id}/documents/{document_id}/original')
def original(project_id: str, document_id: str):
    project = load_project(project_id)
    doc = next((d for d in project['documents'] if d['id'] == document_id), None)
    if doc is None:
        raise HTTPException(404, 'Document introuvable')
    root = DEFAULT_CORPUS.resolve() if project_id == 'nova' else (STORE / project_id).resolve()
    path = (root / doc['path']).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(404, 'Fichier introuvable')
    return FileResponse(path, filename=path.name, media_type='application/octet-stream', headers={'X-Content-Type-Options': 'nosniff'})
