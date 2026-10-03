import json
import unittest
from pathlib import Path

from .intelligence import build_project_memory, classify, dates_in, extract_ticket, source_date


def document(text, path="02_Reunions/meeting.txt", extension=".txt", identifier="doc-test"):
    return {"id": identifier, "path": path, "extension": extension, "text": text}


class TemporalExtractionTests(unittest.TestCase):
    def test_french_dates_and_inherited_year(self):
        self.assertEqual([d["date"] for d in dates_in("1er août 2026, 26 sept et 2026-10-22", 2026)],
                         ["2026-08-01", "2026-09-26", "2026-10-22"])
        self.assertEqual(dates_in("31 février 2026 et 5 sept"), [])

    def test_target_is_not_publication_date(self):
        self.assertIsNone(source_date(document("Date cible de mise en production : 22 octobre 2026")))
        self.assertIsNone(source_date(document("Période\n7 juillet au 31 octobre 2026", extension=".pdf")))

    def test_spreadsheet_publication_is_not_first_phase_start(self):
        doc = document("ID | Début\nP-01 | 2026-07-07", "04_Documents_projet/Plan_v3_12sept.xlsx", ".xlsx")
        self.assertEqual(source_date(doc), "2026-09-12")

    def test_email_date_and_sender_do_not_assign_recipient(self):
        doc = document("Subject: Correctif\nFrom: Julien Moreau <julien@example.test>\nTo: Sophie Lambert <sophie@example.test>\nDate: Sat, 19 Sep 2026 10:20:00 -0400\nFix déployé. Re-test requis.", "01_Courriels/test.eml", ".eml")
        memory = build_project_memory([doc])
        self.assertEqual(memory["events"][0]["date"], "2026-09-19")
        self.assertEqual(memory["events"][0]["owner"], "Julien Moreau")
        self.assertEqual(memory["events"][0]["owner_role"], "Auteur")

    def test_negated_approval_and_delivery_are_not_acceptance(self):
        self.assertEqual(classify("CR-04 n’est pas approuvé.")[1], "not_approved")
        self.assertEqual(classify("Brouillon : approbation requise.")[1], "proposed")
        self.assertEqual(classify("Fix déployé. Ne pas fermer avant validation sécurité.")[1], "in_review")

    def test_governance_overrides_proposal_and_stale_plan(self):
        proposal = document("Date : 8 septembre 2026\nNotre recommandation est de déplacer la mise en production au 22 octobre. Ceci reste une proposition.", identifier="proposal")
        decision = document("Date : 10 septembre 2026\nLa date cible de mise en production est déplacée au 22 octobre 2026. Donc approuvé. Le 22 devient la date officielle, sous réserve des validations.", identifier="decision")
        plan = document("[sheet Plan projet]\nID | Activité | Statut | Responsable | Début planifié | Fin planifiée | Note\nP-06 | Mise en production | À venir | Nicolas Perron | 2026-10-15 | 2026-10-15 | Cible initiale", "04_Documents_projet/Plan_v3_12sept.xlsx", ".xlsx", "plan")
        memory = build_project_memory([proposal, decision, plan])
        self.assertEqual(memory["schedule"]["current_target"], "2026-10-22")
        self.assertEqual(memory["schedule"]["changes"][0]["date"], "2026-09-10")
        self.assertTrue(any(a["id"] == "stale-plan" for a in memory["alerts"]))
        self.assertTrue(any(e["status"] == "superseded" for e in memory["events"]))

    def test_no_future_realization_or_global_completion_inferred(self):
        doc = document("Date : 7 juillet 2026\nCharte : mise en production ciblée au 15 octobre 2026.")
        memory = build_project_memory([doc])
        self.assertEqual(memory["as_of"], "2026-07-07")
        self.assertEqual(memory["stats"]["completed_tickets"], 0)
        self.assertNotIn("completion_percent", memory)

    def test_ticket_completion_uses_validation_date(self):
        doc = document("TICKET INT-101\nTitre : Connecteur\nCréé : 5 septembre 2026\nDemandeur : Marc Gervais\nStatut : Fermé\nCommentaires :\n17 sept 14:23 - Boréal : Correctif déployé.\n17 sept 16:10 - Marc : Validé. Je ferme.", "03_Tickets/INT-101.txt")
        events, ticket = extract_ticket(doc, {"marc": "Marc Gervais"})
        self.assertEqual(ticket["completed_on"], "2026-09-17")
        self.assertEqual(events[1]["status"], "delivered")
        self.assertEqual(events[2]["status"], "completed")
        self.assertEqual(events[2]["owner"], "Marc Gervais")

    def test_undated_and_unrelated_documents_do_not_invent_events(self):
        memory = build_project_memory([document("Document sans date explicite."), document("Date : 2 octobre 2026\nFormation Excel", "08_Archives_et_documents_connexes/excel.txt", identifier="unrelated")])
        self.assertEqual(memory["events"], [])
        self.assertEqual(memory["extraction"]["excluded_documents"], 1)
        self.assertEqual(len(memory["extraction"]["undated_documents"]), 1)

    def test_duplicate_events_keep_sources_and_stable_ids(self):
        doc = document("Date : 7 juillet 2026\nDécision : Canada Central.")
        other = {**doc, "id": "other"}
        first = build_project_memory([doc, other])
        second = build_project_memory([other, doc])
        self.assertEqual(len(first["events"]), 1)
        self.assertEqual(len(first["events"][0]["evidence"]), 2)
        self.assertEqual(first["events"][0]["id"], second["events"][0]["id"])


class NovaCorpusRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "data/processed/documents.json"
        cls.documents = json.loads(path.read_text(encoding="utf-8"))
        cls.memory = build_project_memory(cls.documents)

    def test_real_target_and_closed_tickets(self):
        self.assertEqual(self.memory["schedule"]["current_target"], "2026-10-22")
        self.assertEqual(self.memory["schedule"]["delay_days"], 7)
        self.assertEqual(self.memory["schedule"]["changes"][-1]["date"], "2026-09-10")
        self.assertEqual(self.memory["stats"]["completed_tickets"], 5)
        self.assertEqual(self.memory["as_of"], "2026-09-29")

    def test_three_gates_and_explicit_project_owner_transition(self):
        self.assertEqual({t["id"] for t in self.memory["gates"]}, {"SEC-210", "ACC-303", "OPS-601"})
        self.assertEqual([(a["effective_on"], a["owner"]) for a in self.memory["assignments"]],
                         [("2026-07-07", "Élodie Caron"), ("2026-09-16", "Nicolas Perron")])

    def test_all_evidence_ids_and_locators_are_resolvable(self):
        ids = {d["id"] for d in self.documents}
        event_ids = [e["id"] for e in self.memory["events"]]
        self.assertEqual(len(event_ids), len(set(event_ids)))
        for event in self.memory["events"]:
            self.assertRegex(event["date"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertTrue(event["evidence"])
            for source in event["evidence"]:
                self.assertIn(source["document_id"], ids)
                self.assertTrue(source["locator"])
                self.assertTrue(source["excerpt"])


if __name__ == "__main__":
    unittest.main()
