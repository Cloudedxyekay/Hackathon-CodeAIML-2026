import json
import math
import re
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

    excerpt_items = [_build_excerpt(item, question) for item in evidence]
    answer = _draft_answer(question, excerpt_items)
    confidence = _confidence(evidence, excerpt_items)
    uncertainty = _uncertainty(evidence, excerpt_items, confidence)

    return {
        "question": question,
        "answer": answer,
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


def _build_excerpt(item, question, max_chars=520):
    text = _normalize_space(item.get("text", ""))
    sentences = _sentences(text)
    key_terms = set(_tokens(question))
    best_index = 0
    best_overlap = 0

    for index, sentence in enumerate(sentences):
        overlap = len(key_terms.intersection(_tokens(sentence)))
        if overlap > best_overlap:
            best_index = index
            best_overlap = overlap

    selected = " ".join(sentences[max(0, best_index - 1) : best_index + 2]).strip()
    if not selected:
        selected = text
    if len(selected) <= max_chars:
        return {"excerpt": selected, "matched_terms": best_overlap}

    return {"excerpt": _trim_around_terms(selected, key_terms, max_chars), "matched_terms": best_overlap}


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


def _uncertainty(evidence, excerpt_items, confidence):
    text = " ".join(item["excerpt"].lower() for item in excerpt_items)
    notes = []

    if confidence == "low":
        notes.append("Les preuves retrouvees sont faibles ou peu nombreuses.")
    elif confidence == "medium":
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
