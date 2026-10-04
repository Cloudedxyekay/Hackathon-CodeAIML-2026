"""Compare source-backed discrepancies, rather than retrieve the word contradiction."""
import re
from pathlib import Path
from .intelligence import build_project_memory, fold


def is_contradiction_question(question):
    return bool(re.search(r'contradic|incoheren|inconsisten|conflicting|conflits? entre.*(?:sources|informations)', fold(question)))


def comparisons(documents):
    memory = build_project_memory(documents)
    tickets = {t['id']: t for t in memory['tickets']}
    findings = []
    for alert in memory['alerts']:
        proofs = alert['evidence']
        if alert['id'] == 'stale-plan':
            conclusion = alert['description'] + ' Il s’agit d’un plan non actualisé, pas de deux décisions également valides.'
            title = 'Échéancier — plan périmé'
        elif alert['id'] == 'status-conflict':
            # The report actually says green/delivered, not accepted or closed.
            relevant = [t for t in tickets.values() if t['topic'] in {'security', 'accessibility'} and t['status'] != 'completed']
            if not relevant:
                continue
            proofs = proofs[:1] + [p for t in relevant for p in t['evidence']]
            states = '; '.join(f"{t['id']} : {'en validation' if t['status'] == 'in_review' else 'ouvert'}, suivi du {t['last_update']}" for t in relevant)
            conclusion = f'Le rapport présente la sécurité et l’accessibilité en VERT avec des correctifs livrés/appliqués. Les suivis indiquent pourtant {states}. Livraison et acceptation sont distinctes : ces validations restent à obtenir. Le VERT ne prouve pas leur clôture.'
            title = 'Statut — présentation optimiste à nuancer'
        elif alert['id'] == 'stale-risk':
            resolved = [t for t in tickets.values() if t['topic'] == 'integration' and t['status'] == 'completed']
            conclusion = 'La ligne du registre conserve le risque du connecteur « Ouvert », tandis que ' + '; '.join(f"{t['id']} est fermé depuis le {t['completed_on']}" for t in resolved) + '. Vérifier la date de suivi de la ligne et réconcilier le registre avec la preuve de résolution; la date du classeur ne suffit pas à dater ce statut.'
            title = 'Risques — registre à réconcilier'
        else:
            continue
        if len({p['path'] for p in proofs}) < 2:
            continue
        sources = list(dict.fromkeys(f"{Path(p['path']).name} ({p.get('published_on') or 'date source inconnue'})" for p in proofs))
        findings.append({'id': alert['id'], 'title': title, 'conclusion': conclusion,
                         'label': title + '. Sources : ' + ' ; '.join(sources) + '. ' + conclusion,
                         'evidence': proofs})
    return findings
