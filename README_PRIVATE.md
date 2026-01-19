# Project Blackboard – Private README

This repository is intentionally **private**.
It contains the canonical implementation of Project Blackboard’s FastAPI 
backend, including ingestion, retrieval, calibration, and grading logic.

This repo is not intended for public sharing.

---
## Having trouble starting the server?
See `TROUBLESHOOTING.md` for a fast checklist.


## Recent Changes (12/23/25)

- Renamed Tier 1 endpoint from `/tier1/rubric-answer` to `/tier1/course-answer`
  - Old route retained as a hidden alias for backward compatibility
- Unified FastAPI entrypoint so all routes are registered in `app/server.py`
- Added file header conventions to clarify runtime vs shim vs experimental code
- Normalized documentation to reflect current architecture

This change set explains why multiple files were modified together.
# End of December 23 changes ------

## Repo posture

- This repo is the **source of truth** for the application logic.
- IP protection is achieved by keeping the repo private.
- No secrets are committed; all configuration is via environment 
variables.
- Any future public-facing materials should live in a separate, 
stripped-down repo.

---

## App structure (canonical)

- **Canonical FastAPI app**
  - `app/server.py`
  - All routes are registered here.

- **Entrypoint shim**
  - `app.py`
  - Exists only so `uvicorn app:app` continues to work.
  - Contains no logic.

- **Documentation**
  - `docs/code_map.md` describes request flow, ingestion, retrieval, and 
citations.

---

## API tiers

### Tier 1 – Course Answer
- **Endpoint:** `GET /tier1/course-answer`
- Purpose:
  - Answer questions grounded in authoritative course references.
- Sources include:
  - rubric
  - syllabus
  - style guide
  - calibration documents
- Notes:
  - This endpoint was formerly named `/tier1/rubric-answer`.
  - The old route is retained as a hidden alias for backward 
compatibility.

### Tier 2 – Feedback Suggest
- **Endpoints:**
  - `GET /tier2/feedback-suggest`
  - `POST /tier2/feedback-suggest`
- Purpose:
  - Generate feedback suggestions using:
    - rubric context
    - feedback library examples
    - calibration examples
- Returns structured feedback plus citations.

### Calibration
- **Endpoint:** `POST /calibration/ingest`
- Purpose:
  - Ingest calibration and reference materials into the vector store.
- All ingested content is tagged with a `source` label.

---

## Ingestion notes

- Supported ingestion formats:
  - plain text files
  - CSV (feedback library)
  - structured JSON-like formats
- Ingestion code lives in:
  - `app/ingest.py`
  - `app/ingest_csv.py`
  - `app/ingest_text_file.py`
  - `app/ingest_structured.py`
- All ingested records store:
  - `source`
  - chunk index
  - metadata
  - embeddings

Seed documents for BA101 live in:
- `data/ba101_documents/`

These are **test fixtures only** and are not ingested unless explicitly 
requested.

---

## Citations

- Citations are returned as structured objects, not inline strings.
- Formatting helpers live in:
  - `app/qa.py`
- Citation labels use prefixes like:
  - `[R1]` for rubric/reference hits
  - `[F1]` for feedback library h

---

## Batch Grading (Training Data)

- Purpose: Grade real submissions and store grading traces (training data).
- Server: ensure the API is running locally.

- Start server:
  - `python -m uvicorn app.server:app --reload`

  - `python scripts/grade_batch.py <SUBMISSIONS_DIR> <ASSIGNMENT_ID> <COURSE> --csv-out artifacts/grades.csv`
  - Example:
   - `python scripts/grade_batch.py data/ba101_submissions/week_1 ba101_week_1 BA101 --anonymize --csv-out artifacts/ba101_week1_grades.csv`

  - `--anonymize`: basic redaction of emails/phones/IDs before sending
  - `--points`: set points possible (default 40.0)
  - `--top-k-rubric`, `--top-k-feedback`: retrieval sizes (defaults 6)
  - `--server`: override server base URL (default http://localhost:8000)

- Output:
  - Console logs include `request_id`, `rubric_id`, and citation count
  - Optional CSV contains file, request_id, rubric_id, score_low/high, and suggested_feedback


