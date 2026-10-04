import hashlib
import json
import unittest
from io import BytesIO

from pypdf import PdfReader
from .intelligence import PROCESSED
from .executive_pdf import build_brief, executive_pdf, render_pdf


class ExecutivePdfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = json.loads((PROCESSED / 'documents.json').read_text(encoding='utf-8'))
        cls.brief = build_brief(cls.docs)

    def test_major_decisions_include_governance_but_not_minor_chat(self):
        titles = [d['title'] for d in self.brief['decisions']]
        self.assertIn('Le lancement est reporté', titles)
        self.assertIn('Le mobile avancé passe à la phase 2', titles)
        self.assertIn('Les rapports avancés sont autorisés', titles)
        self.assertLessEqual(len(titles), 8)
        self.assertFalse(any('HDMI' in d['text'] or 'café' in d['text'] for d in self.brief['decisions']))
        self.assertTrue(any('Élodie' in d['who'] for d in self.brief['decisions'] if d['title'] == 'Le lancement est reporté'))

    def test_actions_and_proofs_are_explicit(self):
        text = '\n'.join(t['title'] for t in self.brief['tasks'])
        for ticket in ('SEC-210', 'ACC-303', 'OPS-601'):
            self.assertIn(ticket, text)
        ids = {d['id'] for d in self.docs}
        for item in self.brief['decisions'] + self.brief['tasks']:
            self.assertTrue(item['evidence'])
            for proof in item['evidence']:
                self.assertIn(proof['document_id'], ids)

    def test_valid_pdf_contains_sections_and_does_not_mutate_sources(self):
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in PROCESSED.glob('*.json')}
        response = executive_pdf()
        self.assertTrue(response.body.startswith(b'%PDF'))
        self.assertEqual(response.media_type, 'application/pdf')
        reader = PdfReader(BytesIO(response.body))
        text = '\n'.join(page.extract_text() for page in reader.pages)
        for phrase in ('Ce qui reste à faire', 'Les grandes décisions', 'Les preuves à consulter', 'Nicolas Perron', 'SEC-210', '24 000'):
            self.assertIn(phrase, text)
        self.assertGreaterEqual(len(reader.pages), 4)
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in PROCESSED.glob('*.json')}
        self.assertEqual(before, after)

    def test_empty_corpus_does_not_invent_major_decisions(self):
        brief = build_brief([])
        self.assertFalse(brief['decisions'])
        self.assertFalse(brief['tasks'])
        self.assertIsNone(brief['target'])


if __name__ == '__main__':
    unittest.main()
