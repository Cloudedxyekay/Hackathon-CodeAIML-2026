import json
import math
import os
import re
import socket
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


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


def answer_question(question):
    question = (question or "").strip()
    candidates = search_documents(question, limit=14)
    evidence = _latest_relevant_evidence(candidates, limit=6)
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

    openai_answer = _openai_reasoning_answer(question, evidence, excerpt_items)
    if openai_answer:
        return {**openai_answer, "provider": "openai"}

    return None


def _reasoning_payload(question, evidence, excerpt_items):
    return [
        {
            "id": index + 1,
            "file": item.get("path"),
            "title": item.get("title"),
            "type": _source_type(item.get("path", "")),
            "date": item.get("source_date"),
            "locator": item.get("locator", "text chunk"),
            "excerpt": excerpt.get("excerpt"),
        }
        for index, (item, excerpt) in enumerate(zip(evidence, excerpt_items))
    ]


def _reasoning_system_prompt():
    return (
        "You are NOVA Project Memory. Answer the user's question using only the provided evidence. "
        "Do not invent facts. Return the shortest answer that fully answers the question. "
        "For date or status questions, prefer the latest authoritative decision over older plans, drafts, or proposals. "
        "If the evidence is uncertain or conditional, say so in uncertainty. "
        "Return only valid JSON with keys: answer, confidence, uncertainty. "
        "confidence must be one of high, medium, low."
    )


def _reasoning_user_prompt(question, sources):
    return json.dumps(
        {
            "question": question,
            "evidence": sources,
            "output_rules": [
                "Answer in the same language as the question when possible.",
                "Do not quote long excerpts in the answer.",
                "Do not include references in the answer field; references are displayed separately by the app.",
            ],
        },
        ensure_ascii=False,
    )


def _ollama_reasoning_answer(question, evidence, excerpt_items):
    model = os.getenv("OLLAMA_MODEL")
    if not model:
        return None

    sources = _reasoning_payload(question, evidence, excerpt_items)
    body = {
        "model": model,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": _reasoning_system_prompt()},
            {"role": "user", "content": _reasoning_user_prompt(question, sources)},
        ],
        "options": {
            "temperature": 0,
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
        timeout = float(os.getenv("OLLAMA_TIMEOUT", "120"))
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = data.get("message", {}).get("content", "")
        return _parse_reasoning_json(content)
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError, socket.timeout):
        return None


def _openai_reasoning_answer(question, evidence, excerpt_items):
    if not os.getenv("OPENAI_API_KEY"):
        return None

    try:
        from openai import OpenAI
    except ImportError:
        return None

    sources = _reasoning_payload(question, evidence, excerpt_items)
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "answer": {"type": "string"},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "uncertainty": {"type": "string"},
        },
        "required": ["answer", "confidence", "uncertainty"],
    }

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
        return _parse_reasoning_json(response.output_text)
    except Exception:
        return None


def _parse_reasoning_json(content):
    parsed = json.loads(_extract_json_object(content or ""))
    if not isinstance(parsed, dict):
        return None
    answer = str(parsed.get("answer", "")).strip()
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
    if _is_go_live_date_question(question):
        candidate = _approved_go_live_candidate(evidence)
        if candidate:
            return {
                "answer": f"La date de mise en production actuellement approuvée est le {candidate['date']}.",
                "focus_terms": [candidate["date"], "approuvée", "mise en production"],
                "evidence": candidate["evidence"],
            }

    return None


def _is_go_live_date_question(question):
    value = " ".join(_tokens(question))
    return (
        any(term in value for term in ["date", "quand", "echeance", "echeancier"])
        and any(term in value for term in ["production", "go-live", "live"])
        and any(term in value for term in ["approuvee", "approuve", "actuellement", "officielle", "cible"])
    )


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


def _latest_relevant_evidence(candidates, limit):
    if not candidates:
        return []

    top_score = candidates[0].get("score", 0)
    minimum_score = max(1.0, top_score * 0.35)
    relevant = [item for item in candidates if item.get("score", 0) >= minimum_score]
    relevant.sort(
        key=lambda item: (
            item.get("source_timestamp") is not None,
            item.get("source_timestamp") or 0,
            item.get("score", 0),
        ),
        reverse=True,
    )
    return relevant[:limit]


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
