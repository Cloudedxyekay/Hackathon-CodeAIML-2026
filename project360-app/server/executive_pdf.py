"""Read-only executive PDF: major governance decisions and source references."""
import json
import re
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from .intelligence import PROCESSED, build_project_memory, evidence, fold, source_date, dates_in, roster_from, resolve_owner
from .synthesis import build_synthesis, current_commitments

router = APIRouter(tags=['executive-brief'])


def schedule_context(doc, target, roster):
    """Quote the decision's own source; never reuse another report's rationale."""
    on = source_date(doc)
    year = int(on[:4]) if on else None
    sender = re.search(r'^From:\s*([^<\n]+)', doc['text'], re.M)
    author = resolve_owner(sender[1], {**roster, **{fold(v): v for v in roster.values()}}) if sender else None
    decision_line = None
    context = []
    reasons = []
    for line in doc['text'].splitlines():
        if line.lstrip().startswith('>') or re.match(r'^(Subject|From|To|Date):', line):
            continue
        speaker = re.match(r'^\d{2}:\d{2}(?:\s*[-–])?\s+([^:]+):\s*(.+)', line)
        content = speaker[2] if speaker else line.strip()
        value = fold(content)
        if target in [item['date'] for item in dates_in(content, year)] and re.search(r'decision|approuv|date officielle|date cible.*deplac', value):
            if decision_line is None:
                decision_line = line
                if speaker:
                    author = resolve_owner(speaker[1], roster)
        if re.search(r'parce que|en raison|a cause|afin de|motif|raison du report', value):
            reasons.append(content)
        elif re.search(r'stabilis|reprise des tests|re-test|validation|risque|condition', value):
            if content:
                context.append(content)
    explanation = ('Motif cité dans la source : « ' + ' '.join(reasons)[:900] + ' ».' if reasons
                   else 'Motif explicite non précisé dans cette source.')
    if context:
        explanation += ' Contexte cité dans la même source : « ' + ' '.join(context[:3])[:900] + ' ».'
    return author, explanation, decision_line


def build_brief(documents, memory=None):
    memory = memory if memory is not None else build_project_memory(documents)
    documents = [d for d in documents if not d['path'].startswith('08_Archives')]
    decisions, tasks = [], []

    def find(fragment):
        return next((d for d in documents if fragment in d['path']), None)

    def proof(doc, terms):
        lines = [(number, line) for number, line in enumerate(doc['text'].splitlines(), 1)
                 if any(term in fold(line) for term in terms)]
        if not lines:
            return evidence(doc, doc['text'], 'Document complet')
        return evidence(doc, '\n'.join(line for _, line in lines),
                        'Lignes ' + ', '.join(str(number) for number, _ in lines))

    def add(title, text, doc, who, terms, extra=None, on=None):
        if doc:
            decisions.append({'title': title, 'text': text, 'date': on or source_date(doc),
                              'who': who, 'evidence': [proof(doc, terms)] + (extra or [])})

    charter = find('Charte_Projet')
    if charter:
        amount = re.search(r'Budget initial\s*:\s*([^\n]+)', charter['text'], re.I)
        target = re.search(r'Date cible de mise en production\s*:\s*([^\n]+)', charter['text'], re.I)
        add('Le cadre initial du projet',
            'La phase 1 couvre un portail de demandes : SSO, suivi, pièces jointes, workflow, tableau de suivi et rapports standards. '
            + ('Budget initial : ' + amount[1] + '. ' if amount else '')
            + ('Cible initiale : ' + target[1] + '. Cette cible est historique ; les décisions ultérieures prévalent.' if target else ''),
            charter, 'Élodie Caron, chargée de projet désignée dans la charte.' if 'Élodie Caron' in charter['text'] else 'Personne non précisée dans la source.',
            ['charge', 'budget initial', 'date cible', 'authentification', 'creation', 'pieces', 'workflow', 'tableau', 'rapports'])
    adr = find('ADR-007')
    architecture = find('M02_Transcript')
    if adr and 'canada central' in fold(adr['text']):
        add('Les données de production restent au Canada',
            'Canada Central remplace la région américaine prévue dans l’architecture initiale. L’architecture v1 devient obsolète sur ce point.',
            adr, 'Élodie formule le choix, Marc et Sophie donnent leur accord dans l’atelier.' if architecture else 'Décision acceptée dans ADR-007 ; auteur non nommé.',
            ['canada central', 'v1', 'statut'], [proof(architecture, ['09:10', '09:12'])] if architecture else None)
    cr = find('CR-01_Rapports')
    if cr and 'approuve' in fold(cr['text']):
        amount = re.search(r'([0-9][0-9 \u00a0]*)\s*\$', cr['text'])
        add('Les rapports avancés sont autorisés',
            'CR-01 autorise l’ajout de rapports avancés et d’un export de synthèse.'
            + (' Montant de ce changement : ' + amount[1].strip() + ' $.' if amount else '')
            + ' Ce changement est distinct de CR-04, qui n’est pas approuvé.',
            cr, 'Comité de projet, autorité explicitement indiquée dans CR-01.',
            ['rapports', 'export', 'approuv', 'comite', '$', 'aout'])
    for change in memory['schedule']['changes']:
        if change['target'] == memory['schedule']['changes'][0]['target']:
            continue
        source = next((d for d in documents if d['id'] == change['evidence'][0]['document_id']), None)
        source_ids = {proof['document_id'] for item in memory['schedule']['history']
                      if item['date'] == change['date'] and item['target'] == change['target']
                      and item['status'] in ('approved', 'conditional') for proof in item['evidence']}
        transcript = next((doc for doc in documents if doc['id'] in source_ids and 'Transcript' in doc['path']), None)
        if transcript:
            source = transcript
        if source:
            author, explanation, _ = schedule_context(source, change['target'], roster_from(documents))
            add('Le lancement est reporté',
                'La date approuvée de mise en production passe au ' + change['target'] + '. ' + explanation,
                source, author + ' (auteur ou intervenant ayant annoncé la décision).' if author else 'Auteur de la décision non précisé dans la source.',
                ['from:', 'decision', 'approuv', 'date officielle', 'deplace', 'stabilis', 'reprise des tests', 'risque', 'validation', 're-test', 'parce que', 'en raison', 'afin de'], on=change['date'])
    for assignment in memory['assignments'][1:]:
        doc = next((d for d in documents if d['id'] == assignment['evidence'][0]['document_id']), None)
        note = find('Note_transition')
        if note and assignment['effective_on'] == source_date(note):
            doc = note
        add('La responsabilité du projet change',
            assignment['owner'] + ' reprend la charge du projet. Les décisions et suivis futurs doivent être dirigés vers cette personne.',
            doc, 'Élodie annonce la transition ; Nicolas Perron reprend le rôle.' if doc and 'Note_transition' in doc['path'] else 'Attribution explicite dans la source.',
            ['reprend', 'prend officiellement', 'charge', 'elodie'], on=assignment['effective_on'])
    scope = find('Decision_Portee_Phase2')
    if scope and 'phase 2' in fold(scope['text']):
        email = find('E10_Fonction_mobile')
        add('Le mobile avancé passe à la phase 2',
            'CR-04 est reporté : les optimisations mobiles avancées ne font pas partie de la phase 1 approuvée. La compatibilité mobile de base reste requise. Aucune dépense CR-04 ne peut être engagée sans nouvelle approbation.',
            scope, 'Décision de portée du 24 septembre ; Nicolas confirme la position dans le courriel associé.' if email and 'Nicolas' in email['text'] else 'Décision consignée ; auteur non précisé.',
            ['optimisations', 'phase 1', 'depense'], [proof(email, ['from:', 'approuve', 'phase 2', 'depense'])] if email else None)
    committee = find('M06_Transcript')
    if committee and memory['gates']:
        add('Le comité définit les conditions de lancement',
            'Le comité a exigé l’acceptation sécurité de SEC-210, la fermeture du blocage clavier ACC-303 et un runbook approuvé avec rollback. Les conditions encore ouvertes figurent dans les actions actuelles. Un correctif livré ne vaut pas acceptation.',
            committee, 'Nicolas énonce les conditions ; Sophie, Mélissa et Olivier les confirment.',
            ['10:02', '10:05', '10:07', '10:09', '10:10', '10:15'])
    for gate in memory['gates']:
        action = {'security': 'Exécuter le re-test et obtenir l’acceptation sécurité.',
                  'accessibility': 'Corriger la navigation au clavier, puis faire confirmer la fermeture.',
                  'operations': 'Finaliser le runbook, y inclure le rollback et obtenir l’accord exploitation.'}.get(gate['topic'], gate['title'])
        tasks.append({'title': gate['id'] + ' — ' + action, 'who': (gate['owner'] or 'Non précisé') + ' (demandeur / référent cité dans le ticket)',
                      'due': 'Avant la mise en production ; date précise à confirmer.', 'priority': 'Bloquant', 'evidence': gate['evidence']})
    finance = find('E07_Facture_003')
    if finance:
        tasks.append({'title': 'Vérifier INV-003 et l’autorisation de la ligne CR-04 avant paiement.',
                      'who': 'Personne chargée de la vérification à confirmer ; voir le courriel finance.',
                      'due': 'Avant libération de la facture ; date précise non documentée.', 'priority': 'Important',
                      'evidence': [proof(finance, ['from:', '18', 'cr-04', 'approb', 'facture'])]})
    for alert in memory['alerts']:
        if alert['id'] in ('stale-plan', 'status-conflict', 'stale-risk'):
            tasks.append({'title': alert['title'], 'who': 'Responsable de mise à jour à confirmer.',
                          'due': 'À confirmer.', 'priority': 'Important', 'evidence': alert['evidence']})
    synthesis = build_synthesis(documents, memory)
    for commitment in sorted(current_commitments(synthesis, memory), key=lambda item: item['date'] or '', reverse=True):
        tasks.append({'title': commitment['title'],
                      'who': (commitment['owner'] or 'Non précisé') + ' (' + (commitment['owner_role'] or 'responsable non attribué') + ')',
                      'due': commitment['due'] or 'À confirmer ; consulter l’extrait pour les échéances relatives.',
                      'priority': 'Engagement documenté — réalisation à confirmer', 'evidence': commitment['evidence']})
    resolved = [t for t in memory['tickets'] if t['status'] == 'completed' and t['completed_on']]
    return {'as_of': memory['as_of'], 'target': memory['schedule']['current_target'],
            'conditional': memory['schedule']['conditional'],
            'owner': memory['assignments'][-1]['owner'] if memory['assignments'] else 'Non précisé',
            'decisions': sorted(decisions, key=lambda d: d['date'] or '9999'), 'tasks': tasks,
            'resolved': sorted(resolved, key=lambda t: t['completed_on']), 'documents': memory['stats']['documents']}


def build_executive_summary(documents, memory):
    """Keep the existing JSON briefing on the same current model as the PDF."""
    brief = build_brief(documents, memory)
    target = brief['target'] or 'À confirmer'
    condition = ' — conditionnelle aux validations restantes' if brief['conditional'] else ''
    finance = [item['text'] for item in brief['decisions'] if item['title'] in ('Le cadre initial du projet', 'Les rapports avancés sont autorisés')]
    return {'title': 'Brief executif NOVA', 'as_of': brief['as_of'],
            'status': 'Cible approuvée : ' + target + condition + '.',
            'top_points': ['Responsable actuel : ' + brief['owner'] + '.',
                           'Cible approuvée : ' + target + condition + '.',
                           ' '.join(finance) if finance else 'Portée et budget non précisés dans les sources disponibles.'],
            'risks': [f"{gate['id']} : {gate['title']} — validation restante." for gate in memory['gates']]
                     + [alert['description'] for alert in memory['alerts'] if alert['id'] != 'pending-gates'],
            'open_actions': brief['tasks'], 'decisions': brief['decisions'],
            'timeline_events': len(memory['events']),
            'evidence_ready_answers': 0}


def render_pdf(brief):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether

    font, bold = 'Helvetica', 'Helvetica-Bold'
    regular_path, bold_path = Path('C:/Windows/Fonts/arial.ttf'), Path('C:/Windows/Fonts/arialbd.ttf')
    if regular_path.exists() and bold_path.exists():
        if 'BriefArial' not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont('BriefArial', str(regular_path)))
            pdfmetrics.registerFont(TTFont('BriefArialBold', str(bold_path)))
        font, bold = 'BriefArial', 'BriefArialBold'
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BriefBody', fontName=font, fontSize=9.5, leading=13, spaceAfter=6))
    styles.add(ParagraphStyle(name='BriefSmall', fontName=font, fontSize=8, leading=12, textColor=colors.HexColor('#64748b'), spaceAfter=8))
    styles.add(ParagraphStyle(name='BriefTitle', fontName=bold, fontSize=26, leading=32, textColor=colors.HexColor('#172554'), spaceAfter=16))
    styles.add(ParagraphStyle(name='BriefHeading', fontName=bold, fontSize=17, leading=23, textColor=colors.HexColor('#1d4ed8'), spaceAfter=14))
    styles.add(ParagraphStyle(name='BriefSub', fontName=bold, fontSize=11, leading=15, spaceBefore=8, spaceAfter=5, keepWithNext=True))
    styles.add(ParagraphStyle(name='BriefExcerpt', fontName=font, fontSize=8.5, leading=12, spaceAfter=5))
    def para(text, style='BriefBody'):
        return Paragraph(escape(str(text)).replace('\n', '<br/>'), styles[style])
    references = {}
    def cite(proofs):
        ids = []
        for proof in proofs:
            key = proof['document_id']
            if key not in references:
                references[key] = (len(references) + 1, dict(proof))
            else:
                saved = references[key][1]
                if proof['locator'] not in saved['locator']:
                    saved['locator'] += ' ; ' + proof['locator']
                if proof['excerpt'] not in saved['excerpt']:
                    saved['excerpt'] += '\n' + proof['excerpt']
            ids.append('[' + str(references[key][0]) + ']')
        return ' '.join(ids)
    story = [para('NOVA', 'BriefTitle'), para('Briefing exécutif', 'BriefHeading'),
             para('État des informations au ' + (brief['as_of'] or 'date non précisée'), 'BriefSmall'),
             para('Le projet en une minute', 'BriefSub'),
             para('Responsable actuel : ' + brief['owner']),
             para('Cible approuvée : ' + (brief['target'] or 'Non précisée') + (' — sous réserve des validations restantes.' if brief['conditional'] else '.')),
             para(f"{len(brief['decisions'])} grandes décisions retenues · {len(brief['resolved'])} tickets avec clôture confirmée · {len(brief['tasks'])} points de suivi."),
             para('Ce rapport distingue les décisions officielles, les réalisations confirmées et les actions encore ouvertes. Il ne déduit pas un pourcentage global d’avancement.', 'BriefSmall'),
             para('Ce qui s’est passé', 'BriefSub')]
    for decision in brief['decisions']:
        story.append(para((decision['date'] or 'Date inconnue') + ' — ' + decision['title'] + ' ' + cite(decision['evidence'])))
    if brief['resolved']:
        story.append(para('Avancées confirmées', 'BriefSub'))
        for ticket in brief['resolved']:
            story.append(para(ticket['completed_on'] + ' — ' + ticket['id'] + ' : ' + ticket['title'] + '. Clôture confirmée. ' + cite(ticket['evidence'])))
    story += [PageBreak(), para('Les grandes décisions', 'BriefHeading'),
              para('Seuls les changements de cadre, de budget, de localisation, de calendrier, de responsabilité, de portée ou de conditions de lancement sont retenus.', 'BriefSmall')]
    for decision in brief['decisions']:
        story.append(KeepTogether([para((decision['date'] or 'Date non précisée') + ' · ' + decision['title'], 'BriefSub'),
                  para(decision['text']), para('Qui l’a dit ou consigné : ' + decision['who']),
                  para('Preuves : ' + cite(decision['evidence']), 'BriefSmall')]))
    story += [PageBreak(), para('Ce qui reste à faire', 'BriefHeading'),
              para('Les points bloquants sont à lever avant le lancement. Les échéances et les responsabilités non établies restent à confirmer.', 'BriefSmall')]
    for task in brief['tasks']:
        story.append(KeepTogether([para(task['priority'] + ' · ' + task['title'], 'BriefSub'), para('Personne concernée : ' + task['who']),
                  para('Échéance : ' + task['due']), para('Preuves : ' + cite(task['evidence']), 'BriefSmall')]))
    if not brief['tasks']:
        story.append(para('Aucune action ouverte identifiée par les règles de ce briefing ; cela ne constitue pas une autorisation de lancement.'))
    story += [PageBreak(), para('Les preuves à consulter', 'BriefHeading'),
              para('Les références renvoient aux documents du corpus. Les extraits ci-dessous sont raccourcis pour faciliter la lecture ; les fichiers originaux restent accessibles dans le Dossier.', 'BriefSmall')]
    for number, proof in references.values():
        excerpt = re.sub(r'\s+', ' ', proof['excerpt']).strip()
        if len(excerpt) > 360:
            excerpt = excerpt[:360].rsplit(' ', 1)[0] + ' […]'
        story.append(KeepTogether([para(f"[{number}] {Path(proof['path']).name}", 'BriefSub'),
                  para('Publication : ' + (proof['published_on'] or 'Non précisée') + ' · ' + proof['locator'], 'BriefSmall'),
                  para(excerpt, 'BriefExcerpt'), para('Fichier : ' + proof['path'], 'BriefSmall')]))
    buffer = BytesIO()
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#dbe3ed'))
        canvas.line(42, 38, A4[0] - 42, 38)
        canvas.setFont(font, 8)
        canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawString(42, 24, 'NOVA · Briefing exécutif · État documentaire : ' + (brief['as_of'] or 'inconnu'))
        canvas.drawRightString(A4[0] - 42, 24, 'Page ' + str(doc.page))
        canvas.restoreState()
    SimpleDocTemplate(buffer, pagesize=A4, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=56,
                      title='NOVA — Briefing exécutif', author='NOVA Project Memory').build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()


@router.get('/api/brief/pdf')
def executive_pdf():
    path = PROCESSED / 'documents.json'
    if not path.exists():
        raise HTTPException(409, 'Les documents doivent être analysés avant de générer le briefing.')
    docs = json.loads(path.read_text(encoding='utf-8'))
    if not docs:
        raise HTTPException(409, 'Aucun document disponible pour le briefing.')
    brief = build_brief(docs)
    return Response(render_pdf(brief), media_type='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename="NOVA-briefing-{brief["as_of"] or "sans-date"}.pdf"', 'Cache-Control': 'no-store'})
