def build_update_analysis(event_text, baseline, actions):
    affected = []
    event_lower = event_text.lower()
    for action in actions:
        haystack = " ".join(
            [
                action.get("title", ""),
                action.get("owner", ""),
                action.get("status", ""),
                action.get("evidence", ""),
            ]
        ).lower()
        if any(term in event_lower for term in haystack.split()[:12]):
            affected.append(action)

    return {
        "summary": "Nouvelle information recue. Comparez-la au baseline avant de modifier les conclusions approuvees.",
        "event": event_text,
        "baseline_status": baseline.get("status", "baseline incomplet"),
        "changed_items": [
            "Statut du probleme a verifier",
            "Actions potentiellement touchees",
            "Preuves a rattacher avant toute approbation",
        ],
        "affected_actions": affected[:5],
        "warning": "Ne pas inventer d'approbation. Une proposition reste une proposition tant qu'une source ne confirme pas la decision.",
    }


def generate_executive_brief(baseline, answers, timeline, actions):
    open_actions = [item for item in actions if item.get("status") != "done"]
    return {
        "title": "Brief executif NOVA",
        "status": baseline.get("status", "A completer apres ingestion et analyse des preuves."),
        "as_of": baseline.get("as_of", "2026-09-30 09:00 America/Montreal"),
        "top_points": [
            baseline.get("scope", "Portee a confirmer avec les sources du corpus."),
            baseline.get("budget", "Budget et factures a verifier."),
            baseline.get("go_live", "Date de mise en production a confirmer."),
        ],
        "risks": baseline.get("risks", ["Contradictions possibles entre sources anciennes et recentes."]),
        "open_actions": open_actions[:5],
        "evidence_ready_answers": len([answer for answer in answers if answer.get("sources")]),
        "timeline_events": len(timeline),
    }

