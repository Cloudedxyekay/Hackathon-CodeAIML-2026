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

On Windows, run each command below in a separate PowerShell terminal inside
`project360-app`. Reopen VS Code after installing Node.js so its PATH is refreshed.

```powershell
# Backend (local virtual environment)
.\.venv\Scripts\python.exe -m uvicorn server.main:app --reload --host 127.0.0.1 --port 8000

# Frontend (in the second terminal)
npm.cmd run dev
```

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

## Project memory, calendar and progress

The default **Mémoire du projet** workspace provides three linked views:

- **Chronologie**: dated decisions, proposals, deliveries, validations and risks;
  search and filters by actor, topic, event type, month and date meaning.
- **Calendrier**: monthly navigation, multi-day planned activities and a daily agenda.
- **Avancement**: the documented project plan, cumulative ticket creations and
  explicit closures, and a ticket register with source references.

Every event opens an evidence drawer with original excerpts, source locators and
the full extracted document. The workspace also shows project-owner transitions,
approved target changes, open production gates, and discrepancies in stale plans
or status reports. Export the filtered events as an `.ics` calendar or JSON.
**Ré-analyser** re-ingests the local corpus and rebuilds project memory.

The extractor runs locally without an API key or connected LLM. It uses explicit
date fields, French date parsing, structured ticket/plan fields and linguistic
rules. Authors and requesters are labelled separately from assigned owners.
Planning targets are not recorded as actual deliveries; undated publication
dates and unknown closure dates remain unknown. Global project completion is
not inferred from ticket counts. The latest plan's declared statuses remain
historical claims. Only explicit governance sources set the approved target.

API: `GET /api/project-memory`, `GET /api/timeline`,
`GET /api/documents/{document_id}`, `POST /api/ingest`.
Generated files: `data/processed/project_memory.json` and `timeline.json`.

### Optional LLM enrichment

The **Enrichir IA** button uses Ollama by default, so the demo can run without a
paid API key. Install Ollama, pull a model, and restart Uvicorn:

```powershell
ollama pull qwen2.5:7b
$env:OLLAMA_MODEL="qwen2.5:7b"
uvicorn server.main:app --reload --port 8000
```

If Ollama runs somewhere other than `http://127.0.0.1:11434`, set
`OLLAMA_BASE_URL`. Click **Enrichir IA** to explicitly send evidence excerpts to
the configured model. No provider request is made during page loading or local
re-ingestion.

Local enrichment is intentionally bounded for demo speed: Ollama enriches the
highest-signal 30 events by default, in small batches with shorter excerpts. To
process more or tune throughput, set `NOVA_AI_EVENT_LIMIT`, `NOVA_AI_BATCH_SIZE`
or `NOVA_AI_WORKERS`.

The connector asks the model for structured JSON annotations: concise summaries,
decision descriptions, dates and named actors.
Annotations must reference an existing event and quote exact source text;
unsupported dates, names and citations are discarded. AI summaries are labelled
and kept separate from canonical approvals, ticket states and assigned roles.
Results are cached against a corpus fingerprint. A changed corpus invalidates
the annotations, and a provider error preserves local extraction.
OpenAI remains available as an explicit fallback: set `NOVA_AI_PROVIDER=openai`,
`OPENAI_API_KEY`, and `NOVA_AI_MODEL`. The API key is never sent to the browser.
Provider storage is disabled for OpenAI using `store: false`.

API: `POST /api/project-memory/enrich`. Cache: `data/processed/ai_enrichment.json`.

Run extraction and regression checks:

```powershell
.\.venv\Scripts\python.exe -m server.ingest
.\.venv\Scripts\python.exe -m unittest server.test_intelligence server.test_ai_extraction -v
npm.cmd run build
```

## Demo Flow

## Suivi par catégorie dans le Dossier

L’onglet **Dossier** conserve ses catégories du projet et présente dans chacune
les décisions, responsables explicitement désignés, engagements, échéances
et risques via `GET /api/dossier`.
Chaque élément conserve ses extraits, son document et son localisateur.
Les propositions, décisions conditionnelles et dates périmées sont distinguées.
Les engagements sont des obligations ou promesses documentées ; leur réalisation
n’est pas déduite. Les échéances relatives restent dans l’extrait et les dates
inconnues restent inconnues. Les demandeurs de tickets ne sont pas assimilés à
des responsables assignés. Les divergences du plan et du registre sont affichées.
Les filtres sélectionnent les catégories du projet ; l’export JSON inclut le dossier complet.
**Ré-analyser le corpus** régénère les sources et la mémoire locale sans appel LLM.

Vérification : `.\.venv\Scripts\python.exe -m unittest server.test_synthesis server.test_dossier`.
Export Markdown et JSON : `.\.venv\Scripts\python.exe -m server.synthesis`
(fichiers dans `data/reports`).

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
For direct factual questions, such as the currently approved go-live date, NOVA extracts only the requested fact for the answer and keeps the longer proof text in the excerpts section.

- `answer`: concise synthesis from retrieved corpus excerpts.
- `confidence`: `high`, `medium`, or `low`, based on retrieval strength and source coverage.
- `cited_source_files`: unique source files used by the answer.
- `references`: typed source references shown after the answer.
- `excerpts`: exact cited text snippets with locator and score.
- `uncertainty`: what NOVA cannot confirm or what still needs human review.

This implementation is local and self-contained. It uses lexical retrieval over `data/processed/chunks.json`; add a hosted LLM later if you want stronger synthesis while keeping the same response shape. PDF and Excel ingestion are supported through `pypdf` and `openpyxl` from `requirements.txt`.

### Optional External Reasoning Model

Ask NOVA can use a reasoning model after local retrieval. The app still retrieves evidence locally, then sends only the selected snippets to the model for concise synthesis.

For a hackathon demo, Ollama is the most reliable option because it runs locally and does not require API keys.

Ollama setup:

```powershell
ollama pull qwen2.5:7b
$env:OLLAMA_MODEL="qwen2.5:7b"
uvicorn server.main:app --reload --port 8000
```

If Ollama runs somewhere other than `http://127.0.0.1:11434`, set:

```powershell
$env:OLLAMA_BASE_URL="http://127.0.0.1:11434"
```

OpenAI remains optional if you prefer a hosted model:

PowerShell:

```powershell
pip install openai
$env:OPENAI_API_KEY="your-api-key"
$env:NOVA_REASONING_MODEL="gpt-4.1-mini"
uvicorn server.main:app --reload --port 8000
```

Reasoning order:

1. Use `OLLAMA_MODEL` when set.
2. Use OpenAI when `OPENAI_API_KEY` is set.
3. Fall back to the local answer extractor.

## What To Improve Next

- Fill `answers.json` with final evidence-backed answers to Q01-Q10.
- Add PDF and XLSX extraction dependencies if needed.
- Add real embeddings and LLM synthesis if you have an API key.
- Add exact page/cell locators for PDF/XLSX evidence.
