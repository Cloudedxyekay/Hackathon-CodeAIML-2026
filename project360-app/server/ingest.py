import json
import re
from pathlib import Path

from .extractors.read_eml import read_eml
from .extractors.read_pdf import read_pdf
from .extractors.read_txt import read_txt
from .extractors.read_xlsx import read_xlsx

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
DEFAULT_CORPUS = REPO_ROOT / "project 360 data" / "NOVA_ETUDIANTS"
PROCESSED = ROOT / "data" / "processed"


READERS = {
    ".txt": read_txt,
    ".md": read_txt,
    ".csv": read_txt,
    ".eml": read_eml,
    ".pdf": read_pdf,
    ".xlsx": read_xlsx,
}


def normalize_space(text):
    return re.sub(r"\s+", " ", text or "").strip()


def chunk_text(text, size=1200, overlap=160):
    text = normalize_space(text)
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += max(1, size - overlap)
    return chunks


def infer_tags(path, text):
    value = f"{path} {text}".lower()
    tags = []
    for tag, terms in {
        "go-live": ["mise en production", "go-live", "production"],
        "invoice": ["facture", "inv-", "invoice"],
        "security": ["securite", "sécurité", "audit", "journalisation"],
        "accessibility": ["accessibilite", "accessibilité", "contraste", "focus", "labels"],
        "risk": ["risque", "bloquant", "retard"],
        "architecture": ["architecture", "canada central", "hebergement", "hébergement"],
        "change-request": ["cr-", "demande de changement"],
    }.items():
        if any(term in value for term in terms):
            tags.append(tag)
    return tags


def ingest_corpus(corpus_path=None):
    corpus = Path(corpus_path) if corpus_path else DEFAULT_CORPUS
    PROCESSED.mkdir(parents=True, exist_ok=True)

    documents = []
    chunks = []

    if not corpus.exists():
        return {
            "ok": False,
            "message": f"Corpus not found: {corpus}",
            "documents": 0,
            "chunks": 0,
        }

    for path in sorted(corpus.rglob("*")):
        if not path.is_file():
            continue
        reader = READERS.get(path.suffix.lower())
        if not reader:
            continue
        rel = path.relative_to(corpus).as_posix()
        try:
            text = reader(path)
        except Exception as exc:
            text = f"Extraction failed: {exc}"
        tags = infer_tags(rel, text)
        doc = {
            "id": f"doc-{len(documents) + 1:03d}",
            "path": rel,
            "title": path.stem.replace("_", " "),
            "extension": path.suffix.lower(),
            "tags": tags,
            "summary": normalize_space(text)[:260],
            "text": text,
        }
        documents.append(doc)
        for index, chunk in enumerate(chunk_text(text)):
            chunks.append(
                {
                    "id": f"{doc['id']}-chunk-{index + 1:03d}",
                    "document_id": doc["id"],
                    "path": rel,
                    "title": doc["title"],
                    "tags": tags,
                    "locator": f"chunk {index + 1}",
                    "text": chunk,
                }
            )

    (PROCESSED / "documents.json").write_text(
        json.dumps(documents, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (PROCESSED / "chunks.json").write_text(
        json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (PROCESSED / "embeddings.json").write_text(
        json.dumps(
            {
                "mode": "lexical-starter",
                "note": "Replace this file with vector embeddings when adding a model provider.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    from .intelligence import build_project_memory, save_project_memory

    memory = build_project_memory(documents)
    save_project_memory(memory)
    return {"ok": True, "documents": len(documents), "chunks": len(chunks),
            "events": len(memory["events"]), "decisions": memory["stats"]["decisions"]}


if __name__ == "__main__":
    print(json.dumps(ingest_corpus(), indent=2))

