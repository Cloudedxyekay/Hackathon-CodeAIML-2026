from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from .rag import answer_question, reasoning_status, search_documents
from .ingest import ingest_corpus, DEFAULT_CORPUS
from .prompts import build_update_analysis, generate_executive_brief
from .intelligence import get_project_memory
from .ai_extraction import attach_enrichment, enrich, EnrichmentError

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
PROCESSED = ROOT / "data" / "processed"

app = FastAPI(title="NOVA Project Memory API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str


class SearchRequest(BaseModel):
    query: str
    limit: int = 8


class UpdateRequest(BaseModel):
    event_text: str


def read_json(name: str, fallback: Any):
    path = PROCESSED / name
    if not path.exists():
        return fallback
    import json

    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/health")
def health():
    return {"ok": True, "service": "nova-project-memory"}


@app.get("/api/reasoning-status")
def reasoning():
    return reasoning_status()


@app.post("/api/ingest")
def ingest():
    result = ingest_corpus()
    return result


@app.get("/api/dashboard")
def dashboard():
    return {
        "baseline": read_json("baseline.json", {}),
        "timeline": read_json("timeline.json", []),
        "actions": read_json("actions.json", []),
        "documents": read_json("documents.json", []),
        "answers": read_json("answers.json", []),
        "memory": attach_enrichment(get_project_memory()),
    }


@app.get("/api/answers")
def answers():
    return read_json("answers.json", [])


@app.get("/api/timeline")
def timeline():
    return get_project_memory()["events"]


@app.get("/api/project-memory")
def project_memory():
    return attach_enrichment(get_project_memory())


@app.post("/api/project-memory/enrich")
def enrich_project_memory():
    try:
        return enrich(get_project_memory())
    except EnrichmentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


@app.get("/api/documents/{document_id}")
def document(document_id: str):
    for item in read_json("documents.json", []):
        if item["id"] == document_id:
            return item
    raise HTTPException(status_code=404, detail="Document introuvable")


@app.get("/api/documents")
def documents():
    return read_json("documents.json", [])


@app.get("/api/documents/{document_id}/original")
def original_document(document_id: str, download: bool = True):
    item = document(document_id)
    corpus = DEFAULT_CORPUS.resolve()
    path = (corpus / item['path']).resolve()
    if not path.is_relative_to(corpus) or not path.is_file():
        raise HTTPException(status_code=404, detail="Fichier original introuvable")
    inline = path.suffix.lower() in ('.pdf', '.txt', '.md', '.png', '.jpg', '.jpeg')
    types = {'.pdf': 'application/pdf', '.txt': 'text/plain', '.md': 'text/plain',
             '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
             '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
             '.eml': 'message/rfc822'}
    return FileResponse(path, filename=path.name,
                        media_type=types.get(path.suffix.lower(), 'application/octet-stream'),
                        content_disposition_type='inline' if inline and not download else 'attachment',
                        headers={'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store'})


@app.get("/api/dossier")
def dossier():
    from .dossier import build_dossier
    return build_dossier(read_json("dossier.json", {"sections": []}),
                         read_json("documents.json", []), get_project_memory())


@app.get("/api/synthesis")
def synthesis():
    from .synthesis import build_synthesis
    return build_synthesis(read_json("documents.json", []), get_project_memory())


@app.post("/api/search")
def search(req: SearchRequest):
    return {"results": search_documents(req.query, req.limit)}


@app.post("/api/ask")
def ask(req: AskRequest):
    return answer_question(req.question)


@app.post("/api/update")
def update(req: UpdateRequest):
    baseline = read_json("baseline.json", {})
    actions = read_json("actions.json", [])
    return build_update_analysis(req.event_text, baseline, actions)


@app.get("/api/brief")
def brief():
    return generate_executive_brief(
        baseline=read_json("baseline.json", {}),
        answers=read_json("answers.json", []),
        timeline=read_json("timeline.json", []),
        actions=read_json("actions.json", []),
    )
