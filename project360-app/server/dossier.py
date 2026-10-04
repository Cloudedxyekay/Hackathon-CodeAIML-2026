"""Attach evidence registers to the existing project categories."""
from copy import deepcopy

from .synthesis import build_synthesis


SECTION_TOPICS = {
    'pilotage': {'governance', 'delivery'},
    'go-live': {'schedule', 'operations'},
    'portee': {'scope'},
    'finance': {'finance'},
    'architecture': {'architecture', 'data', 'integration', 'performance'},
    'securite': {'security'},
    'accessibilite': {'accessibility'},
}


def build_dossier(base, documents, memory):
    result = deepcopy(base)
    registers = build_synthesis(documents, memory)
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
        topics = SECTION_TOPICS.get(section['id'], set())
        paths = {source['file'] for source in section.get('sources', [])}
        section['registers'] = {}
        for group, items in registers['groups'].items():
            # A risk overview collects all risks. Other categories retain topic
            # assignments; document matches supplement decisions and promises.
            section['registers'][group] = [
                item for item in items
                if (section['id'] == 'risques' and group == 'risques')
                or item['topic'] in topics
                or (group in ('decisions', 'engagements') and
                    any(proof['path'] in paths for proof in item['evidence']))
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
    return result
