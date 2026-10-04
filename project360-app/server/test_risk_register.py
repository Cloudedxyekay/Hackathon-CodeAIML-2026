import io
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from . import rag
from .extractors.read_xlsx import read_xlsx
from .risk_register import current_risks, is_current_risk_question, parse_rows


class RiskRegisterTests(unittest.TestCase):
    question = "Quels sont les trois principaux risques du projet aujourd'hui?"

    @classmethod
    def setUpClass(cls):
        cls.documents = json.loads((rag.PROCESSED / "documents.json").read_text())
        cls.register = next(d for d in cls.documents if "Registre_Risques_29sept" in d["path"])

    def test_original_workbook_and_flattened_cache_have_the_same_rows(self):
        path = rag.ROOT.parent / "project 360 data/NOVA_ETUDIANTS" / self.register["path"]
        original = parse_rows({**self.register, "text": read_xlsx(path)})
        cached = parse_rows(self.register)
        fields = ("id", "risque", "probabilite", "impact", "statut", "mitigation", "commentaire")
        self.assertEqual([{k: row.get(k) for k in fields} for row in original],
                         [{k: row.get(k) for k in fields} for row in cached])
        self.assertEqual(len(cached), 5)

    def test_active_ranking_excludes_closed_and_explicitly_resolved_risks(self):
        result = current_risks(self.documents)
        self.assertEqual([row["id"] for row in result["active"]], ["R-02", "R-03", "R-04"])
        self.assertEqual([row["priority_score"] for row in result["active"]], [9, 6, 4])
        excluded = {row["id"]: row for row in result["excluded"]}
        self.assertEqual(excluded["R-05"]["exclusion"], "closed")
        self.assertEqual(excluded["R-01"]["resolution"]["date"], "2026-09-17")
        self.assertEqual(result["date"], "2026-09-29")

    def test_latest_register_can_reopen_a_previously_resolved_risk(self):
        newer = {**self.register, "path": "04_Documents_projet/Registre_Risques_30sept.xlsx",
                 "text": self.register["text"].replace("Suivi au 9 septembre 2026", "Réouvert au 30 septembre 2026")}
        result = current_risks([*self.documents, newer])
        self.assertEqual(result["date"], "2026-09-30")
        self.assertIn("R-01", [row["id"] for row in result["active"]])
        self.assertNotIn("R-01", [row["id"] for row in result["excluded"]])

    def test_negated_future_and_unrelated_resolution_do_not_close_connector(self):
        for sentence in ("Le risque du connecteur n'est pas résolu.",
                         "Le risque du connecteur sera résolu.",
                         "Le connecteur reste à suivre. Le risque de migration est résolu."):
            email = {"id": "check", "path": "01_Courriels/check.eml", "extension": ".eml",
                     "text": f"Subject: Suivi général From: Test Date: Thu, 17 Sep 2026 16:22:00 -0400 Bonjour, {sentence}"}
            result = current_risks([self.register, email])
            self.assertNotIn("R-01", [row["id"] for row in result["excluded"]], sentence)

    def test_unknown_status_is_not_assumed_open(self):
        changed = {**self.register, "text": self.register["text"].replace("Sophie Lambert | Ouvert", "Sophie Lambert | À confirmer")}
        result = current_risks([changed])
        self.assertNotIn("R-02", [row["id"] for row in result["active"]])

    def test_ranking_is_derived_from_values_not_fixed_risk_ids(self):
        changed = {**self.register, "text": self.register["text"].replace("Accessibilité | Moyenne | Moyen", "Accessibilité | Élevée | Critique")}
        documents = [d for d in self.documents if d["path"] != self.register["path"]] + [changed]
        result = current_risks(documents)
        self.assertEqual(result["active"][0]["id"], "R-04")

    @patch.object(rag, "_external_reasoning_answer", return_value=None)
    def test_question_uses_register_rows_with_resolvable_exclusion_evidence(self, model):
        result = rag.answer_question(self.question)
        self.assertEqual([item["answer_key"] for item in model.call_args.args[1]], ["R-02", "R-03", "R-04"])
        self.assertIn("2026-09-29", result["answer"])
        self.assertIn("encore ouvert dans le registre", result["answer"])
        self.assertEqual(result["cited_source_files"], [self.register["path"], "01_Courriels/E12_Resolution_integration.eml"])
        self.assertTrue(all(item["locator"] for item in result["excerpts"]))

    def test_ollama_schema_requires_only_the_three_selected_active_risks(self):
        def transport(request, timeout):
            body = json.loads(request.data)
            required = body["format"]["properties"]["answer"]["required"]
            self.assertEqual(required, ["R-02", "R-03", "R-04"])
            payload = {"answer": {key: "Effectuer la mitigation indiquée dans le registre." for key in required},
                       "confidence": "high", "uncertainty": ""}
            return io.BytesIO(json.dumps({"message": {"content": json.dumps(payload)}}).encode())
        with patch.dict(os.environ, {"OLLAMA_MODEL": "test-model", "OLLAMA_TIMEOUT": "45"}), \
             patch.object(rag.urllib.request, "urlopen", side_effect=transport):
            result = rag.answer_question(self.question)
        self.assertEqual(result["reasoning_mode"], "ollama")
        self.assertIsNone(result["fallback_reason"])

    def test_missing_register_does_not_invent_three_risks(self):
        with patch.object(rag, "_load", return_value=[]), patch.object(rag, "_external_reasoning_answer") as model:
            result = rag.answer_question(self.question)
        model.assert_not_called()
        self.assertEqual(result["confidence"], "low")
        self.assertEqual(result["references"], [])

    def test_intent_and_requested_count(self):
        self.assertTrue(is_current_risk_question(self.question))
        self.assertTrue(is_current_risk_question("What are the top three project risks today?"))
        self.assertFalse(is_current_risk_question("Quels risques sont fermés ?"))
        self.assertFalse(is_current_risk_question("Pourquoi R-01 est-il un risque ?"))
        with patch.object(rag, "_external_reasoning_answer", return_value=None) as model:
            rag.answer_question("Quels sont les deux principaux risques actuels ?")
        self.assertEqual(len(model.call_args.args[1]), 2)


if __name__ == "__main__":
    unittest.main()
