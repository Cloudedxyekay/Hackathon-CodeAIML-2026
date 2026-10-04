import json
import unittest

from .dossier import build_dossier
from .intelligence import PROCESSED, build_project_memory


class DossierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = json.loads((PROCESSED / 'dossier.json').read_text(encoding='utf-8'))
        cls.documents = json.loads((PROCESSED / 'documents.json').read_text(encoding='utf-8'))
        cls.result = build_dossier(cls.base, cls.documents, build_project_memory(cls.documents))

    def section(self, identifier):
        return next(s for s in self.result['sections'] if s['id'] == identifier)

    def test_preserves_project_categories_without_modifying_base(self):
        self.assertEqual([s['id'] for s in self.result['sections']], [s['id'] for s in self.base['sections']])
        self.assertNotIn('registers', self.base['sections'][0])
        for section in self.result['sections']:
            self.assertEqual(set(section['registers']), {'decisions', 'responsables', 'engagements', 'echeances', 'risques', 'documents'})

    def test_security_risk_and_explicit_owner_are_in_security(self):
        security = self.section('securite')['registers']
        self.assertTrue(any('SEC-210' in r['title'] for r in security['risques']))
        self.assertTrue(any(r['owner'] == 'Sophie Lambert' and r['owner_role'] == 'Propriétaire du risque' for r in security['responsables']))
        self.assertFalse(any('ACC-303' in r['title'] for r in security['risques']))

    def test_go_live_keeps_current_and_superseded_dates(self):
        deadlines = self.section('go-live')['registers']['echeances']
        self.assertTrue(any(d['due'] == '2026-10-22' and d['status'] == 'conditional' for d in deadlines))
        self.assertTrue(any(d['due'] == '2026-10-15' and d['status'] == 'superseded' for d in deadlines))

    def test_every_attached_element_has_resolvable_source(self):
        identifiers = {d['id'] for d in self.documents}
        for section in self.result['sections']:
            for items in section['registers'].values():
                for item in items:
                    self.assertTrue(item['evidence'])
                    for proof in item['evidence']:
                        self.assertIn(proof['document_id'], identifiers)
                        self.assertTrue(proof['excerpt'])


if __name__ == '__main__':
    unittest.main()
