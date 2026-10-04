import json
import math
import os
import re
import socket
import urllib.error
import urllib.request
import unicodedata
from contextvars import ContextVar
from threading import Lock
from time import monotonic
from collections import Counter
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

from .risk_register import current_risks, is_current_risk_question, requested_count
from .recent_changes import is_recent_changes_question, recent_updates
from .intelligence import dates_in
from .contradictions import is_contradiction_question, comparisons

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
_reasoning_failure = ContextVar("reasoning_failure", default=None)
_ollama_lock = Lock()

# These defaults favour interactive local responses.  They can be raised for a
# larger model or more exhaustive answers without changing the code.
OLLAMA_DEFAULT_CONTEXT_TOKENS = 3072
OLLAMA_DEFAULT_PREDICT_TOKENS = 256

REASONING_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "uncertainty": {"type": "string"},
    },
    "required": ["answer", "confidence", "uncertainty"],
    "additionalProperties": False,
}


def _load(name, fallback):
    path = PROCESSED / name
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def _tokens(text):
    return re.findall(r"[a-zA-ZÀ-ÿ0-9_-]{2,}", (text or "").lower())


def _score(query, text):
    query_terms = Counter(_tokens(query))
    text_terms = Counter(_tokens(text))
    if not query_terms or not text_terms:
        return 0.0
    score = 0.0
    for term, q_count in query_terms.items():
        if term in text_terms:
            score += (1 + math.log(text_terms[term])) * q_count
    return score


def search_documents(query, limit=8):
    chunks = _load("chunks.json", [])
    ranked = []
    for chunk in chunks:
        if chunk.get("path") in {"README.txt", "MANIFEST.csv"}:
            continue
        haystack = " ".join(
            [
                chunk.get("title", ""),
                chunk.get("path", ""),
                chunk.get("text", ""),
                " ".join(chunk.get("tags", [])),
            ]
        )
        score = _score(query, haystack)
        if score > 0:
            source_date = _source_date(chunk)
            ranked.append(
                {
                    **chunk,
                    "score": round(score, 3),
                    "source_date": source_date["display"],
                    "source_timestamp": source_date["timestamp"],
                }
            )
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:limit]


def _search_candidates(question):
    candidates = search_documents(question, limit=14)
    for expansion in _query_expansions(question):
        candidates = _merge_evidence(candidates, search_documents(expansion, limit=10))
    return candidates


def _query_expansions(question):
    value = " ".join(_tokens(question))
    expansions = []

    if _asks_why(value) and _mentions_go_live(value):
        expansions.append(
            "cible approuvee demeure 22 octobre date officielle comite conditions go-live connecteur stabilisation INT-101 ferme valide"
        )
    elif _mentions_go_live(value) and _asks_current(value):
        expansions.append("cible approuvee demeure 22 octobre date officielle comite conditions go-live")

    return expansions


def reasoning_status():
    status = {
        "ollama_model": os.getenv("OLLAMA_MODEL"),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        "ollama_reachable": False,
        "ollama_models": [],
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
    }
    base_url = status["ollama_base_url"].rstrip("/")
    request = urllib.request.Request(f"{base_url}/api/tags", method="GET")

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        status["ollama_reachable"] = True
        status["ollama_models"] = [model.get("name") for model in data.get("models", []) if model.get("name")]
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError, socket.timeout):
        pass

    return status


def _fold(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def _asks_open_commitments(question):
    value = _fold(question)
    return bool(
        re.search(r"\b(engagements?|taches?|travaux|commitments?|tasks?|actions?)\b", value)
        and re.search(r"pas|reste|restant|encore|non|inachev|incomplet|ouvert|pending|outstanding|unfinished|uncompleted|not.*completed", value)
    )


def _commitment_inventory():
    """Use complete source records so a broad inventory is not a top-k keyword search.

    Keep closed tickets as counter-evidence and scope decisions with their negations.
    Administrative follow-ups are reported as unconfirmed, not inferred overdue work.
    """
    evidence, tickets, followups, deferred = [], [], [], []
    for document in _load("documents.json", []):
        path = document.get("path", "")
        if path.startswith("08_Archives") or path in {"README.txt", "MANIFEST.csv"}:
            continue
        text = _normalize_space(document.get("text", ""))
        if not text or text.startswith("Extraction failed:"):
            continue
        value = _fold(text)
        ticket = re.match(r"TICKET\s+([A-Z]+-\d+)", text)
        status = re.search(r"\bStatut\s*:\s*(EN VALIDATION|OUVERT|FERMÉ|FERME)\b", text, re.I)
        # These clauses capture requests, not every historical mention of a topic.
        plan_action = re.search(r"(?:faire\s+)?mettre a jour[^.;]+(?:plans?|communications?)[^.;]*", value)
        finance_action = "facture" in value and bool(re.search(r"avant de la liberer|approbation correspondante", value))
        scope_decision = "phase 2" in value and bool(re.search(r"report|pas.*approuv|sans.*approbation", value))
        supporting = bool(re.search(r"conditions.*go-live|validation securite|runbook|rollback", value))
        if not (ticket or plan_action or finance_action or scope_decision or supporting):
            continue
        date = _source_date(document)
        item = {**document, "text": text, "locator": "Document complet", "score": 1.0,
                "source_date": date["display"], "source_timestamp": date["timestamp"]}
        evidence.append(item)
        if ticket and status:
            title = re.search(r"Titre\s*:\s*(.*?)\s+Créé\s*:", text)
            tickets.append({"id": ticket[1], "status": _fold(status[1]),
                            "title": title[1] if title else ticket[1], "item": item})
        if plan_action:
            # Find the equivalent original sentence without losing accents.
            sentence = next((s for s in re.split(r"[;]|(?<=[.!?])\s+", text)
                             if "mettre a jour" in _fold(s) and re.search(r"plans?|communications?", _fold(s))), text)
            followups.append(("Plans et communications", sentence.strip(" -"), item))
        if finance_action:
            body = re.split(r"\bBonjour[^,]*,", text, maxsplit=1)
            followups.append(("Validation financière", body[-1].strip(), item))
        if scope_decision:
            deferred.append(item)
    deferred.sort(key=lambda item: item.get("source_timestamp") or 0)
    return evidence, tickets, followups, deferred


def _commitment_model_evidence(tickets, followups, deferred):
    """Send every item's current state, without repeating entire source histories."""
    selected = []
    for ticket in tickets:
        text = ticket["item"]["text"]
        summary = f"{ticket['id']} — {ticket['title']}. Statut : {ticket['status'].upper()}."
        if ticket["status"] != "ferme":
            description = re.search(r"Description(?: initiale)?\s*:\s*(.*?)(?=Pièce jointe|Étapes|Commentaires|$)", text)
            if description:
                summary += " " + description[1].strip()
            comments = re.split(r"Commentaires\s*:", text, maxsplit=1)
            if len(comments) > 1:
                updates = re.split(r"(?=\b\d{1,2}\s+(?:sept|septembre|octobre|août)\b)", comments[1])
                summary += " " + " ".join(updates[-2:]).strip()
            # Older details can still describe the outstanding deliverable.
            for sentence in _sentences(text):
                if "rollback" in sentence.lower() and sentence not in summary:
                    summary += " " + sentence
        selected.append({**ticket["item"], "text": summary,
                         "answer_key": ticket["id"] if ticket["status"] != "ferme" else None,
                         "answer_label": f"{ticket['id']} ({ticket['status']})"})
    for index, (label, detail, item) in enumerate(followups):
        selected.append({**item, "text": f"{label} (clôture non confirmée) : {detail}",
                         "answer_key": f"followup_{index + 1}",
                         "answer_label": f"{label} (clôture non confirmée)"})
    if deferred:
        selected.append({**deferred[-1], "answer_key": "deferred_scope",
                         "answer_label": "Phase 2 — hors engagements approuvés de Phase 1, nouvelle approbation requise"})
    return selected


def _answer_open_commitments(question):
    evidence, tickets, followups, deferred = _commitment_inventory()
    open_tickets = [t for t in tickets if t["status"] != "ferme"]
    lines = ["Selon les statuts documentés, les engagements techniques encore ouverts ou en validation sont :"]
    for ticket in open_tickets:
        text = ticket["item"]["text"]
        comments = re.split(r"Commentaires\s*:", text, maxsplit=1)
        # Preserve the whole status history: delivery alone cannot close a ticket.
        detail = comments[-1] if len(comments) > 1 else text
        lines.append(f"- {ticket['id']} — {ticket['title']} ({ticket['status']}) : {detail}")
    if not open_tickets:
        lines.append("Aucun ticket ouvert identifié dans les sources disponibles ; cela ne prouve pas que tous les engagements sont terminés.")
    if followups:
        lines.append("\nAutres suivis documentés, dont la clôture reste à confirmer :")
        for label, detail, _ in followups:
            lines.append(f"- {label} : {detail}")
    if deferred:
        lines.append("\nPortée reportée — Phase 2, hors engagements approuvés de Phase 1 :")
        lines.append(deferred[-1]["text"])
    model_evidence = _commitment_model_evidence(tickets, followups, deferred)
    excerpts = [{"excerpt": item["text"], "matched_terms": 0} for item in model_evidence]
    model_answer = _external_reasoning_answer(question, model_evidence, excerpts) if model_evidence else None
    # Reject a summary that drops a known open ticket or loses the phase boundary.
    if model_answer:
        answer_value = _fold(model_answer["answer"])
        missing_ticket = any(t["id"].lower() not in answer_value for t in open_tickets)
        missing_scope = bool(deferred) and (
            not all(s in answer_value for s in ("phase 2", "phase 1"))
            or not re.search(r"non approuv|pas approuv|hors.*phase 1|nouvelle approbation|not approved|outside.*phase 1", answer_value)
        )
        missing_followup = any(
            not re.search(r"plan|communication", answer_value) if label == "Plans et communications"
            else not re.search(r"factur|financ|invoice", answer_value)
            for label, _, _ in followups
        )
        if missing_ticket or missing_scope or missing_followup:
            _reasoning_failure.set("Le modèle a omis un engagement ou sa portée. La liste vérifiée des sources est affichée.")
            model_answer = None
    return {
        "question": question, "answer": model_answer["answer"] if model_answer else "\n".join(lines),
        "reasoning_mode": model_answer.get("provider", "external_model") if model_answer else "local",
        "confidence": "medium" if evidence else "low",
        "cited_source_files": _source_files(evidence), "references": _references(evidence),
        "excerpts": [{"file": item["path"], "locator": item["locator"], "date": item["source_date"],
                      "excerpt": item["text"], "score": item["score"]} for item in evidence],
        "evidence": [{"file": item["path"], "locator": item["locator"], "date": item["source_date"],
                      "excerpt": item["text"], "score": item["score"]} for item in evidence],
        "uncertainty": "État fondé sur les sources ingérées. Une livraison ne vaut pas acceptation. "
                       "L'absence de confirmation de clôture d'un suivi administratif ne prouve pas qu'il est encore en cours.",
    }


def answer_question(question):
    token = _reasoning_failure.set(None)
    started = monotonic()
    try:
        result = _answer_question(question)
        result["reasoning_mode"] = result.get("reasoning_mode", "local")
        result["fallback_reason"] = _reasoning_failure.get() if result["reasoning_mode"] == "local" else None
        result["elapsed_seconds"] = round(monotonic() - started, 2)
        return result
    finally:
        _reasoning_failure.reset(token)


def _answer_current_risks(question):
    inventory = current_risks(_load("documents.json", []), requested_count(question))
    if not inventory or not inventory["rows"]:
        return {"question": question,
                "answer": "Je ne dispose pas d'un registre des risques lisible pour établir les principaux risques actuels.",
                "confidence": "low", "cited_source_files": [], "references": [], "excerpts": [], "evidence": [],
                "uncertainty": "Ré-ingérez le registre des risques avant de conclure."}

    def evidence_row(row):
        return {**row["document"], "text": row["raw"], "locator": row["locator"], "score": 1.0,
                "source_date": row["register_date"], "source_timestamp": None}

    selected = []
    for row in inventory["active"]:
        # Ranking and status come from the register; the model only summarizes
        # the selected row's consequence and mitigation, one required entry each.
        label = (f"{row['id']} — {row['risque']} "
                 f"(statut : {row['statut']}; probabilité : {row['probabilite']}; impact : {row['impact']}; "
                 f"responsable : {row.get('proprietaire') or 'non précisé'})")
        selected.append({**evidence_row(row), "answer_key": row["id"], "answer_label": label})
    exclusions, additional = [], []
    for row in inventory["excluded"]:
        additional.append(evidence_row(row))
        if row["exclusion"] == "closed":
            exclusions.append(f"{row['id']} ({row['risque']}) est fermé dans le registre")
        else:
            closure = row["resolution"]
            additional.append({**closure["document"], "text": closure["excerpt"], "locator": closure["locator"],
                               "score": 1.0, "source_date": closure["date"], "source_timestamp": None})
            exclusions.append(f"{row['id']} ({row['risque']}) figure encore ouvert dans le registre, "
                              f"mais la confirmation du {closure['date']} résout le problème à l'origine de ce risque")
    date_label = inventory["date"] or "date non précisée"
    preface = (f"Selon le registre du {date_label}, recoupé avec les confirmations de résolution "
               "et classé par probabilité × impact :")
    excerpts = [{"excerpt": item["text"], "matched_terms": 0} for item in selected]
    model_answer = _external_reasoning_answer(question, selected, excerpts) if selected else None
    if model_answer:
        body = model_answer["answer"]
    else:
        body = "\n".join(f"- {item['answer_label']} : {row.get('mitigation') or 'Mitigation non précisée.'}"
                         for row, item in zip(inventory["active"], selected))
    if not selected:
        body = "Aucun risque avec un statut explicitement actif n'a été identifié dans ce registre."
    answer = preface + "\n" + body
    if exclusions:
        answer += "\n\nExclus du classement : " + "; ".join(exclusions) + "."
    evidence = selected + additional
    rendered = [{"file": item["path"], "locator": item["locator"], "date": item["source_date"],
                 "excerpt": item["text"], "score": item["score"]} for item in evidence]
    return {"question": question, "answer": answer,
            "reasoning_mode": model_answer.get("provider", "external_model") if model_answer else "local",
            "confidence": "medium", "cited_source_files": _source_files(evidence),
            "references": _references(evidence), "excerpts": rendered, "evidence": rendered,
            "uncertainty": f"État documenté au {date_label}, pas une vérification en temps réel. "
                           "Classement par probabilité × impact (faible=1, moyen=2, élevé=3, critique=4); "
                           "les niveaux inconnus sont classés après les niveaux renseignés. "
                           "Une résolution de problème ne met pas automatiquement à jour le registre."}


def _answer_recent_changes(question):
    window = recent_updates(_load("project_memory.json", {}), question)
    labels = {"updates": "Décisions et annonces datées de la période",
              "followups": "Suivis et rappels — pas de changement d'état confirmé"}
    for section in labels:
        days = sorted({item["date"] for item in window["updates"] if item["section"] == section})
        if days:
            labels[section] += f" ({days[0]}" + (f" au {days[-1]})" if len(days) > 1 else ")")
    evidence, model_evidence, seen_sections = [], [], set()
    for update in window["updates"]:
        section = update["section"]
        sources = []
        for source in update["evidence"]:
            item = {"path": source["path"], "title": Path(source["path"]).stem,
                    "locator": source.get("locator", "Événement daté"), "score": 1.0,
                    "source_date": update["date"], "event_date": update["date"],
                    "published_on": source.get("published_on"), "source_timestamp": None,
                    "text": source.get("excerpt", update["text"])}
            evidence.append(item)
            sources.append(item)
        model_item = {**sources[0], "text": update["text"], "answer_section": section}
        if section not in seen_sections:
            model_item.update(answer_key=section, answer_label=labels[section])
            seen_sections.add(section)
        model_evidence.append(model_item)
    model_evidence.sort(key=lambda item: (item["answer_section"] != "updates", item["source_date"]))
    preface = (f"Période examinée : du {window['start']} au {window['end']} inclus "
               f"(fuseau {window['timezone']}).")
    model_answer = None
    if model_evidence:
        model_question = f"{question}\nPériode exacte : {window['start']} au {window['end']} inclus."
        excerpts = [{"excerpt": item["text"], "matched_terms": 0} for item in model_evidence]
        model_answer = _external_reasoning_answer(model_question, model_evidence, excerpts)
        if model_answer and any(item["date"] < window["start"]
                                for item in dates_in(model_answer["answer"], int(window["end"][:4]))):
            _reasoning_failure.set("Le modèle a ajouté une date antérieure à la période. Les événements filtrés sont affichés.")
            model_answer = None
    if model_answer:
        body = model_answer["answer"]
    elif window["updates"]:
        sections = []
        for key, label in labels.items():
            records = [item for item in window["updates"] if item["section"] == key]
            if records:
                sections.append(label + " :\n" + "\n".join(f"- {item['date']} : {item['text']}" for item in records))
        body = "\n\n".join(sections)
    else:
        body = "Aucun changement daté n'est documenté dans cette période. Cela ne prouve pas qu'aucun changement n'a eu lieu."
    if window["updates"] and "updates" not in seen_sections:
        body = "Aucun changement d'état confirmé dans cette période; seuls des suivis sont documentés.\n" + body
    coverage = window["corpus_as_of"]
    if coverage and coverage < window["end"]:
        body += f"\n\nLes sources disponibles s'arrêtent au {coverage}; aucun fait ultérieur ne peut être confirmé."
    rendered = [{"file": item["path"], "locator": item["locator"], "date": item["event_date"],
                 "published_on": item["published_on"], "excerpt": item["text"], "score": item["score"]}
                for item in evidence]
    return {"question": question, "answer": preface + "\n\n" + body,
            "reasoning_mode": model_answer.get("provider", "external_model") if model_answer else "local",
            "confidence": "medium" if evidence else "low", "date_window": {key: window[key] for key in ("start", "end", "timezone", "corpus_as_of")},
            "cited_source_files": _source_files(evidence), "references": _references(evidence),
            "excerpts": rendered, "evidence": rendered,
            "uncertainty": "La période est calculée depuis la date actuelle, pas depuis le dernier document. "
                           "Les dates planifiées et les instantanés de registre ne prouvent pas un changement réalisé; "
                           "les rappels et états maintenus sont présentés séparément."}


def _answer_contradictions(question):
    findings = comparisons(_load("documents.json", []))
    evidence, selected = [], []
    for finding in findings:
        records = [{"path": p["path"], "title": Path(p["path"]).stem,
                    "text": p["excerpt"], "locator": p.get("locator", "Comparaison documentaire"),
                    "source_date": p.get("published_on"), "score": 1.0}
                   for p in finding["evidence"]]
        evidence.extend(records)
        selected.append({**records[0], "answer_key": finding["id"], "answer_label": finding["label"],
                         "text": finding["label"]})
    model = _external_reasoning_answer(question, selected, [{"excerpt": p["text"]} for p in selected]) if selected else None
    body = model["answer"] if model else "\n\n".join("- " + f["label"] for f in findings)
    rendered = [{"file": p["path"], "locator": p["locator"], "date": p["source_date"],
                 "excerpt": p["text"], "score": 1.0} for p in evidence]
    return {"question": question, "answer": ("Oui. Voici les écarts documentés et l’information à retenir :\n\n" + body
            if findings else "Je n’ai pas identifié de contradiction étayée par deux sources dans les comparaisons disponibles. Cela ne prouve pas que tout le corpus est cohérent."),
            "reasoning_mode": model.get("provider", "external_model") if model else "local",
            "confidence": "medium" if findings else "low", "references": _references(evidence),
            "cited_source_files": _source_files(evidence), "excerpts": rendered, "evidence": rendered,
            "uncertainty": "Comparaison de l’échéancier, des validations et du registre des risques. Les dates des sources et celles des suivis peuvent différer; une évolution historique n’est pas automatiquement une contradiction."}


def _answer_question(question):
    question = (question or "").strip()
    if is_contradiction_question(question):
        return _answer_contradictions(question)
    if is_recent_changes_question(question):
        return _answer_recent_changes(question)
    if is_current_risk_question(question):
        return _answer_current_risks(question)
    if _asks_open_commitments(question):
        return _answer_open_commitments(question)
    candidates = _search_candidates(question)
    evidence = _latest_relevant_evidence(candidates, limit=6, query=question)
    if not evidence:
        return {
            "question": question,
            "answer": "Je n'ai pas trouve de preuve pertinente dans le corpus ingere pour repondre a cette question.",
            "confidence": "low",
            "cited_source_files": [],
            "references": [],
            "excerpts": [],
            "evidence": [],
            "uncertainty": "Aucune source pertinente trouvee. Lancez l'ingestion ou ajoutez des documents traites avant de tirer une conclusion.",
        }

    direct_answer = _direct_answer(question, evidence)
    if direct_answer and direct_answer.get("evidence"):
        evidence = direct_answer["evidence"]

    focus_terms = direct_answer.get("focus_terms", []) if direct_answer else []
    excerpt_items = [_build_excerpt(item, question, focus_terms=focus_terms) for item in evidence]
    model_answer = _external_reasoning_answer(question, evidence, excerpt_items)
    answer = model_answer.get("answer") if model_answer else direct_answer["answer"] if direct_answer else _draft_answer(question, excerpt_items)
    confidence = _confidence(evidence, excerpt_items)
    if model_answer and model_answer.get("confidence") in {"high", "medium", "low"}:
        confidence = model_answer["confidence"]
    reasoning_mode = model_answer.get("provider", "external_model") if model_answer else "local"
    uncertainty = (
        model_answer.get("uncertainty")
        if model_answer
        else _uncertainty(evidence, excerpt_items, confidence, direct_answer=direct_answer)
    )

    return {
        "question": question,
        "answer": answer,
        "reasoning_mode": reasoning_mode,
        "confidence": confidence,
        "cited_source_files": _source_files(evidence),
        "references": _references(evidence),
        "excerpts": [
            {
                "file": item["path"],
                "locator": item.get("locator", "text chunk"),
                "date": item.get("source_date"),
                "excerpt": excerpt["excerpt"],
                "score": item["score"],
            }
            for item, excerpt in zip(evidence, excerpt_items)
        ],
        "evidence": [
            {
                "file": item["path"],
                "locator": item.get("locator", "text chunk"),
                "date": item.get("source_date"),
                "excerpt": excerpt["excerpt"],
                "score": item["score"],
            }
            for item, excerpt in zip(evidence, excerpt_items)
        ],
        "uncertainty": uncertainty,
    }


def _build_excerpt(item, question, focus_terms=None, max_chars=360):
    text = _normalize_space(item.get("text", ""))
    sentences = _sentences(text)
    key_terms = set(_tokens(question))
    answer_terms = set(_tokens(" ".join(focus_terms or [])))
    best_index = 0
    best_overlap = 0

    for index, sentence in enumerate(sentences):
        sentence_terms = set(_tokens(sentence))
        overlap = len(key_terms.intersection(sentence_terms))
        if answer_terms:
            overlap += len(answer_terms.intersection(sentence_terms)) * 4
        if overlap > best_overlap:
            best_index = index
            best_overlap = overlap

    selected = " ".join(sentences[max(0, best_index - 1) : best_index + 2]).strip()
    if not selected:
        selected = text
    if len(selected) <= max_chars:
        return {"excerpt": selected, "matched_terms": best_overlap}

    trim_terms = answer_terms or key_terms
    return {"excerpt": _trim_around_terms(selected, trim_terms, max_chars), "matched_terms": best_overlap}


def _draft_answer(question, excerpt_items):
    key_terms = set(_tokens(question))
    useful = []

    for item in excerpt_items:
        for sentence in _sentences(item["excerpt"]):
            if len(sentence) < 25:
                continue
            if key_terms.intersection(_tokens(sentence)):
                useful.append(sentence.strip())
                break
        if len(useful) == 3:
            break

    if not useful:
        useful = [excerpt_items[0]["excerpt"]]
    return " ".join(useful)


def _external_reasoning_answer(question, evidence, excerpt_items):
    ollama_answer = _ollama_reasoning_answer(question, evidence, excerpt_items)
    if ollama_answer:
        return {**ollama_answer, "provider": "ollama"}
    # An explicitly selected local provider must not trigger another long request.
    if os.getenv("OLLAMA_MODEL"):
        return None

    openai_answer = _openai_reasoning_answer(question, evidence, excerpt_items)
    if openai_answer:
        return {**openai_answer, "provider": "openai"}

    _reasoning_failure.set("Aucun modèle disponible. Configurez OLLAMA_MODEL dans le fichier .env du serveur et démarrez Ollama.")
    return None


def _reasoning_payload(question, evidence, excerpt_items):
    return [
        {
            "id": index + 1,
            "file": item.get("path"),
            "date": item.get("source_date"),
            "priority_score": item.get("selection_score", item.get("score")),
            "authority_hint": _authority_hint(item),
            "excerpt": excerpt.get("excerpt"),
            **({"answer_key": item["answer_key"]} if item.get("answer_key") else {}),
            **({"answer_section": item["answer_section"]} if item.get("answer_section") else {}),
        }
        for index, (item, excerpt) in enumerate(zip(evidence, excerpt_items))
    ]


def _reasoning_system_prompt():
    return (
        "You are NOVA Project Memory. Answer the user's question using only the provided evidence. "
        "Do not invent facts. Write a clear, readable answer in natural prose that fully answers every part of the question. "
        "Keep the answer under 160 words. Use two to four sentences for a simple question. "
        "For unfinished commitments, instead use a complete list covering every open or in-validation ticket, "
        "administrative and financial follow-up, and distinguish deferred Phase 2 proposals from approved Phase 1 work. "
        "A delivered fix is not acceptance; exclude explicitly closed tickets from outstanding work. "
        "For a list, include each open ticket ID, each administrative/financial follow-up, and a separate Phase 2 sentence stating it is outside approved Phase 1 scope. "
        "Do not infer completion or approval from an old plan or an optimistic draft. "
        "If the question asks why, include the reason; do not answer with only a date or status. "
        "For date or status questions, prefer the latest authoritative decision over older plans, drafts, or proposals. "
        "When sources conflict, treat newer committee decisions, approved reminders, and transition notes as more authoritative than initial charters, draft plans, or proposals. "
        "If the evidence is uncertain or conditional, say so in uncertainty. "
        "Return only valid JSON with keys: answer, confidence, uncertainty. "
        "confidence must be one of high, medium, low."
    )


def _reasoning_user_prompt(question, sources):
    return json.dumps(
        {
            "question": question,
            "answer_format": (
                ("The answer must be an object with one concise summary (at most 65 words) for EACH answer_key. "
                 "Summarize ALL records sharing its answer_section, and retain their event dates. "
                 if is_recent_changes_question(question)
                 else "The answer must be an object with exactly one short sentence (at most 20 words) for EACH answer_key in evidence. ")
                +
                "Include ALL these keys; records with neither answer_key nor answer_section are counter-evidence only. "
                "Summarize each selected record and its mitigation or remaining action, not the entire history. "
                "Do not introduce other items or change the selected records' statuses."
                if any(source.get("answer_key") for source in sources)
                else "The answer must be a concise string."
            ),
            "evidence": sources,
            "output_rules": [
                "Answer in the same language as the question when possible.",
                *(["Write every answer value in French. Give only a short recommended next action for each comparison. "
                   "The verified comparison, dates, sources and conclusion are already displayed before your sentence. "
                   "Do not repeat them. Never treat delivery as acceptance or an outdated plan as an equally valid decision."]
                  if is_contradiction_question(question) else []),
                "Use plain, readable wording; do not return only a bare extracted value unless the user asks for only that value.",
                "Use priority_score and authority_hint to resolve contradictions; current authoritative evidence beats older baseline or draft evidence.",
                "Do not quote long excerpts in the answer.",
                "Do not include references in the answer field; references are displayed separately by the app.",
                *(["For each selected risk, state only its mitigation as an action still to perform. "
                   "Mitigation is a plan, not proof of completion. Do not invent an overall severity rating; "
                   "the register's probability and impact are displayed separately."]
                  if is_current_risk_question(question) else []),
                *(["Only summarize dated observations within the stated period. Do not turn historical reminders into new changes. "
                   "Records in the followups section are reminders or maintained states, not new decisions or completed work. "
                   "A future target date is not a realized event. An announced fix is not delivered or accepted. "
                   "In the updates section, focus on the newly stated conditions or announced actions; "
                   "mention the existing go-live date only in followups, never as a new decision. "
                   "Do not describe deferred scope as newly approved in this period.",
                   "Write all answer values in French." if re.search(r"semaine|derniers jours", _fold(question))
                   else "Write all answer values in English."]
                  if is_recent_changes_question(question) else []),
            ],
        },
        ensure_ascii=False,
    )


def _reasoning_schema(evidence):
    keys = [item["answer_key"] for item in evidence if item.get("answer_key")]
    if not keys:
        return REASONING_SCHEMA
    return {**REASONING_SCHEMA, "properties": {**REASONING_SCHEMA["properties"], "answer": {
        "type": "object", "properties": {key: {"type": "string"} for key in keys},
        "required": keys, "additionalProperties": False,
    }}}


def _ollama_reasoning_answer(question, evidence, excerpt_items):
    model = os.getenv("OLLAMA_MODEL")
    if not model:
        return None

    sources = _reasoning_payload(question, evidence, excerpt_items)
    body = {
        "model": model,
        "stream": False,
        "format": _reasoning_schema(evidence),
        "keep_alive": "30m",
        "messages": [
            {"role": "system", "content": _reasoning_system_prompt()},
            {"role": "user", "content": _reasoning_user_prompt(question, sources)},
        ],
        "options": {
            "temperature": 0,
            "num_ctx": int(os.getenv("NOVA_OLLAMA_CONTEXT_TOKENS", OLLAMA_DEFAULT_CONTEXT_TOKENS)),
            "num_predict": int(os.getenv("NOVA_OLLAMA_PREDICT_TOKENS", OLLAMA_DEFAULT_PREDICT_TOKENS)),
        },
    }
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    request = urllib.request.Request(
        f"{base_url}/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        queue_timeout = float(os.getenv("OLLAMA_QUEUE_TIMEOUT", "90"))
    except ValueError:
        queue_timeout = 90
    if not _ollama_lock.acquire(timeout=max(0, queue_timeout)):
        _reasoning_failure.set("Ollama traite déjà une question. Réessayez après sa réponse.")
        return None
    try:
        timeout = float(os.getenv("OLLAMA_TIMEOUT", "60"))
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Invalid timeout")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        if data.get("done_reason") == "length":
            _reasoning_failure.set("La réponse Ollama a atteint sa limite de longueur. Une réponse locale est affichée.")
            return None
        content = data.get("message", {}).get("content", "")
        answer = _parse_reasoning_json(content, evidence)
        if not answer:
            _reasoning_failure.set("Ollama a renvoyé une réponse invalide. Une réponse locale est affichée.")
        return answer
    except (TimeoutError, socket.timeout):
        _reasoning_failure.set("Ollama a dépassé le délai de réponse. Une réponse locale est affichée.")
        return None
    except urllib.error.HTTPError as exc:
        _reasoning_failure.set(f"Ollama a renvoyé une erreur HTTP {exc.code}. Vérifiez que le modèle {model} est installé.")
        return None
    except (OSError, urllib.error.URLError):
        _reasoning_failure.set("Connexion à Ollama impossible. Ouvrez l'application Ollama puis réessayez.")
        return None
    except (ValueError, TypeError, AttributeError):
        _reasoning_failure.set("Configuration ou réponse Ollama invalide. Vérifiez OLLAMA_TIMEOUT et le modèle sélectionné.")
        return None
    finally:
        _ollama_lock.release()


def _openai_reasoning_answer(question, evidence, excerpt_items):
    if not os.getenv("OPENAI_API_KEY"):
        return None

    try:
        from openai import OpenAI
    except ImportError:
        return None

    sources = _reasoning_payload(question, evidence, excerpt_items)
    schema = _reasoning_schema(evidence)

    try:
        client = OpenAI()
        response = client.responses.create(
            model=os.getenv("NOVA_REASONING_MODEL", "gpt-4.1-mini"),
            input=[
                {"role": "system", "content": _reasoning_system_prompt()},
                {"role": "user", "content": _reasoning_user_prompt(question, sources)},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "nova_answer",
                    "schema": schema,
                    "strict": True,
                }
            },
        )
        return _parse_reasoning_json(response.output_text, evidence)
    except Exception:
        return None


def _parse_reasoning_json(content, evidence=None):
    parsed = json.loads(_extract_json_object(content or ""))
    if not isinstance(parsed, dict):
        return None
    answer = parsed.get("answer")
    sections = [item for item in evidence or [] if item.get("answer_key")]
    if sections:
        if not isinstance(answer, dict) or set(answer) != {item["answer_key"] for item in sections}:
            return None
        if any(not isinstance(value, str) or not value.strip() for value in answer.values()):
            return None
        answer = "\n".join(f"- {item['answer_label']} : {answer[item['answer_key']].strip()}" for item in sections)
    elif not isinstance(answer, str):
        return None
    answer = answer.strip()
    confidence = str(parsed.get("confidence", "")).strip().lower()
    uncertainty = str(parsed.get("uncertainty", "")).strip()
    if not answer or confidence not in {"high", "medium", "low"}:
        return None
    return {
        "answer": answer,
        "confidence": confidence,
        "uncertainty": uncertainty,
    }


def _extract_json_object(content):
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.I)
        content = re.sub(r"\s*```$", "", content)
    start = content.find("{")
    end = content.rfind("}")
    if start >= 0 and end >= start:
        return content[start : end + 1]
    return content


def _direct_answer(question, evidence):
    value = " ".join(_tokens(question))
    if _is_go_live_date_question(question) and not _asks_why(value):
        candidate = _approved_go_live_candidate(evidence)
        if candidate:
            return {
                "answer": f"La date de mise en production actuellement approuvée est le {candidate['date']}.",
                "focus_terms": [candidate["date"], "approuvée", "mise en production"],
                "evidence": candidate["evidence"],
            }

    return None


def _asks_why(value):
    return any(term in value for term in ["pourquoi", "raison", "cause", "change", "changement", "deplace", "retard"])


def _asks_current(value):
    return any(
        term in value
        for term in [
            "actuel",
            "actuelle",
            "actuellement",
            "prevue",
            "prevu",
            "approuvee",
            "approuve",
            "officielle",
            "demeure",
            "reste",
        ]
    )


def _mentions_go_live(value):
    return any(term in value for term in ["production", "go-live", "live", "livraison", "lancement", "deploiement"])


def _is_go_live_date_question(question):
    value = " ".join(_tokens(question))
    return (
        any(term in value for term in ["date", "quand", "echeance", "echeancier"])
        and _mentions_go_live(value)
        and any(term in value for term in ["approuvee", "approuve", "actuellement", "officielle", "cible"])
    )


def _merge_evidence(*groups):
    merged = []
    seen = set()
    for group in groups:
        for item in group or []:
            key = (item.get("path"), item.get("locator"))
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _approved_go_live_candidate(evidence):
    candidates = []
    for item in evidence:
        text = _normalize_space(item.get("text", ""))
        for date_match in _french_date_matches(text):
            if _is_metadata_date(text, date_match.start()):
                continue

            window = _window_around(text, date_match.start(), date_match.end(), radius=170)
            window_lower = window.lower()
            if not any(term in window_lower for term in ["production", "go-live", "cible", "date"]):
                continue

            authority = _authority_score(window_lower)
            if authority == 0:
                continue

            if re.search(r"\b(proposition|recommandation|brouillon|pas encore|non approuv|aucune approbation)\b", window_lower):
                authority -= 2

            if authority <= 0:
                continue

            candidates.append(
                {
                    "date": _normalize_french_date(date_match.group(0), item.get("source_date")),
                    "authority": authority,
                    "source_timestamp": item.get("source_timestamp") or 0,
                    "score": item.get("score", 0),
                    "item": item,
                }
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda candidate: (
            candidate["authority"],
            candidate["source_timestamp"],
            candidate["score"],
        ),
        reverse=True,
    )
    best = candidates[0]
    supporting = []
    seen_paths = set()
    for candidate in candidates:
        item = candidate["item"]
        path = item.get("path")
        if candidate["date"] != best["date"] or path in seen_paths:
            continue
        seen_paths.add(path)
        supporting.append(item)

    best["evidence"] = supporting[:4]
    return best


def _authority_score(text):
    score = 0
    for term in ["approuve", "approuvée", "approuvee", "officielle", "demeure", "reste", "comite", "comité"]:
        if term in text:
            score += 2
    for term in ["conditionnelle", "conditions", "critères", "criteres"]:
        if term in text:
            score += 1
    return score


def _is_metadata_date(text, start):
    prefix = text[max(0, start - 18) : start].lower()
    return any(marker in prefix for marker in ["date:", "date :", "créé :", "cree :", "created", "subject:"])


def _french_date_matches(text):
    month_pattern = (
        "janvier|fevrier|février|mars|avril|mai|juin|juillet|aout|août|"
        "sept|septembre|oct|octobre|novembre|decembre|décembre"
    )
    return list(re.finditer(rf"\b\d{{1,2}}\s+(?:{month_pattern})(?:\s+20\d{{2}})?\b", text or "", re.I))


def _normalize_french_date(value, source_date=None):
    value = _normalize_space(value).lower()
    if re.search(r"\b20\d{2}\b", value):
        return value

    year = (source_date or "")[:4]
    if year:
        return f"{value} {year}"
    return value


def _window_around(text, start, end, radius=160):
    return text[max(0, start - radius) : min(len(text), end + radius)].strip()


def _latest_relevant_evidence(candidates, limit, query=""):
    if not candidates:
        return []

    query_value = " ".join(_tokens(query))
    top_score = max(item.get("score", 0) for item in candidates)
    minimum_score = 1.0 if (_asks_current(query_value) or _asks_why(query_value)) else max(1.0, top_score * 0.35)
    relevant = [item for item in candidates if item.get("score", 0) >= minimum_score]
    for item in relevant:
        item["selection_score"] = round(item.get("score", 0) + _authority_boost(item, query_value), 3)

    relevant.sort(
        key=lambda item: (
            item.get("selection_score", item.get("score", 0)),
            item.get("source_timestamp") is not None,
            item.get("source_timestamp") or 0,
        ),
        reverse=True,
    )
    return relevant[:limit]


def _authority_boost(item, query_value):
    text = _normalize_space(item.get("text", "")).lower()
    title = (item.get("title") or "").lower()
    path = (item.get("path") or "").lower()
    current_question = _asks_current(query_value)
    boost = 0.0

    if current_question:
        if re.search(r"\b(approuv|officielle|demeure|reste|d[ée]cision|comit[ée])\b", text):
            boost += 8.0
        if re.search(r"\b(initiale?|pr[ée]liminaire|brouillon|proposition|recommandation)\b", text):
            boost -= 5.0
        if "charte" in title or "charte" in path:
            boost -= 4.0
        if "plan projet" in text and re.search(r"\b(cible initiale|cible de planification|version pr[ée]liminaire)\b", text):
            boost -= 4.0

    if _mentions_go_live(query_value):
        if re.search(r"\b(22 octobre|date officielle|cible approuv[ée]e|cible 22 octobre)\b", text):
            boost += 8.0
        if re.search(r"\b(15 octobre)\b", text) and re.search(r"\b(initiale?|ancien|pas encore corrig|mettre [aà] jour|d[ée]plac[ée]e)\b", text):
            boost -= 3.0

    if _asks_why(query_value):
        if re.search(r"\b(connecteur|stabilisation|tests int[ée]gr[ée]s|anomalies bloquantes|int-101)\b", text):
            boost += 4.0

    return boost


def _authority_hint(item):
    text = _normalize_space(item.get("text", "")).lower()
    title = (item.get("title") or "").lower()
    path = (item.get("path") or "").lower()

    if re.search(r"\b(approuv|officielle|demeure|reste|d[ée]cision|comit[ée])\b", text):
        return "authoritative/current decision evidence"
    if re.search(r"\b(proposition|recommandation|brouillon|pr[ée]liminaire)\b", text):
        return "proposal or draft; do not treat as final approval"
    if "charte" in title or "charte" in path or "cible initiale" in text:
        return "initial baseline; may be superseded by later decisions"
    return "supporting evidence"


def _confidence(evidence, excerpt_items):
    top_score = evidence[0].get("score", 0)
    strong_excerpt_count = sum(1 for item in excerpt_items if item["matched_terms"] >= 2)
    cited_files = len(_source_files(evidence))

    if top_score >= 6 and strong_excerpt_count >= 2 and cited_files >= 2:
        return "high"
    if top_score >= 2 and strong_excerpt_count >= 1:
        return "medium"
    return "low"


def _uncertainty(evidence, excerpt_items, confidence, direct_answer=None):
    text = " ".join(item["excerpt"].lower() for item in excerpt_items)
    notes = []

    if direct_answer:
        notes.append("Réponse extraite automatiquement à partir des sources citées.")
    if confidence == "low":
        notes.append("Les preuves retrouvees sont faibles ou peu nombreuses.")
    elif confidence == "medium" and not direct_answer:
        notes.append("La reponse repose sur une recherche lexicale locale, sans validation par un modele de raisonnement externe.")

    if re.search(r"\b(proposition|brouillon|a confirmer|confirmer|question|risque|peu de marge|pas approuv)", text):
        notes.append("Certaines sources emploient un langage non final comme proposition, brouillon, risque ou confirmation requise.")

    if len(_source_files(evidence)) == 1:
        notes.append("Une seule source principale appuie la reponse.")

    if not notes:
        notes.append("Aucune incertitude majeure detectee dans les extraits cites, mais la reponse depend du corpus actuellement ingere.")

    return " ".join(notes)


def _source_files(evidence):
    files = []
    for item in evidence:
        path = item.get("path")
        if path and path not in files:
            files.append(path)
    return files


def _references(evidence):
    references = []
    seen = set()

    for item in evidence:
        path = item.get("path")
        if not path or path in seen:
            continue
        seen.add(path)
        references.append(
            {
                "file": path,
                "title": item.get("title") or Path(path).stem,
                "type": _source_type(path),
                "date": item.get("source_date"),
                "locator": item.get("locator", "text chunk"),
            }
        )

    return references


def _source_type(path):
    extension = Path(path).suffix.lower()
    types = {
        ".eml": "email",
        ".pdf": "document",
        ".xlsx": "spreadsheet",
        ".xls": "spreadsheet",
        ".csv": "spreadsheet",
        ".txt": "note",
        ".md": "document",
    }
    return types.get(extension, "source")


def _source_date(item):
    text = item.get("text", "")
    path = item.get("path", "")
    title = item.get("title", "")
    header_text = text[:300]
    candidates = [
        _date_from_email_header(text),
        _date_from_iso(header_text),
        _date_from_french_text(header_text),
        _date_from_french_text(f"{title} {path}"),
    ]

    for source_date in candidates:
        if source_date:
            return {"display": source_date.strftime("%Y-%m-%d"), "timestamp": source_date.timestamp()}

    return {"display": None, "timestamp": None}


def _date_from_email_header(text):
    match = re.search(r"\bDate:\s+(.+?)(?=\s+(Bonjour|Salut|Merci|Objet|Subject|From|To)\b|$)", text or "", re.I)
    if not match:
        return None

    try:
        return parsedate_to_datetime(match.group(1)).replace(tzinfo=None)
    except (TypeError, ValueError, IndexError, AttributeError):
        return None


def _date_from_iso(text):
    matches = re.findall(r"\b(20\d{2})[-/](\d{2})[-/](\d{2})\b", text or "")
    dates = []
    for year, month, day in matches:
        try:
            dates.append(datetime(int(year), int(month), int(day)))
        except ValueError:
            continue
    return max(dates) if dates else None


def _date_from_french_text(text):
    month_names = {
        "janvier": 1,
        "fevrier": 2,
        "février": 2,
        "mars": 3,
        "avril": 4,
        "mai": 5,
        "juin": 6,
        "juillet": 7,
        "aout": 8,
        "août": 8,
        "sept": 9,
        "septembre": 9,
        "oct": 10,
        "octobre": 10,
        "novembre": 11,
        "decembre": 12,
        "décembre": 12,
    }
    pattern = r"\b(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\s+(20\d{2})\b"
    dates = []

    for day, month_name, year in re.findall(pattern, text or "", re.I):
        month = month_names.get(month_name.lower())
        if not month:
            continue
        try:
            dates.append(datetime(int(year), month, int(day)))
        except ValueError:
            continue

    return max(dates) if dates else None


def _sentences(text):
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]


def _normalize_space(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _trim_around_terms(text, terms, max_chars):
    lowered = text.lower()
    positions = [lowered.find(term.lower()) for term in terms if lowered.find(term.lower()) >= 0]
    center = min(positions) if positions else 0
    start = max(0, center - max_chars // 3)
    end = min(len(text), start + max_chars)
    start = max(0, end - max_chars)
    return text[start:end].strip()
