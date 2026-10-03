import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from . import ai_extraction as ai
from .intelligence import build_project_memory


class AIExtractionTests(unittest.TestCase):
    def setUp(self):
        self.memory = build_project_memory([{"id": "doc-test", "path": "02_Reunions/decision.txt", "extension": ".txt",
                                             "text": "Date : 10 septembre 2026\nParticipants : Nicolas Perron\nDécision : cible du 22 octobre 2026 approuvée, sous réserve des validations."}])
        self.event = self.memory["events"][0]
        self.annotation = {"event_id": self.event["id"], "title": "Cible approuvée sous conditions",
                           "summary": "Le comité fixe la cible au 22 octobre, sous réserve des validations.",
                           "dates": ["2026-09-10", "2026-10-22"], "owners": ["Nicolas Perron"],
                           "decision": "22 octobre, conditionnel aux validations.",
                           "excerpt": "cible du 22 octobre 2026 approuvée, sous réserve des validations."}

    def test_exact_evidence_and_entities_are_required(self):
        accepted, rejected = ai.validate_annotations(self.memory, ai.AnnotationResult(annotations=[self.annotation]))
        self.assertEqual(len(accepted), 1)
        self.assertEqual(rejected, 0)
        for field, invented in (("excerpt", "Une citation qui n’est pas dans la source."),
                                ("dates", ["2026-10-29"]), ("owners", ["Une Personne Inventée"]),
                                ("event_id", "evt-does-not-exist")):
            with self.subTest(field=field):
                accepted, rejected = ai.validate_annotations(self.memory, ai.AnnotationResult(annotations=[{**self.annotation, field: invented}]))
                self.assertEqual(accepted, [])
                self.assertEqual(rejected, 1)

    def test_missing_key_never_calls_provider(self):
        with patch.dict("os.environ", {}, clear=True), patch.object(ai, "urlopen") as provider:
            with self.assertRaises(ai.EnrichmentError):
                ai.enrich(self.memory)
            provider.assert_not_called()

    def test_unconditional_approval_cannot_replace_condition(self):
        annotation = {**self.annotation, "summary": "Le passage en production est approuvé.", "decision": "Approuvé."}
        accepted, rejected = ai.validate_annotations(self.memory, ai.AnnotationResult(annotations=[annotation]))
        self.assertEqual(accepted, [])
        self.assertEqual(rejected, 1)

    def test_success_is_cached_without_overwriting_authority(self):
        canonical = copy.deepcopy(self.memory)
        body = {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps({"annotations": [self.annotation]})}]}]}
        requests = []

        def transport(request, timeout):
            requests.append(json.loads(request.data))
            self.assertEqual(timeout, 120)
            return io.BytesIO(json.dumps(body).encode())

        with tempfile.TemporaryDirectory() as folder, patch.object(ai, "PROCESSED", Path(folder)), patch.dict("os.environ", {"OPENAI_API_KEY": "test-only-no-network"}):
            result = ai.enrich(self.memory, transport=transport)
            self.assertEqual(result["accepted"], 1)
            self.assertEqual(result["memory"]["schedule"], canonical["schedule"])
            self.assertEqual(result["memory"]["events"][0]["status"], canonical["events"][0]["status"])
            self.assertEqual(result["memory"]["events"][0]["date"], canonical["events"][0]["date"])
            self.assertEqual(requests[0]["store"], False)
            self.assertTrue(requests[0]["text"]["format"]["strict"])
            cached = ai.attach_enrichment(copy.deepcopy(canonical))
            self.assertEqual(cached["ai"]["enriched_events"], 1)
            canonical["events"][0]["evidence"][0]["excerpt"] += " Nouvelle information."
            refreshed = ai.attach_enrichment(canonical)
            self.assertEqual(refreshed["ai"]["enriched_events"], 0)
            self.assertNotIn("ai_annotation", refreshed["events"][0])

    def test_provider_failure_is_sanitized_and_retains_existing_data(self):
        before = copy.deepcopy(self.memory)
        def transport(request, timeout):
            raise HTTPError(request.full_url, 401, "test-secret-value", {}, io.BytesIO(b'test-secret-value'))
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-secret-value"}):
            with self.assertRaises(ai.EnrichmentError) as failure:
                ai.enrich(self.memory, transport=transport)
            self.assertNotIn("test-secret-value", str(failure.exception))
            self.assertEqual(self.memory, before)
            self.assertFalse(ai.LOCK.locked())

    def test_incomplete_response_does_not_persist(self):
        def transport(request, timeout):
            return io.BytesIO(b'{"status":"incomplete","output":[]}')
        with tempfile.TemporaryDirectory() as folder, patch.object(ai, "PROCESSED", Path(folder)), patch.dict("os.environ", {"OPENAI_API_KEY": "test-only"}):
            with self.assertRaises(ai.EnrichmentError):
                ai.enrich(self.memory, transport=transport)
            self.assertFalse((Path(folder) / "ai_enrichment.json").exists())

    def test_large_corpus_is_processed_in_bounded_batches(self):
        memory = copy.deepcopy(self.memory)
        memory["events"] = [{**copy.deepcopy(self.event), "id": f"evt-{index}"} for index in range(65)]
        batch_sizes = []
        def transport(request, timeout):
            batch = json.loads(json.loads(request.data)["input"])
            batch_sizes.append(len(batch))
            annotations = [{**self.annotation, "event_id": item["event_id"]} for item in batch]
            body = {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps({"annotations": annotations})}]}]}
            return io.BytesIO(json.dumps(body).encode())
        with tempfile.TemporaryDirectory() as folder, patch.object(ai, "PROCESSED", Path(folder)), patch.dict("os.environ", {"OPENAI_API_KEY": "test-only"}):
            result = ai.enrich(memory, transport=transport)
            self.assertEqual(sorted(batch_sizes), [5, 30, 30])
            self.assertEqual(result["accepted"], 65)


if __name__ == "__main__":
    unittest.main()
