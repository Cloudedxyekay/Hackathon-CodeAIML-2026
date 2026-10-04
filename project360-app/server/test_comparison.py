import base64
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from . import comparison as c


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = patch.object(c, 'STORE', Path(self.temp.name))
        self.store.start()
        self.addCleanup(self.store.stop)

    def test_demo_comparison_has_scoped_sources_and_reusable_solutions(self):
        identifier = c.create_demo()['id']
        result = c.compare(c.CompareRequest(projects=['nova', identifier]))
        self.assertEqual(len(result['projects']), 2)
        self.assertTrue(result['projects'][1]['demo'])
        self.assertTrue(all(result['projects'][1]['axes'].values()))
        self.assertTrue(result['knowledge'])
        self.assertTrue(any(s['priority'] == 'urgent' for s in result['suggestions']))
        for item in result['knowledge']:
            self.assertEqual({p['project_id'] for p in item['evidence']}, {'nova', identifier})
        self.assertTrue(any('2026-11-05' in e['text'] for e in result['projects'][1]['axes']['schedule']))

    def test_comparison_does_not_change_nova_files(self):
        snapshot = lambda: {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in c.PROCESSED.glob('*.json')}
        before = snapshot()
        identifier = c.create_demo()['id']
        c.compare(c.CompareRequest(projects=['nova', identifier]))
        self.assertEqual(snapshot(), before)

    def test_import_unknown_data_stays_unknown_and_original_is_exact(self):
        content = b'Notes without explicit dates or approvals.'
        req = c.ImportRequest(name='Test', files=[c.ImportedFile(name='../note.txt', content=base64.b64encode(content).decode())])
        identifier = c.import_project(req)['id']
        project = c.load_project(identifier)
        result = c.summarize(project)
        self.assertIsNone(result['memory']['as_of'])
        self.assertFalse(result['axes']['schedule'])
        original = c.original(identifier, project['documents'][0]['id'])
        self.assertEqual(Path(original.path).read_bytes(), content)
        self.assertTrue(Path(original.path).is_relative_to(Path(self.temp.name)))

    def test_rejects_invalid_project_and_duplicate_selection(self):
        with self.assertRaises(HTTPException):
            c.load_project('../processed')
        with self.assertRaises(HTTPException):
            c.compare(c.CompareRequest(projects=['nova', 'nova']))

    def test_invalid_import_does_not_create_project(self):
        with self.assertRaises(HTTPException):
            c.import_project(c.ImportRequest(name='Bad', files=[c.ImportedFile(name='a.txt', content='%%%')]))
        self.assertFalse(list(Path(self.temp.name).glob('*/project.json')))


if __name__ == '__main__':
    unittest.main()
