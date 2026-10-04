"""Exercise imports without touching the demo corpus or processed data."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from openpyxl import Workbook
from . import ingest, intelligence, main, rag, updates
from .dossier import SECTION_TOPICS


class UpdateImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.corpus, self.processed = root / 'corpus', root / 'processed'
        self.corpus.mkdir()
        self.processed.mkdir()
        for module, name, value in (
            (ingest, 'DEFAULT_CORPUS', self.corpus), (ingest, 'PROCESSED', self.processed),
            (main, 'DEFAULT_CORPUS', self.corpus), (main, 'PROCESSED', self.processed),
            (intelligence, 'PROCESSED', self.processed), (rag, 'PROCESSED', self.processed),
            (updates, 'STORE', root / 'updates'),
        ):
            context = patch.object(module, name, value)
            context.start()
            self.addCleanup(context.stop)
        (self.corpus / 'decision.txt').write_text('Date : 10 septembre 2026\nLa date cible de mise en production est déplacée au 22 octobre 2026. Donc approuvé.')
        (self.corpus / 'SEC-210.txt').write_text('TICKET SEC-210\nTitre : Sécurité\nCréé : 12 septembre 2026\nDemandeur : Sophie Lambert\nStatut : En validation\nDescription : Validation sécurité requise.')
        (self.processed / 'dossier.json').write_text(json.dumps({'sections': [{'id': key} for key in SECTION_TOPICS]}))
        ingest.ingest_corpus()
        self.client = TestClient(main.app)
        self.addCleanup(self.client.close)

    def test_http_import_reaches_all_shared_views_and_preserves_original(self):
        content = b'Date : 4 octobre 2026\nAuteur : Sophie Lambert\nSEC-210 est ferme apres re-test.\nProposition : mise en production le 5 novembre 2026.'
        response = self.client.post('/api/updates/preview', files={'file': ('update.txt', content, 'text/plain')})
        self.assertEqual(response.status_code, 200, response.text)
        preview = response.json()
        self.assertEqual(len(updates._current()[0]), 2)
        response = self.client.post(f"/api/updates/{preview['id']}/integrate", json={})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        identifier = result['analysis']['document']['id']
        self.assertEqual(result['analysis']['current_target'], '2026-10-22')
        self.assertNotIn('SEC-210', result['analysis']['remaining_gates'])
        self.assertTrue(result['analysis']['affected_information'])
        self.assertEqual(self.client.get(f'/api/documents/{identifier}/original').content, content)
        for endpoint in ('/api/timeline', '/api/project-memory', '/api/dossier', '/api/dashboard'):
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIn(identifier, response.text, endpoint)
        self.assertIn(identifier, self.client.post('/api/search', json={'query': 're-test'}).text)
        self.assertEqual(len(self.client.get('/api/updates').json()['imports']), 1)
        self.assertEqual(updates.integrate_upload(preview['id']), result)
        self.assertEqual(self.client.post('/api/updates/preview', files={'file': ('copy.txt', content)}).status_code, 400)

    def test_supplier_does_not_close_reviewer_gate(self):
        preview = updates.preview_upload('supplier.eml', b'From: Julien Moreau <julien@example.test>\nDate: Sun, 4 Oct 2026 10:00:00 -0400\nSubject: Fix\n\nSEC-210 est ferme. Correctif deploye.')
        result = updates.integrate_upload(preview['id'])
        self.assertIn('SEC-210', result['analysis']['remaining_gates'])

    def test_undated_transcription_survives_reingestion_with_stable_id(self):
        with patch.dict(ingest.READERS, {'.png': lambda path: ''}):
            preview = updates.preview_upload('capture.png', b'image fixture')
        self.assertEqual(self.client.post(f"/api/updates/{preview['id']}/integrate", json={}).status_code, 400)
        result = updates.integrate_upload(preview['id'], 'Runbook : ajouter la validation après déploiement.')
        identifier = result['analysis']['document']['id']
        self.assertTrue(any(e['date_kind'] == 'received' for e in result['analysis']['events']))
        ingest.ingest_corpus()
        doc = next(d for d in updates._current()[0] if d['id'] == identifier)
        self.assertIn('validation après', doc['text'])
        self.assertTrue(doc['text_reviewed'])

    def test_generic_spreadsheet_is_integrated(self):
        workbook = Workbook()
        workbook.active.append(['Date', '2026-10-04'])
        workbook.active.append(['Information', 'Runbook : exercice de reprise requis'])
        stream = io.BytesIO()
        workbook.save(stream)
        preview = updates.preview_upload('nouvelle-information.xlsx', stream.getvalue())
        result = updates.integrate_upload(preview['id'])
        self.assertTrue(result['analysis']['events'])
        self.assertTrue(all(e['date'] for e in result['analysis']['events']))

    def test_approved_november_date_changes_live_calendar(self):
        preview = updates.preview_upload('decision-novembre.txt', 'Date : 4 octobre 2026\nLa date cible de mise en production est déplacée au 5 novembre 2026. Donc approuvé.'.encode())
        result = updates.integrate_upload(preview['id'])
        self.assertEqual(result['analysis']['previous_target'], '2026-10-22')
        self.assertEqual(result['analysis']['current_target'], '2026-11-05')
        self.assertTrue(any(e['date'] == '2026-11-05' and e['date_kind'] == 'planned' for e in result['analysis']['events']))

    def test_text_pdf_extraction_and_original(self):
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        writer = PdfWriter()
        page = writer.add_blank_page(width=600, height=800)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(b'BT /F1 12 Tf 40 700 Td (Date : 4 octobre 2026) Tj 0 -20 Td (Runbook : exercice requis.) Tj ET')
        page[NameObject('/Contents')] = writer._add_object(stream)
        output = io.BytesIO()
        writer.write(output)
        preview = updates.preview_upload('information.pdf', output.getvalue())
        self.assertIn('exercice requis', preview['extracted_text'])
        result = updates.integrate_upload(preview['id'])
        identifier = result['analysis']['document']['id']
        self.assertEqual(self.client.get(f'/api/documents/{identifier}/original').content, output.getvalue())

    def test_failed_publish_restores_previous_state(self):
        preview = updates.preview_upload('rollback.txt', b'Date : 4 octobre 2026\nNouvelle information de demonstration.')
        previous = {p.name: p.read_bytes() for p in self.processed.iterdir()}
        with patch.object(ingest, 'publish_corpus', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                updates.integrate_upload(preview['id'])
        self.assertEqual(previous, {p.name: p.read_bytes() for p in self.processed.iterdir()})
        self.assertFalse((self.corpus / '09_Mises_a_jour' / preview['id']).exists())
        self.assertEqual(updates.history(), [])

    def test_rejects_unsupported_empty_and_invalid_dates(self):
        for name, content in [('bad.exe', b'abc'), ('empty.txt', b'')]:
            with self.assertRaises(ValueError):
                updates.preview_upload(name, content)
        preview = updates.preview_upload('../../safe.txt', b'Nouvelle information')
        self.assertEqual(preview['filename'], 'safe.txt')
        with self.assertRaises(ValueError):
            updates.analyze_upload(preview['id'], document_date='2026-02-31')
