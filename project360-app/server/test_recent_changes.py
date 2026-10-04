import io
import json
import os
import unittest
from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from . import rag
from .recent_changes import TIMEZONE, is_recent_changes_question, recent_updates, week_window


TODAY = date(2026, 10, 3)
QUESTION = "Que'est-ce qui a changé depuis la semaine dernière?"


def event(on, text, kind="observed", path="03_Tickets/EX-1.txt", published=None):
    return {"date": on, "date_kind": kind, "summary": text, "topic": "delivery",
            "evidence": [{"path": path, "locator": "Ligne 4", "excerpt": text,
                          "published_on": published or on}]}


class RecentChangesTests(unittest.TestCase):
    def setUp(self):
        self.clock = patch("server.recent_changes.datetime")
        mocked = self.clock.start()
        mocked.now.return_value = datetime(2026, 10, 3, 12, tzinfo=ZoneInfo(TIMEZONE))
        self.addCleanup(self.clock.stop)

    def test_typo_accents_and_weekly_variants(self):
        for text in (QUESTION, "Qu'est-ce qui a changé la semaine dernière ?",
                     "What changed since last week?", "What changed in the last 7 days?"):
            self.assertTrue(is_recent_changes_question(text), text)
        self.assertFalse(is_recent_changes_question("Quels sont les principaux risques ?"))

    def test_rolling_week_is_anchored_to_today_not_corpus_end(self):
        self.assertEqual(week_window(QUESTION), (date(2026, 9, 26), TODAY))
        result = recent_updates({"as_of": "2026-09-29", "events": []}, QUESTION)
        self.assertEqual(result["start"], "2026-09-26")
        self.assertEqual(result["end"], "2026-10-03")

    def test_calendar_week_and_year_boundary(self):
        self.assertEqual(week_window("Qu'est-ce qui a changé la semaine dernière ?", TODAY),
                         (date(2026, 9, 21), date(2026, 9, 27)))
        self.assertEqual(week_window(QUESTION, date(2027, 1, 3)),
                         (date(2026, 12, 27), date(2027, 1, 3)))

    def test_event_dates_are_inclusive_and_plans_and_snapshots_are_not_changes(self):
        events = [event("2026-09-25", "Ancienne décision approuvée."),
                  event("2026-09-26", "Nouveau correctif livré.", published="2026-09-12"),
                  event("2026-10-03", "Nouvelle décision approuvée."),
                  event("2026-10-04", "Événement futur."),
                  event("2026-09-28", "Mise en production", kind="planned"),
                  event("2026-09-29", "R-05 | Fermé", path="Registre_Risques.xlsx")]
        result = recent_updates({"events": events}, QUESTION)
        self.assertEqual([item["date"] for item in result["updates"]], ["2026-09-26", "2026-10-03"])
        self.assertEqual(result["updates"][0]["evidence"][0]["published_on"], "2026-09-12")

    def test_new_document_does_not_redate_old_closure(self):
        memory = {"events": [event("2026-09-29", "Le connecteur a été fermé le 17 septembre 2026.")]}
        self.assertEqual(recent_updates(memory, QUESTION)["updates"], [])

    def test_unchanged_statuses_are_separate_from_changes(self):
        result = recent_updates({"events": [event("2026-09-29", "Toujours pas reçu la version finale."),
                                              event("2026-09-26", "Statut maintenu EN VALIDATION.")]}, QUESTION)
        self.assertEqual({item["section"] for item in result["updates"]}, {"followups"})

    @patch.object(rag, "_external_reasoning_answer", return_value=None)
    def test_real_corpus_filters_before_model_and_discloses_coverage(self, model):
        result = rag.answer_question(QUESTION)
        self.assertEqual(result["date_window"]["start"], "2026-09-26")
        self.assertIn("s'arrêtent au 2026-09-29", result["answer"])
        self.assertIn("Suivis et rappels", result["answer"])
        self.assertNotIn("2026-09-17", result["answer"])
        self.assertNotIn("R-05", result["answer"])
        self.assertTrue(model.called)
        for item in model.call_args.args[1]:
            self.assertGreaterEqual(item["source_date"], "2026-09-26")
            self.assertLessEqual(item["source_date"], "2026-10-03")
        self.assertTrue(any(item["published_on"] < "2026-09-26" for item in result["excerpts"]))

    def test_no_recent_evidence_does_not_fall_back_to_old_search_results(self):
        memory = {"as_of": "2026-09-17", "events": [event("2026-09-17", "Connecteur fermé.")]}
        with patch.object(rag, "_load", return_value=memory), patch.object(rag, "_external_reasoning_answer") as model:
            result = rag.answer_question(QUESTION)
        model.assert_not_called()
        self.assertEqual(result["references"], [])
        self.assertIn("Aucun changement daté", result["answer"])
        self.assertEqual(result["confidence"], "low")

    def test_model_cannot_reintroduce_an_older_dated_change(self):
        with patch.object(rag, "_external_reasoning_answer", return_value={
            "answer": "Le 17 septembre 2026, INT-101 a été fermé.", "provider": "ollama",
            "confidence": "high", "uncertainty": ""
        }):
            result = rag.answer_question(QUESTION)
        self.assertEqual(result["reasoning_mode"], "local")
        self.assertIn("antérieure", result["fallback_reason"])
        self.assertNotIn("17 septembre", result["answer"])

    def test_ollama_gets_required_sections_and_exact_date_window(self):
        def transport(request, timeout):
            body = json.loads(request.data)
            prompt = json.loads(body["messages"][1]["content"])
            self.assertIn("2026-09-26 au 2026-10-03", prompt["question"])
            self.assertIn("Write all answer values in French.", prompt["output_rules"])
            required = body["format"]["properties"]["answer"]["required"]
            self.assertEqual(required, ["updates", "followups"])
            content = {"answer": {"updates": "Le 26 septembre, le comité précise les conditions de go-live.",
                                  "followups": "Le 29 septembre, le runbook reste attendu."},
                       "confidence": "medium", "uncertainty": "Sources jusqu'au 29 septembre."}
            return io.BytesIO(json.dumps({"message": {"content": json.dumps(content)}}).encode())
        with patch.dict(os.environ, {"OLLAMA_MODEL": "test-model", "OLLAMA_TIMEOUT": "45"}), \
             patch.object(rag.urllib.request, "urlopen", side_effect=transport):
            result = rag.answer_question(QUESTION)
        self.assertEqual(result["reasoning_mode"], "ollama")
        self.assertIsNone(result["fallback_reason"])


if __name__ == "__main__":
    unittest.main()
