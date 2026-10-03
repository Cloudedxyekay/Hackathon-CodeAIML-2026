from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .rag import answer_question, reasoning_status, search_documents
from .ingest import ingest_corpus
from .prompts import build_update_analysis, generate_executive_brief

ROOT = Path(__file__).resolve().parents[1]
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
    }


@app.get("/api/answers")
def answers():
    return read_json("answers.json", [])


@app.get("/api/timeline")
def timeline():
    return read_json("timeline.json", [])


@app.get("/api/documents")
def documents():
    return read_json("documents.json", [])


@app.get("/api/dossier")
def dossier():
    return read_json("dossier.json", {"sections": []})


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
