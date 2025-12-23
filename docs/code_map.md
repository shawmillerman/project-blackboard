# Project Blackboard, Code Map

This document explains how the Project Blackboard FastAPI app starts, how requests flow through the system, how ingestion and retrieval work, where citations are assembled, and where calibration data is stored and applied.

Repo spine (most important files):
- app.py
- app/server.py
- app/calibration_api.py
- app/retrieval.py
- app/ingest.py, app/ingest_csv.py, app/ingest_text_file.py, app/ingest_structured.py
- app/chunking.py
- app/embed.py
- app/db.py
- app/config.py
- app/qa.py

---

## 1) Entry point and server startup

### Primary entry point
- `app.py`
  - Contains `app = FastAPI()` (confirmed)
  - Likely includes router registration directly OR delegates to `app/server.py`

### Server wiring
- `app/server.py`
  - Intended role: central place to assemble the app, include routers, middleware, and shared dependencies.
  - TODO: confirm whether `app.py` imports from `app.server` or duplicates setup.

### How the server starts
Typical patterns (one of these is used):
- Pattern A, uvicorn targets `app:app`
  - `uvicorn app:app --reload`
- Pattern B, uvicorn targets `app.server:app` or a factory function
  - `uvicorn app.server:app --reload`
  - or `uvicorn app.server:create_app --factory --reload`

TODO, confirm the correct command by searching for `uvicorn` usage or reading the top of `app.py`.

---

## 2) API surface, routes and request flow

### Calibration routes
- `app/calibration_api.py`
  - Defines `router = APIRouter(prefix="/calibration", tags=["calibration"])` (confirmed)
  - Implements at least:
    - `POST /calibration/ingest` (confirmed)
  - Intended role:
    - Receive ingestion requests for calibration materials, likely style guide, syllabus, rubric, feedback library
    - Kick off ingestion pipeline, then store chunks and embeddings in pgvector-backed storage

Router wiring:
- Somewhere in app assembly, the router is included, example:
  - `app.include_router(calibration_router)` (observed in your grep output, file name not confirmed)

TODO:
- Identify whether router is included from `app.py` or `app/server.py`, also confirm the router variable name, `router` vs `calibration_router`.

### QA routes
- `app/qa.py`
  - Intended role: a simple question-answer endpoint for validating retrieval behavior.
  - Likely reads from vector store via `app/retrieval.py`, then formats an answer plus citations.

TODO:
- Confirm endpoint path(s) in this file, likely `/qa`, `/ask`, or similar.

---

## 3) Request flow, routes → services → DB

### High-level request flow for ingestion
`POST /calibration/ingest`
- calibration_api.py
  - Parses request payload
  - Determines ingestion target(s), file(s), or document type(s)
  - Calls ingestion orchestrator:
    - ingest.py (likely)
      - which calls one of:
        - ingest_text_file.py
        - ingest_csv.py
        - ingest_structured.py
  - Ingestion steps:
    - chunking.py to split content into chunks with metadata
    - embed.py to create embeddings for chunks
    - db.py to write chunks, embeddings, metadata into storage

### High-level request flow for retrieval
QA endpoint or grading endpoint calls retrieval
- qa.py (or another route)
  - Passes user query, assignment context, or rubric context into retrieval.py
- retrieval.py
  - Embeds query (embed.py)
  - Queries vector store (db.py)
  - Returns top chunks plus metadata
  - Assembles citations (see citations section)

---

## 4) Ingestion flow

Ingestion modules:
- `app/ingest.py`
  - Intended role: orchestrator, a common entry point for ingestion from different sources.
- `app/ingest_text_file.py`
  - Reads text files, normalizes content, passes content to chunker.
- `app/ingest_csv.py`
  - Reads CSV, likely feedback library or structured rubric items, turns rows into documents, then chunks or stores directly.
- `app/ingest_structured.py`
  - Handles structured documents, possibly JSON-like formats, or schema-driven ingestion.

Chunking:
- `app/chunking.py`
  - Responsible for splitting documents into chunks
  - Key decisions live here:
    - chunk size
    - overlap
    - metadata fields attached to each chunk, like source_file, doc_type, section, row_id

Embedding:
- `app/embed.py`
  - Creates embeddings for chunks and for queries
  - Responsible for:
    - selecting embedding model
    - batching
    - retry logic, timeouts
    - returning vectors in the format expected by db.py

Storage:
- `app/db.py`
  - Manages DB connection and SQL
  - Responsible for:
    - inserting documents/chunks
    - inserting embeddings to pgvector column(s)
    - similarity search queries
    - filtering by doc_type, assignment_id, course, etc (if supported)

TODO:
- Confirm whether ingestion stores raw text alongside embeddings, and the schema used for citations.

---

## 5) Retrieval flow

Primary retrieval module:
- `app/retrieval.py`
  - Intended role:
    - embed query
    - similarity search
    - optionally rerank or filter
    - return a context bundle for the LLM, plus citations metadata

Typical retrieval steps:
1) Input: user query, assignment_id (optional), course (optional), filters (optional)
2) Create query embedding via embed.py
3) Similarity search in db.py, top K chunks
4) Build a retrieval result object:
   - chunk texts
   - chunk metadata
   - scores or distances
5) Return result to calling layer (qa endpoint or grading endpoint)

TODO:
- Confirm how filtering is handled, if there is a concept of assignment_id or course-level corpuses.

---

## 6) Citations

Where citations are added:
- Likely in `app/retrieval.py` OR in the layer that formats the final LLM response (qa.py, or grading service if exists).
- The core requirement:
  - citations appear only when expected
  - citations map cleanly back to chunk metadata

Citation construction typically uses metadata like:
- source file name, like `ba101_syllabus_2026.txt`
- document section, page, or row id
- chunk index
- optionally a stable chunk_id in the DB

TODO:
- Identify the exact function that builds citations, search for terms like `citation`, `source`, `chunk_id`, `metadata`, `references`.

---

## 7) Calibration and feedback library

Data files in repo:
- `data/ba101_documents/ba101_style_guide_v1.txt`
- `data/ba101_documents/ba101_syllabus_2026.txt`
- `data/ba101_documents/feedback_library.csv`
- `data/ba101_documents/rubric_test.pdf`

Calibration API:
- `app/calibration_api.py`
  - `POST /calibration/ingest` is the entry point that likely ingests one or more of the above.

How calibration is applied:
Two common patterns:
- Pattern A, retrieval-time grounding
  - The system retrieves calibration snippets (style guide, feedback patterns, rubric) and injects them into the prompt context.
- Pattern B, prompt-time dominance
  - The system includes a fixed calibration instruction block in the prompt and uses retrieval only as supporting citations.

TODO:
- Identify which pattern is used in your app today, or if it is a hybrid.

---

## 8) Config and environment variables

Config module:
- `app/config.py`
  - Intended role:
    - load environment variables
    - define settings and defaults
    - centralize model names, DB URLs, table names, feature flags

DB module:
- `app/db.py`
  - uses config values for connection strings

Embed module:
- `app/embed.py`
  - uses config values for OpenAI key and model selection

Recommended env var list (names only, do not commit values):
- OPENAI_API_KEY
- DATABASE_URL (or SUPABASE_DB_URL)
- SUPABASE_URL (if used)
- SUPABASE_ANON_KEY or SERVICE_ROLE_KEY (only if applicable, be careful)
- EMBEDDING_MODEL (optional)
- APP_ENV (optional, dev, prod)

TODO:
- Confirm the exact env var names currently used.

---

## 9) Runbook, how to run and verify

### Install dependencies
- Create venv and install requirements:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -r requirements.txt

### Run server
TODO, confirm which command matches your code:
- `uvicorn app:app --reload`
- OR `uvicorn app.server:app --reload`

### Verify with Swagger
- Open:
  - http://127.0.0.1:8000/docs

### Ingestion
Use the calibration ingestion endpoint:
- `POST /calibration/ingest`
  - Provide whatever payload is required, likely file path(s) or a named document set.

TODO:
- Document the exact request body schema after we look at the endpoint signature.

### Quick smoke test
- Run a QA query endpoint (if present) after ingestion:
  - `GET /qa` or `POST /qa`
  - Confirm:
    - retrieval returns relevant context
    - citations appear in expected format
    - response length is sane

---

## 10) Known cleanup items

Not tracked, local-only:
- `app/__pycache__/...`
  - Ignore, do not commit
  - Confirm .gitignore includes `__pycache__/` and `*.pyc`

Non-production scripts:
- `experiments/hello_assistant.py`
  - Archived scratch file, not part of runtime.

---

## 11) Next steps to finalize this code map

To remove remaining TODOs, capture these tiny outputs:
- grep include_router and FastAPI from app.py and app/server.py
- list all routes, by searching for `@router.` and `@app.` decorators
- identify where citations are assembled, search for `citation` and `source`
- identify how ingestion selects files, does it accept file paths, a directory, or a named corpus

Once confirmed, update this document with:
- exact uvicorn command
- exact endpoint paths, methods, request schemas
- exact citation format
- exact calibration dominance strategy
