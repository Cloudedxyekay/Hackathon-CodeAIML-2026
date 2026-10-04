"""Attach evidence registers to the existing project categories."""
from copy import deepcopy
import re

from .synthesis import build_synthesis, current_commitments


SECTION_TOPICS = {
    'pilotage': {'governance', 'delivery'},
    'go-live': {'schedule', 'operations'},
    'portee': {'scope'},
    'finance': {'finance'},
    'architecture': {'architecture', 'data', 'integration', 'performance'},
    'securite': {'security'},
    'accessibilite': {'accessibility'},
}

SECTION_NAMES = {
    'pilotage': 'Décisions et responsables',
    'go-live': 'Date de lancement et préparatifs',
    'portee': 'Fonctionnalités et changements',
    'finance': 'Budget, factures et contrats',
    'architecture': 'Système et données',
    'securite': 'Sécurité et vérifications',
    'accessibilite': 'Accessibilité et tests',
    'risques': 'Risques et points à clarifier',
}


def build_dossier(base, documents, memory):
    result = deepcopy(base)
    registers = build_synthesis(documents, memory)
    excluded_paths = {'README.txt', 'MANIFEST.csv'}
    commitments = current_commitments(registers, memory)
    result['historical_summary'] = deepcopy(result.get('summary', {}))
    charter = next((doc for doc in documents if 'Charte_Projet' in doc['path'] and not doc['path'].startswith('08_Archives')), None)
    budget = re.search(r'Budget initial\s*:\s*([^\n]+)', charter['text'], re.I) if charter else None
    result['as_of'] = memory['as_of']
    result['summary'] = {
        **result.get('summary', {}),
        'title': 'Dossier de reprise NOVA',
        'status': 'Cible approuvée : ' + (memory['schedule']['current_target'] or 'À confirmer')
                  + (' — conditionnelle aux validations restantes.' if memory['schedule']['conditional'] else '.'),
        'owner': memory['assignments'][-1]['owner'] if memory['assignments'] else 'Non précisé',
        'budget': 'Budget initial documenté : ' + budget[1] + '. Voir Finance pour les changements.' if budget else 'Budget non précisé ; consulter les décisions sourcées dans Finance.',
        'principle': 'Une proposition ou une livraison ne vaut pas acceptation ; les informations initiales sont conservées comme historiques.',
    }
    result['evidence_as_of'] = registers['as_of']
    result['completed_documents'] = [
        {'document_id': proof['document_id'], 'completed_on': ticket['completed_on'],
         'reason': 'Fermeture explicite du ticket ' + ticket['id']}
        for ticket in memory['tickets'] if ticket['status'] == 'completed'
        for proof in ticket['evidence']
    ]
    result['verification_tasks'] = [
        {'id': 'gate-' + gate['id'], 'label': gate['id'], 'priority': 'urgent',
         'title': gate['title'],
         'description': 'Validation ouverte ou en cours : cette condition doit être levée avant la mise en production.',
         'evidence': gate['evidence']}
        for gate in memory['gates']
    ]
    result['verification_tasks'].extend(
        {'id': alert['id'], 'label': {'stale-plan': 'Date du plan', 'status-conflict': 'Statut du projet', 'stale-risk': 'Registre des risques'}.get(alert['id'], alert['title']),
         'priority': 'important', 'title': alert['title'],
         'description': alert['description'], 'evidence': alert['evidence']}
        for alert in memory['alerts'] if alert['id'] != 'pending-gates'
    )
    for section in result.get('sections', []):
        section['historical_facts'] = section.get('historical_facts', section.get('facts', []))
        section['historical_open_items'] = section.get('historical_open_items', section.get('open_items', []))
        section['title'] = SECTION_NAMES.get(section['id'], section.get('title', section['id']))
        topics = SECTION_TOPICS.get(section['id'], set())
        paths = {source['file'] for source in section.get('sources', [])}
        section['registers'] = {}
        for group, items in registers['groups'].items():
            # A risk overview collects all risks. Other categories retain topic
            # assignments; document matches supplement decisions and promises.
            section['registers'][group] = [
                {**item, 'evidence': [proof for proof in item['evidence'] if proof['path'] not in excluded_paths]}
                for item in items
                if (section['id'] == 'risques' and group == 'risques')
                or item['topic'] in topics
                or (group in ('decisions', 'engagements') and
                    any(proof['path'] in paths and proof['path'] not in excluded_paths for proof in item['evidence']))
            ]
        section['alerts'] = [alert for alert in registers['alerts']
                             if section['id'] == 'risques' or
                             any(proof['path'] in paths for proof in alert['evidence'])]
        section['current_statuses'] = [
            {'id': ticket['id'], 'status': ticket['status'], 'date': ticket['last_update'], 'evidence': ticket['evidence']}
            for ticket in memory['tickets'] if ticket['topic'] in topics
        ]
        # Risk ownership is explicit, unlike a ticket's requester field.
        for risk in section['registers']['risques']:
            if risk['owner'] and risk['owner_role'] == 'Propriétaire du risque':
                section['registers']['responsables'].append({
                    **risk, 'id': 'owner-' + risk['id'], 'status': 'assigned',
                    'note': 'Responsabilité explicitement déclarée dans le registre des risques.'})
        section['facts'] = [
            f"{ticket['id']} : { {'completed': 'fermé', 'open': 'ouvert', 'in_review': 'en validation'}.get(ticket['status'], ticket['status'])}."
            for ticket in memory['tickets'] if ticket['topic'] in topics
        ]
        if section['id'] == 'go-live':
            target = memory['schedule']['current_target']
            section['facts'].insert(0, f"La date actuellement approuvée est le {target}." if target else 'La date approuvée reste à confirmer.')
            section['facts'].append(
                'Le lancement reste conditionnel aux validations suivantes : ' + ', '.join(g['id'] for g in memory['gates']) + '.'
                if memory['gates'] else 'Aucune condition ouverte identifiée dans les tickets ; les preuves restent à vérifier avant le lancement.')
        elif section['id'] == 'pilotage' and memory['assignments']:
            assignment = memory['assignments'][-1]
            section['facts'].insert(0, f"Responsable actuel : {assignment['owner']} depuis le {assignment['effective_on']}.")
        if section['id'] not in ('go-live', 'pilotage'):
            section['facts'].extend(
                f"Décision documentée le {item['date'] or 'date inconnue'} : {item['note'] or item['title']}"
                for item in section['registers']['decisions'][-3:])
        if section['id'] == 'risques':
            section['facts'].extend(alert['description'] for alert in memory['alerts'])
        section['open_items'] = [
            {'label': f"{gate['id']} : {gate['title']}",
             'owner': (gate['owner'] or 'Non précisé') + ' (référent cité dans le ticket)',
             'due': 'Avant la mise en production', 'evidence': gate['evidence']}
            for gate in memory['gates'] if gate['topic'] in topics or section['id'] in ('go-live', 'risques')
        ]
        section['open_items'].extend(
            {'label': item['title'], 'owner': item['owner'] or 'Non précisé',
             'due': item['due'] or 'À confirmer', 'evidence': item['evidence']}
            for item in commitments
            if item['topic'] in topics or
            (section['id'] == 'go-live' and item['topic'] in ('security', 'accessibility', 'operations', 'schedule')))
    return result
