"""Traceable registers derived from local evidence, without provider calls."""
import hashlib
import re

from .intelligence import dates_in, evidence, fold, resolve_owner, roster_from, source_date, topic_of


def build_synthesis(documents, memory):
    relevant = [d for d in documents if not d['path'].startswith('08_Archives')
                and d['path'] not in ('README.txt', 'MANIFEST.csv')
                and not d['text'].startswith('Extraction failed:')]
    roster = roster_from(relevant)
    groups = {key: [] for key in ('decisions', 'responsables', 'engagements', 'echeances', 'risques')}

    def add(group, title, proofs, owner=None, role=None, status='documented', on=None, due=None, note=None, topic=None):
        signature = f'{group}|{title}|{proofs[0]["document_id"]}|{proofs[0]["locator"]}'
        groups[group].append({'id': hashlib.sha256(signature.encode()).hexdigest()[:16],
                             'title': title, 'owner': owner, 'owner_role': role,
                             'status': status, 'date': on, 'due': due,
                             'note': note, 'evidence': proofs, 'topic': topic or topic_of(title)})

    for item in memory['events']:
        if item['type'] == 'decision' and item['date_kind'] == 'observed':
            add('decisions', item['title'], item['evidence'], status=item['status'], on=item['date'],
                note=item['summary'], topic=item['topic'])
        if item['type'] == 'risk' and item['owner_role'] == 'Propriétaire du risque':
            add('risques', item['title'], item['evidence'], item['owner'], item['owner_role'],
                item['status'], item['date'], note='État déclaré dans le registre ; consulter les divergences ci-dessous.')
    for assignment in memory['assignments']:
        add('responsables', 'Charge du projet NOVA', assignment['evidence'], assignment['owner'],
            assignment['role'], 'historical' if assignment['until'] else 'assigned',
            assignment['effective_on'], note=f"Fin du rôle : {assignment['until']}" if assignment['until'] else None)
    for phase in memory['phases']:
        add('responsables', phase['title'], phase['evidence'], phase['owner'], 'Responsable du plan',
            on=phase['evidence'][0]['published_on'], note='Attribution déclarée dans le plan ; les transitions de gouvernance prévalent.')
        add('echeances', phase['title'], phase['evidence'], phase['owner'], 'Responsable du plan',
            'superseded' if phase.get('warning') else 'planned', phase['start'], phase['end'],
            phase.get('warning') or 'Date planifiée ; ne constitue pas une réalisation confirmée.')
    target = next((e for e in memory['events'] if e['title'] == 'Mise en production NOVA'), None)
    if target:
        add('echeances', target['title'], target['evidence'], target['owner'], target['owner_role'],
            'conditional' if memory['schedule']['conditional'] else 'approved', due=target['date'], note=target['summary'])
    for ticket in memory['tickets']:
        if ticket['status']:
            add('risques', f"{ticket['id']} · {ticket['title']}", ticket['evidence'],
                status=ticket['status'], on=ticket['created_on'],
                note=('Ticket explicitement fermé.' if ticket['status'] == 'completed' else 'Ticket ouvert ou en validation.') + ' Le demandeur ne constitue pas un responsable assigné.')

    # Extract only explicit action sections, obligations or first-person promises.
    for doc in relevant:
        if doc['extension'] == '.xlsx':
            continue
        on = source_date(doc)
        year = int(on[:4]) if on else None
        sender = re.search(r'^From:\s*([^<\n]+)', doc['text'], re.M)
        in_actions = False
        for number, line in enumerate(doc['text'].splitlines(), 1):
            stripped = line.strip()
            normalized = fold(stripped)
            if normalized in ('actions', 'actions :', '## consequences'):
                in_actions = True
                continue
            if in_actions and stripped and not stripped.startswith('-'):
                in_actions = False
            owner, role = None, None
            action = re.match(r'^-\s*([^:]+):\s*(.+)', stripped) if in_actions else None
            speaker = re.match(r'^\d{2}:\d{2}(?:\s*[-–])?\s+([^:]+):\s*(.+)', stripped)
            content = speaker[2] if speaker else stripped
            obligation = re.match(r'^(?:-\s*|Action\s*:\s*)?([^.:]+?)\s+(?:doit|devra)\s+(.+)', content)
            promise = re.match(r"^(?:je (?:vais (?:fournir|livrer|finaliser|corriger|publier|confirmer|preparer)|reprends|publie)|on vise|pour le runbook je relance)", fold(content))
            if action:
                owner = resolve_owner(action[1], roster)
                role = 'Responsable explicitement désigné'
            elif obligation:
                subject = obligation[1].strip()
                named = fold(subject) in roster or subject in roster.values() or 'boreal' in fold(subject)
                team = bool(re.match(r"^(?:l['’])?equipe\b", fold(subject)))
                if not (named or team or fold(subject) in ('on', 'nous')):
                    continue
                owner = resolve_owner(subject, roster) if named or team else None
                role = 'Responsable explicitement désigné' if owner else None
            elif promise:
                owner = resolve_owner(speaker[1], roster) if speaker else (sender[1].strip() if sender else None)
                role = 'Auteur de l’engagement' if owner else None
            else:
                continue
            if not stripped or 'cafe' in normalized or 'hdmi' in normalized:
                continue
            dated = dates_in(content, year)
            future = [d['date'] for d in dated if on and d['date'] > on]
            due = future[-1] if future else None
            add('engagements', stripped, [evidence(doc, stripped, f'Ligne {number}')], owner, role,
                'documented', on, due,
                'Engagement documenté ; réalisation non déduite. Les échéances relatives restent dans l’extrait.')
    return {'as_of': memory['as_of'], 'groups': groups, 'alerts': memory['alerts'],
            'schedule': memory['schedule'], 'counts': {key: len(items) for key, items in groups.items()}}


if __name__ == '__main__':
    import json
    from pathlib import Path
    from .intelligence import PROCESSED, get_project_memory

    documents = json.loads((PROCESSED / 'documents.json').read_text(encoding='utf-8'))
    result = build_synthesis(documents, get_project_memory())
    output = Path(__file__).resolve().parents[1] / 'data' / 'reports'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'synthese.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    labels = {'decisions': 'Décisions importantes', 'responsables': 'Responsables',
              'engagements': 'Engagements', 'echeances': 'Échéances', 'risques': 'Risques'}
    lines = ['# Synthèse du projet NOVA', '', f"État documentaire au {result['as_of']}.", '',
             f"Cible approuvée : {result['schedule']['current_target']}. Conditionnelle : {'oui' if result['schedule']['conditional'] else 'non'}.", '',
             'Les engagements restent documentés ; leur réalisation n’est pas déduite. Les dates planifiées ne sont pas des réalisations.', '']
    for key, items in result['groups'].items():
        lines.extend([f'## {labels[key]}', ''])
        for item in items:
            lines.extend([f"### {item['title']}", '', f"Statut : {item['status']}. Responsable : {item['owner'] or 'Non précisé'} ({item['owner_role'] or 'aucun rôle attribué'}).", '',
                          f"Date documentée / début : {item['date'] or 'Non précisée'}. Échéance : {item['due'] or 'Non précisée'}.", ''])
            if item['note']:
                lines.extend([item['note'], ''])
            for proof in item['evidence']:
                lines.extend([f"Source : {proof['path']} — {proof['locator']} ({proof['document_id']}).", '',
                              '\n'.join('> ' + line for line in proof['excerpt'].splitlines()), ''])
    lines.extend(['## Divergences à vérifier', ''])
    for alert in result['alerts']:
        lines.extend([f"### {alert['title']}", '', alert['description'], ''])
        for proof in alert['evidence']:
            lines.extend([f"Source : {proof['path']} — {proof['locator']}.", '',
                          '\n'.join('> ' + line for line in proof['excerpt'].splitlines()), ''])
    (output / 'synthese.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(result['counts'], ensure_ascii=False))
