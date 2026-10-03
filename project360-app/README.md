# NOVA Project Memory

AI-assisted project memory for the Project 360 NOVA challenge.

The app combines:

- FastAPI backend for ingestion, retrieval, question answering, and update comparison.
- React + Vite frontend for dashboard, evidence search, Q&A, timeline, updates, and bonus executive brief.
- Local JSON storage so the demo remains self-contained.

## Why This Is AI

- Retrieve relevant evidence from messy project files.
- Answer questions with citations.
- Detect contradictions between old and newer sources.
- Generate an executive brief grounded in the corpus.
- Compare a baseline against a new event.

The starter backend uses local lexical retrieval so it runs without an API key. You can upgrade it to use OpenAI, Gemini, Claude, or Ollama embeddings/LLMs later.

## Setup

Install frontend dependencies:

```bash
npm install
```

Install backend dependencies:

```bash
pip install -r requirements.txt
```

If `pip` is not available on your machine yet, install Python 3.11+ first.

## Run

Terminal 1:

```bash
uvicorn server.main:app --reload --port 8000
```

Terminal 2:

```bash
npm run dev
```

Open the Vite URL, usually `http://localhost:5173`.

## Data Flow

1. Put the challenge corpus in `../project 360 data/NOVA_ETUDIANTS`.
2. Run ingestion:

```bash
python -m server.ingest
```

3. The backend writes:

- `data/processed/documents.json`
- `data/processed/chunks.json`
- `data/processed/embeddings.json`

4. The frontend reads API endpoints exposed by FastAPI.

## Demo Flow

1. Open Dashboard.
2. Ask: `Quelle est la date de mise en production actuellement approuvee?`
3. Show the answer with source excerpts.
4. Search evidence for `INV-003`, `securite`, `accessibilite`, `go-live`.
5. Show the timeline and contradictions.
6. Paste a new event in Update Simulator.
7. Generate the executive brief.

## Ask NOVA Agent

The `Ask NOVA` tab calls `POST /api/ask` with a user question and returns an evidence-grounded response. The screen shows the text answer first, then lists the documents, emails, spreadsheets, notes, or other sources used to produce that answer.
When multiple relevant sources are found, NOVA favors the latest dated source document or email and shows that source date in the reference list.

- `answer`: concise synthesis from retrieved corpus excerpts.
- `confidence`: `high`, `medium`, or `low`, based on retrieval strength and source coverage.
- `cited_source_files`: unique source files used by the answer.
- `references`: typed source references shown after the answer.
- `excerpts`: exact cited text snippets with locator and score.
- `uncertainty`: what NOVA cannot confirm or what still needs human review.

This implementation is local and self-contained. It uses lexical retrieval over `data/processed/chunks.json`; add a hosted LLM later if you want stronger synthesis while keeping the same response shape.

## What To Improve Next

- Fill `answers.json` with final evidence-backed answers to Q01-Q10.
- Add PDF and XLSX extraction dependencies if needed.
- Add real embeddings and LLM synthesis if you have an API key.
- Add exact page/cell locators for PDF/XLSX evidence.
