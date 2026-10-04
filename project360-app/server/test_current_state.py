"""Regressions for imported prose and current/historical summary consistency."""
import copy
import json
import unittest
from io import BytesIO
from pypdf import PdfReader

from .intelligence import PROCESSED, build_project_memory, fold
from .synthesis import build_synthesis
from .dossier import build_dossier
from .executive_pdf import build_brief, build_executive_summary, render_pdf

EMAIL_TEXT = '''Subject: NOVA - Report du lancement et suivi SEC-210
From: Nicolas Perron <nicolas.perron@example.test>
Date: Mon, 05 Oct 2026 09:30:00 -0400

Decision du 5 octobre 2026 : la date cible de mise en production est deplacee du 22 octobre au 29 octobre 2026. Cette nouvelle date est approuvee. Donc approuve : le 29 octobre devient la date officielle de lancement de NOVA.

Je confirme cette decision en tant que responsable du projet. Je mettrai a jour le plan de lancement et les communications avant le 7 octobre 2026 a 16 h.
Concernant le ticket SEC-210 : la validation de securite reste ouverte. Sophie Lambert doit effectuer le re-test de la journalisation administrateur avant le 12 octobre 2026 a 15 h et transmettre son rapport par courriel. Ce message ne ferme pas le ticket et ne constitue pas une acceptation de securite.
Melissa Gagnon doit refaire les tests au clavier sur les modales avant le 13 octobre 2026 a 16 h et deposer le rapport dans Microsoft Teams. Aucune validation d'accessibilite n'est declaree terminee dans ce message.
Risque : si les traces administrateur sont incompletes pendant le re-test de SEC-210, la mise en production reste bloquee. Le report de date ne leve pas cette condition.
'''


class CurrentStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = json.loads((PROCESSED / 'dossier.json').read_text(encoding='utf-8'))
        cls.documents = json.loads((PROCESSED / 'documents.json').read_text(encoding='utf-8'))
        cls.email = {'id': 'doc-regression-update', 'path': '09_Mises_a_jour/regression/update.eml',
                     'extension': '.eml', 'text': EMAIL_TEXT}
        cls.updated = cls.documents + [cls.email]
        cls.memory = build_project_memory(cls.updated)

    def test_email_paragraphs_capture_three_canonical_owners_and_deadlines(self):
        synthesis = build_synthesis(self.updated, self.memory)
        actions = [a for a in synthesis['groups']['engagements'] if a['evidence'][0]['document_id'] == self.email['id']]
        self.assertEqual(len(actions), 3)
        self.assertEqual({fold(a['owner']): a['due'] for a in actions},
                         {'nicolas perron': '2026-10-07', 'sophie lambert': '2026-10-12', 'melissa gagnon': '2026-10-13'})
        for action in actions:
            self.assertIn(action['evidence'][0]['excerpt'], EMAIL_TEXT)
            self.assertNotIn('ne ferme pas', action['title'])

    def test_quoted_old_promises_and_passive_subjects_are_not_new_assignments(self):
        doc = {**self.email, 'text': 'Date : 5 octobre 2026\n> Sophie Lambert doit faire le re-test avant le 12 octobre.\nUne validation technique doit confirmer la migration.\nJe ne mettrai pas à jour le plan.'}
        self.assertFalse(build_synthesis([doc], build_project_memory([doc]))['groups']['engagements'])

    def test_dossier_live_target_actions_and_history_are_separate(self):
        original = copy.deepcopy(self.base)
        dossier = build_dossier(self.base, self.updated, self.memory)
        launch = next(s for s in dossier['sections'] if s['id'] == 'go-live')
        self.assertIn('2026-10-29', dossier['summary']['status'])
        self.assertEqual(dossier['as_of'], '2026-10-05')
        self.assertIn('2026-10-29', ' '.join(launch['facts']))
        self.assertNotIn('22 octobre', ' '.join(launch['facts']))
        self.assertEqual(launch['historical_facts'], next(s for s in self.base['sections'] if s['id'] == 'go-live')['facts'])
        self.assertTrue({'2026-10-07', '2026-10-12', '2026-10-13'}.issubset({a['due'] for a in launch['open_items']}))
        self.assertEqual(self.base, original)
        self.assertEqual(sorted(g['id'] for g in self.memory['gates']), ['ACC-303', 'OPS-601', 'SEC-210'])

    def test_json_brief_and_pdf_share_target_owner_and_imported_actions(self):
        summary = build_executive_summary(self.updated, self.memory)
        pdf_brief = build_brief(self.updated, self.memory)
        self.assertIn('2026-10-29', summary['status'])
        self.assertEqual(summary['as_of'], pdf_brief['as_of'])
        self.assertIn('Nicolas Perron', ' '.join(summary['top_points']))
        self.assertTrue({'2026-10-07', '2026-10-12', '2026-10-13'}.issubset({a['due'] for a in summary['open_actions']}))
        text = '\n'.join(p.extract_text() for p in PdfReader(BytesIO(render_pdf(pdf_brief))).pages)
        for phrase in ('2026-10-29', '2026-10-07', '2026-10-12', '2026-10-13', 'Nicolas Perron'):
            self.assertIn(phrase, text)

    def test_new_postponement_does_not_borrow_old_rationale(self):
        brief = build_brief(self.updated, self.memory)
        decision = next(d for d in brief['decisions'] if d['title'] == 'Le lancement est reporté' and d['date'] == '2026-10-05')
        self.assertIn('Nicolas Perron', decision['who'])
        self.assertNotIn('connecteur', decision['text'].lower())
        self.assertIn('re-test', decision['text'])
        self.assertTrue(all(p['document_id'] == self.email['id'] for p in decision['evidence']))

    def test_missing_rationale_stays_unknown_and_explicit_new_reason_is_quoted(self):
        minimal = {**self.email, 'text': 'From: Nicolas Perron <nicolas@example.test>\nDate: Mon, 05 Oct 2026 09:30:00 -0400\nDecision : la date cible de mise en production est deplacee au 29 octobre 2026. Donc approuve.'}
        brief = build_brief(self.documents + [minimal])
        decision = next(d for d in brief['decisions'] if d['date'] == '2026-10-05')
        self.assertIn('Motif explicite non précisé', decision['text'])
        self.assertNotIn('Contexte cité', decision['text'])
        changed = {**minimal, 'text': minimal['text'] + '\nLe report est décidé en raison de la validation de sécurité incomplète.'}
        decision = next(d for d in build_brief(self.documents + [changed])['decisions'] if d['date'] == '2026-10-05')
        self.assertIn('en raison de la validation de sécurité incomplète', decision['text'])

    def test_no_sources_do_not_reuse_legacy_baseline(self):
        summary = build_executive_summary([], build_project_memory([]))
        self.assertIn('À confirmer', summary['status'])
        self.assertFalse(summary['open_actions'])


if __name__ == '__main__':
    unittest.main()
