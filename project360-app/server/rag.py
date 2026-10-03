import json
import math
import re
from collections import Counter
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
            ranked.append({**chunk, "score": round(score, 3)})
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:limit]


def answer_question(question):
    evidence = search_documents(question, limit=5)
    if not evidence:
        return {
            "answer": "Je n'ai pas encore trouve de preuve dans le corpus ingere. Lancez l'ingestion ou ajoutez des documents traites.",
            "confidence": "low",
            "evidence": [],
            "uncertainty": "Aucune source pertinente trouvee.",
        }

    joined = " ".join(item["text"] for item in evidence[:3])
    answer = _draft_answer(question, joined)
    return {
        "answer": answer,
        "confidence": "medium",
        "evidence": [
            {
                "file": item["path"],
                "locator": item.get("locator", "text chunk"),
                "excerpt": item["text"][:450],
                "score": item["score"],
            }
            for item in evidence
        ],
        "uncertainty": "Starter local retrieval only. Replace with an LLM call for stronger synthesis once the evidence set is finalized.",
    }


def _draft_answer(question, text):
    sentences = re.split(r"(?<=[.!?])\s+", text)
    key_terms = set(_tokens(question))
    useful = []
    for sentence in sentences:
        if len(sentence) < 25:
            continue
        overlap = key_terms.intersection(_tokens(sentence))
        if overlap:
            useful.append(sentence.strip())
        if len(useful) == 3:
            break
    if not useful:
        useful = [text[:600]]
    return " ".join(useful)

