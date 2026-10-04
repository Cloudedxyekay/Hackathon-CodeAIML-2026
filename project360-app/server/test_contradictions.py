import unittest
from unittest.mock import patch
from . import rag
from .contradictions import comparisons, is_contradiction_question


def doc(path, text):
    return {'id': path, 'path': path, 'extension': '.' + path.rsplit('.', 1)[-1], 'text': text}


class ContradictionTests(unittest.TestCase):
    def setUp(self):
        self.docs = [
            doc('README.txt', 'Les contradictions font partie du défi.'),
            doc('Plan_12sept.xlsx', '[sheet Plan]\nID | Activité | Statut | Responsable | Début planifié | Fin planifiée | Note\nP-06 | Mise en production | À venir | Nicolas | 2026-10-15 | 2026-10-15 | Cible'),
            doc('decision.txt', 'Date : 27 septembre 2026\nLa cible approuvée de mise en production demeure le 22 octobre 2026, sous réserve des validations.'),
            doc('Rapport_Statut_21sept.pdf', 'Date : 21 septembre 2026\nSécurité VERT Correctif SEC-210 livré\nAccessibilité VERT Correctifs appliqués'),
            doc('SEC-210.txt', 'TICKET SEC-210\nTitre : Audit\nCréé : 12 septembre 2026\nDemandeur : Sophie Lambert\nStatut : EN VALIDATION\nCommentaires :\n26 sept - Sophie : Re-test requis.'),
        ]

    def test_intent_and_factual_pairs(self):
        self.assertTrue(is_contradiction_question('Existe-t-il des informations contradictoires?'))
        self.assertTrue(is_contradiction_question('Quelles incohérences vois-tu?'))
        self.assertFalse(is_contradiction_question('Qui dirige le projet?'))
        findings = comparisons(self.docs)
        self.assertEqual({f['id'] for f in findings}, {'stale-plan', 'status-conflict'})
        text = ' '.join(f['label'] for f in findings)
        for expected in ('2026-10-15', '2026-10-22', '2026-09-26', 'en validation', 'plan non actualisé'):
            self.assertIn(expected, text)
        self.assertNotIn('README', text)

    def test_route_bypasses_keyword_search_and_preserves_both_sources(self):
        with patch.object(rag, '_load', return_value=self.docs), patch.object(rag, '_search_candidates') as search, patch.object(rag, '_external_reasoning_answer', return_value=None):
            result = rag.answer_question('Existe-t-il des informations contradictoires?')
        search.assert_not_called()
        self.assertIn('Plan_12sept.xlsx', result['answer'])
        self.assertIn('decision.txt', result['answer'])
        self.assertNotIn('README.txt', str(result['references']))
        self.assertIn('Livraison et acceptation sont distinctes', result['answer'])

    def test_resolved_validations_are_not_reported_open(self):
        self.docs[-1]['text'] = self.docs[-1]['text'].replace('EN VALIDATION', 'Fermé').replace('Re-test requis.', 'Validé. Je ferme.')
        self.assertNotIn('status-conflict', [f['id'] for f in comparisons(self.docs)])

    def test_no_pair_does_not_claim_consistency(self):
        with patch.object(rag, '_load', return_value=self.docs[:1]), patch.object(rag, '_external_reasoning_answer') as model:
            result = rag.answer_question('Informations contradictoires?')
        model.assert_not_called()
        self.assertIn('Cela ne prouve pas', result['answer'])
        self.assertEqual(result['references'], [])

    def test_model_cannot_omit_required_comparisons(self):
        selected = [{'answer_key': 'schedule', 'answer_label': 'Faits sourcés : plan 15, décision 22'}]
        self.assertIsNone(rag._parse_reasoning_json('{"answer":"Les contradictions font partie du défi", "confidence":"high", "uncertainty":""}', selected))
        result = rag._parse_reasoning_json('{"answer":{"schedule":"Actualiser le plan."},"confidence":"medium","uncertainty":""}', selected)
        self.assertIn('plan 15, décision 22', result['answer'])
