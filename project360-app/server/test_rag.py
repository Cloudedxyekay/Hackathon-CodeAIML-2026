import io
import json
import os
import unittest
from unittest.mock import patch

from . import rag


class CommitmentAnswerTests(unittest.TestCase):
    question = "Queels engagements ne sont toujours pas complétés?"

    def test_intent_handles_typo_accents_and_paraphrases(self):
        for question in (self.question, "Quelles tâches restent à terminer ?",
                         "Quels engagements sont encore ouverts ?", "Which tasks are unfinished?"):
            self.assertTrue(rag._asks_open_commitments(question), question)
        self.assertFalse(rag._asks_open_commitments("Quelle est la date approuvée ?"))

    @patch.object(rag, "_external_reasoning_answer", return_value=None)
    def test_corpus_inventory_includes_technical_admin_and_deferred_scope(self, model):
        result = rag.answer_question(self.question)
        answer = result["answer"]
        for identifier in ("SEC-210", "ACC-303", "OPS-601", "INV-003"):
            self.assertIn(identifier, answer)
        self.assertIn("mettre à jour la date", answer)
        self.assertIn("Phase 2, hors engagements approuvés de Phase 1", answer)
        for identifier in ("INT-101", "DATA-401", "PERF-501", "ACC-301", "ACC-302"):
            self.assertNotIn(identifier, answer)
        self.assertNotIn("README.txt", result["cited_source_files"])
        self.assertIn("clôture reste à confirmer", answer)

    @patch.object(rag, "_external_reasoning_answer", return_value=None)
    def test_model_receives_compact_statuses_and_complete_scope(self, model):
        rag.answer_question(self.question)
        _, evidence, excerpts = model.call_args.args
        sources = {item["path"]: excerpt["excerpt"] for item, excerpt in zip(evidence, excerpts)}
        self.assertIn("Statut : EN VALIDATION", sources["03_Tickets/SEC-210.txt"])
        self.assertIn("Ne pas fermer avant validation sécurité", sources["03_Tickets/SEC-210.txt"])
        self.assertIn("Statut : FERME", sources["03_Tickets/INT-101.txt"])
        self.assertIn("sans nouvelle approbation", " ".join(sources.values()))
        self.assertIn("phase 2", " ".join(sources.values()))
        self.assertLess(sum(map(len, sources.values())), 4000)

    def test_incomplete_model_summaries_fall_back_to_inventory(self):
        for answer in (
            "SEC-210 est en validation. CR-04 reste à faire.",
            "SEC-210, ACC-303, OPS-601. Phase 1. CR-04 est en Phase 2.",
            "SEC-210, ACC-303, OPS-601. Plans et facture à vérifier. CR-04 reste à faire.",
        ):
            with patch.object(rag, "_external_reasoning_answer", return_value={
                "answer": answer, "confidence": "high", "uncertainty": "", "provider": "ollama"
            }):
                result = rag.answer_question(self.question)
                self.assertEqual(result["reasoning_mode"], "local")
                self.assertIn("omis", result["fallback_reason"])
                self.assertIn("INV-003", result["answer"])
                self.assertIn("Phase 2", result["answer"])

    def test_empty_corpus_does_not_claim_completion(self):
        with patch.object(rag, "_load", return_value=[]):
            result = rag.answer_question(self.question)
        self.assertEqual(result["confidence"], "low")
        self.assertEqual(result["references"], [])
        self.assertIn("cela ne prouve pas", result["answer"])


class OllamaConnectionTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"OLLAMA_MODEL": "test-model", "OLLAMA_TIMEOUT": "45"})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_schema_and_generation_budget_and_actual_provider(self):
        content = {"answer": "La cible est le 22 octobre.", "confidence": "high", "uncertainty": ""}

        def transport(request, timeout):
            body = json.loads(request.data)
            self.assertEqual(body["format"], rag.REASONING_SCHEMA)
            self.assertEqual(body["options"]["num_ctx"], 3072)
            self.assertEqual(body["options"]["num_predict"], 256)
            self.assertEqual(body["keep_alive"], "30m")
            self.assertEqual(timeout, 45)
            return io.BytesIO(json.dumps({"message": {"content": json.dumps(content)}, "done_reason": "stop"}).encode())

        with patch.object(rag.urllib.request, "urlopen", side_effect=transport):
            result = rag.answer_question("Quelle est la date de mise en production actuellement approuvée?")
        self.assertEqual(result["reasoning_mode"], "ollama")
        self.assertIsNone(result["fallback_reason"])
        self.assertIn("elapsed_seconds", result)

    def test_timeout_is_explained_and_does_not_call_second_provider(self):
        with patch.object(rag.urllib.request, "urlopen", side_effect=TimeoutError), patch.object(rag, "_openai_reasoning_answer") as other:
            result = rag.answer_question("Quelle est la date de mise en production actuellement approuvée?")
        self.assertEqual(result["reasoning_mode"], "local")
        self.assertIn("délai", result["fallback_reason"])
        other.assert_not_called()
        self.assertFalse(rag._ollama_lock.locked())

    def test_commitment_schema_requires_every_item_and_keeps_ollama_provider(self):
        def transport(request, timeout):
            body = json.loads(request.data)
            required = body["format"]["properties"]["answer"]["required"]
            self.assertEqual(set(required), {"ACC-303", "OPS-601", "SEC-210", "followup_1", "followup_2", "deferred_scope"})
            answer = {key: "Validation à obtenir selon les sources." for key in required}
            answer["followup_1"] = "Clarifier la ligne CR-04 de la facture INV-003 avant sa libération."
            answer["deferred_scope"] = "CR-04 est reporté, sans approbation pour engager les dépenses."
            payload = {"answer": answer, "confidence": "medium", "uncertainty": "Clôtures administratives non confirmées."}
            return io.BytesIO(json.dumps({"message": {"content": json.dumps(payload)}}).encode())

        with patch.object(rag.urllib.request, "urlopen", side_effect=transport):
            result = rag.answer_question(CommitmentAnswerTests.question)
        self.assertEqual(result["reasoning_mode"], "ollama")
        self.assertIsNone(result["fallback_reason"])
        self.assertIn("Phase 2", result["answer"])
        self.assertIn("INV-003", result["answer"])

    def test_incomplete_structured_answer_is_rejected(self):
        sections = [{"answer_key": "SEC-210", "answer_label": "SEC-210"},
                    {"answer_key": "OPS-601", "answer_label": "OPS-601"}]
        for answer in ({"SEC-210": "Re-test requis."}, {"SEC-210": "Re-test requis.", "OPS-601": ""}):
            content = json.dumps({"answer": answer, "confidence": "high", "uncertainty": ""})
            self.assertIsNone(rag._parse_reasoning_json(content, sections))

    def test_busy_model_does_not_queue_another_generation(self):
        with rag._ollama_lock, patch.object(rag.urllib.request, "urlopen") as transport:
            result = rag.answer_question("Quelle est la date de mise en production actuellement approuvée?")
        transport.assert_not_called()
        self.assertIn("déjà", result["fallback_reason"])

    def test_truncated_or_malformed_responses_are_not_presented_as_ollama_answers(self):
        for data in ({"done_reason": "length"}, {"message": {"content": "not JSON"}}):
            with patch.object(rag.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(data).encode())):
                result = rag.answer_question("Quelle est la date de mise en production actuellement approuvée?")
            self.assertEqual(result["reasoning_mode"], "local")
            self.assertTrue(result["fallback_reason"])

    def test_fallback_reason_does_not_leak_between_requests(self):
        with patch.object(rag.urllib.request, "urlopen", side_effect=TimeoutError):
            rag.answer_question("Quelle est la date de mise en production actuellement approuvée?")
        with patch.object(rag, "_load", return_value=[]):
            result = rag.answer_question("Nothing available")
        self.assertIsNone(result["fallback_reason"])


if __name__ == "__main__":
    unittest.main()
