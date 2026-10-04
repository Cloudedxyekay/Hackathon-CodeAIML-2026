import json
import re
import hashlib
import os
from threading import RLock
from uuid import uuid4
from pathlib import Path

from .extractors.read_eml import read_eml
from .extractors.read_pdf import read_pdf
from .extractors.read_txt import read_txt
from .extractors.read_xlsx import read_xlsx
from .extractors.read_image import read_image

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
DEFAULT_CORPUS = REPO_ROOT / "project 360 data" / "NOVA_ETUDIANTS"
PROCESSED = ROOT / "data" / "processed"
INGEST_LOCK = RLock()


READERS = {
    ".txt": read_txt,
    ".md": read_txt,
    ".csv": read_txt,
    ".eml": read_eml,
    ".pdf": read_pdf,
    ".xlsx": read_xlsx,
    ".png": read_image,
    ".jpg": read_image,
    ".jpeg": read_image,
    ".webp": read_image,
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


def extract_source(path):
    try:
        text = READERS[path.suffix.lower()](path)
        return text, [] if text.strip() else ["Aucun texte lisible. Ajoutez une transcription avant l'intégration."]
    except Exception as exc:
        return "", [f"Extraction impossible ({type(exc).__name__}). Ajoutez une transcription ou vérifiez le fichier."]


def build_corpus(corpus, existing_documents=None):
    corpus = Path(corpus)
    existing = {doc["path"]: doc for doc in existing_documents or []}
    documents = []
    chunks = []
    if not corpus.exists():
        raise ValueError(f"Corpus introuvable : {corpus}")

    for path in sorted(corpus.rglob("*")):
        if not path.is_file() or path.is_symlink() or path.name.startswith((".", "~$")):
            continue
        reader = READERS.get(path.suffix.lower())
        if not reader:
            continue
        rel = path.relative_to(corpus).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        metadata_path = path.with_name(path.name + ".nova.json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
        prior = existing.get(rel, {})
        if metadata.get("content_sha256") == digest and "reviewed_text" in metadata:
            text, warnings = metadata["reviewed_text"], metadata.get("warnings", [])
        elif prior.get("content_sha256") == digest:
            text, warnings = prior["text"], prior.get("extraction_warnings", [])
        else:
            text, warnings = extract_source(path)
        tags = infer_tags(rel, text)
        doc = {
            "id": prior.get("id") or "doc-" + hashlib.sha256(rel.encode()).hexdigest()[:16],
            "path": rel,
            "title": Path(metadata.get("original_name", path.name)).stem.replace("_", " "),
            "extension": path.suffix.lower(),
            "tags": tags,
            "summary": normalize_space(text)[:260],
            "text": text,
            "content_sha256": digest,
            "extraction_warnings": warnings,
            **{key: metadata[key] for key in ("imported_at", "source_date_override", "original_name", "text_reviewed") if metadata.get(key)},
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

    from .intelligence import build_project_memory
    memory = build_project_memory(documents)
    return documents, chunks, memory


def publish_corpus(documents, chunks, memory, processed=None):
    """Publish complete JSON files; restore the previous set if publication fails."""
    destination = Path(processed) if processed else PROCESSED
    destination.mkdir(parents=True, exist_ok=True)
    values = {"documents.json": documents, "chunks.json": chunks,
              "project_memory.json": memory, "timeline.json": memory["events"]}
    previous = {name: (destination / name).read_bytes() if (destination / name).exists() else None for name in values}
    staged = []
    try:
        for name, value in values.items():
            temporary = destination / f".{name}.{uuid4().hex}.tmp"
            temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
            staged.append((temporary, destination / name))
        for temporary, target in staged:
            os.replace(temporary, target)
    except Exception:
        for name, content in previous.items():
            target = destination / name
            if content is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(content)
        raise
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)


def ingest_corpus(corpus_path=None, processed_path=None):
    corpus = Path(corpus_path) if corpus_path else DEFAULT_CORPUS
    destination = Path(processed_path) if processed_path else PROCESSED
    with INGEST_LOCK:
        previous = destination / "documents.json"
        existing = json.loads(previous.read_text(encoding="utf-8")) if previous.exists() else []
        documents, chunks, memory = build_corpus(corpus, existing)
        publish_corpus(documents, chunks, memory, destination)
    return {"ok": True, "documents": len(documents), "chunks": len(chunks),
            "events": len(memory["events"]), "decisions": memory["stats"]["decisions"],
            "warnings": [{"path": doc["path"], "messages": doc["extraction_warnings"]}
                         for doc in documents if doc["extraction_warnings"]]}


if __name__ == "__main__":
    print(json.dumps(ingest_corpus(), indent=2))
