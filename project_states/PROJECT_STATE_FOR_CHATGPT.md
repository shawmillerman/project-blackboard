# Project Blackboard – Current State Summary
**Generated:** January 18, 2026

---

## A) Project State Summary

### What the App Does (Reliably)

**Ingestion & Retrieval:**
- Accepts submissions in `.txt`, `.docx`, and `.pdf` formats
- Extracts and cleans text; strips boilerplate, bullets, headers/footers
- Stores embeddings in Supabase Postgres (pgvector)
- Supports vector similarity search for rubric, calibration, and feedback library content

**API Endpoints (Tier 1 & Tier 2):**
- **Tier 1 (`GET /tier1/course-answer`)**: Answer questions grounded in course references (rubric, syllabus, style guide, calibration docs). Returns structured citations.
- **Tier 2 (`POST /tier2/feedback-suggest`)**: Generate feedback suggestions using rubric context + feedback library + calibration examples. Returns score range + citations.

**Batch Grading (`grade_batch.py`):**
- Processes submissions in bulk; extracts text, applies quality gates, calls grader API
- Quality gates: enforces minimum word count (30), content-to-raw ratio (0.2)
- Applies deterministic structural rule: if `< 3 paragraphs`, downgrades Adherence score
- Supports `--dry-run` (extract + quality-gate, no grading) and `--grade` flags
- Idempotent: fails if output already exists (unless `--overwrite`)
- Produces per-file records (JSON) and batch rollup (JSONL)

**Calibration & Score Ranges:**
- Stores instructor-calibrated examples (submission text + feedback + grade) with embeddings
- Computes score ranges using IQR (25th–75th percentile) with confidence-based widening
- Widens range based on sample size and similarity distance
- Integrates with grading flow (feature-flagged via `ENABLE_SCORE_RANGE`)

**Persistence:**
- All ingested content tagged with `source` label for auditing
- Grading traces persist to DB for training data collection
- Environment-based config; no secrets committed

---

### What Problems Were Recently Solved

| Problem | Solution | Status |
|---------|----------|--------|
| FastAPI entrypoint confusion | Unified all routes in `app/server.py`; `app.py` is now a shim | Stable |
| Tier 1 endpoint naming | Renamed to `/tier1/course-answer`; old route retained as hidden alias | Backward compatible |
| Supabase DB connectivity | Connection string resolution; startup table creation; autocommit handling | Operational |
| Batch idempotency | Fail-on-exist behavior; consistent output structure | Implemented |
| Deterministic grading rules | Paragraph count checks integrated into batch processor | Implemented |
| PII exposure in logs | Anonymization flags available (`--anonymize`); not yet systemic | Partial |
| Score range computation | Calibration-based IQR with confidence widening | Feature-flagged |

---

### Architectural Decisions Locked In

1. **Single-rubric-per-assignment model**: Current code assumes one rubric per `assignment_id`. Multi-rubric support is backlog-only.

2. **Discrete rubric scoring**: Only 3 score levels allowed per category (Meets/Meets+ ~ 15, Needs Improvement ~ 11.25, etc.). Continuous scores rejected.

3. **Calibration as separate table**: Instructor examples stored separately from production grades; enables instructor-specific tone/consistency tracking (future).

4. **Embedding-first retrieval**: All grading suggestions driven by vector similarity, not keyword search. No fallback to full-text search.

5. **Batch-local output**: Each batch produces its own `batch_id/extracted/`, `grading/`, `reports/` hierarchy. No global query interface yet.

6. **Text extraction over OCR**: PDF/DOCX parsing uses pypdf + python-docx. OCR is explicitly deferred (flagged as "NEEDS_REVIEW" only).

7. **Paragraph count as sole Adherence rule**: Only structural check currently implemented. Other checks (e.g., all questions answered) are future work.

---

### What Is Intentionally Deferred

**Security/Compliance (Code Review Backlog):**
- DB schema constraints (uniqueness, NOT NULLs) — MVP blocker, high risk
- SQL injection & input validation — Post-MVP priority
- Authentication/authorization/rate-limiting — In-progress (rate limiter exists, auth missing)
- Secrets hardening (env validation, no secret leakage) — Post-MVP
- PII redaction in persistent logs — Known gap, mitigation flags exist

**Feature Completeness (Feature Backlog):**
- Multi-rubric assignments
- Tunable quality gate thresholds (hardcoded currently)
- Rubric versioning & resolution manifest
- OCR for scanned PDFs
- Batch resumption after timeout
- Plagiarism/collusion detection

**Analytics (P2, data prerequisites):**
- Longitudinal student performance tracking
- Cohort-level trend analysis
- Performance report generation
- Instructor explainability dashboard

---

## B) System Mental Model

### Ingestion Flow

```
Raw file (.txt/.docx/.pdf)
  → read_text() [extraction method: txt_plain | docx_paragraphs | pdf_pypdf]
    → clean_text() [normalize whitespace, strip bullets]
      → apply_quality_gates() [check min words, content ratio, extraction warnings]
        → Quality Status: OK_FOR_GRADING | OK_FOR_CALIBRATION | NEEDS_REVIEW
          → [Optional] Persist cleaned text to extracted/
```

- Extraction warnings include boilerplate removals, merged columns, OCR artifacts
- Quality gates are hardcoded: `min_words=30`, `min_ratio=0.2`
- If quality fails, record marked NEEDS_REVIEW; grading skipped

### Grading Flow

```
Clean submission text + assignment_id + course_id
  → retrieve_rubric_context() [vector search, top_k=6 by default]
  → retrieve_feedback_library() [vector search, top_k=6 by default]
  → retrieve_calibration_hits() [filter by assignment_id, vector search]
    → [Optional] compute_score_range_from_calibration() [IQR + widening]
      → prompt LLM with:
          - submission text
          - rubric descriptors + top-k hits
          - feedback library examples + top-k hits
          - score range guidance (if enabled)
        → LLM returns: rubric_id, score_low, score_high, suggested_feedback, citations
          → apply_structural_rules() [paragraph count check → potential Adherence downgrade]
            → Persist record (request_id, rubric_id, score, feedback, citations, adjustments)
```

- All citations return as structured objects (not inline strings)
- Structural rules are deterministic and logged in record
- Score range computation is feature-flagged; disabled by default

### Calibration Model

```
Instructor ingests exemplar submission + feedback + grade
  → Embedding computed for submission_text
    → Stored in calibration_examples table (separate from main ingestion)
      ↓
When grading new submission:
  → Vector search matches to past calibrations (same assignment_id)
    → Extract grade_numeric values
      → Compute percentiles (p25, p75) for score range
        → Widen range based on:
            - Sample size (< 3 → wider; > 8 → tighter)
            - Avg similarity distance (lower → tighter)
          → Return low/high + confidence explanation
```

- Confidence heuristics codified in `grading.py::compute_score_range_from_calibration_hits()`
- Calibration examples never mixed with production grades in retrieval

### Batch Processing

```
Input: submissions_dir + assignment_id + course_id + week + batch_id
  → For each file in directory:
      1. Extract & clean (as above)
      2. Apply quality gates
      3. [--dry-run only] Stop here; mark "dry_run"
      4. [--grade only] Call /tier2/feedback-suggest
      5. Apply structural rules
      6. Persist JSON record
      7. Append to rollup JSONL
      ↓
  → Generate batch_report.json: total, extracted, graded, failed, needs_review_count
      ↓
  → Output structure:
      batch_id/
        extracted/         ← cleaned texts
        grading/           ← [future] grading outputs
        reports/
          batch_report.json  ← summary stats
          batch_rollup.jsonl ← per-file records
          records/           ← individual JSON per file
```

- Dry-run: extracts and quality-gates but does NOT call grader
- Grading only happens if `--grade` flag + quality_status="OK_FOR_GRADING"
- Output is idempotent: fails if batch_id already exists (unless `--overwrite`)

### Persistence Layer

- **Ingestion tables:** One per source (rubric, feedback_library, calibration_examples, etc.)
- **Storage:** Supabase Postgres with pgvector extension
- **Metadata:** All records include `source`, `assignment_id`, `course_id`, chunk index, created_at
- **Access:** Vector similarity; no direct SQL queries in batch processor

---

## C) What's Done vs What's Deferred

### ✅ Implemented & Stable

| Feature | Status | Location |
|---------|--------|----------|
| FastAPI server + 2 API tiers | ✅ Stable | `app/server.py` |
| Text extraction (txt/docx/pdf) | ✅ Stable | `scripts/grade_batch.py`, `app/` |
| Quality gates (word count, ratio) | ✅ Stable | `scripts/grade_batch.py` |
| Vector embeddings + retrieval | ✅ Stable | `app/embed.py`, `app/retrieval.py` |
| Calibration table + storage | ✅ Stable | `app/db.py`, `app/calibration_api.py` |
| Score range computation (IQR) | ✅ Stable (feature-flagged) | `app/grading.py` |
| Batch processor (extract + grade) | ✅ Stable | `scripts/grade_batch.py` |
| Paragraph count rule | ✅ Stable | `scripts/grade_batch.py::apply_structural_rules()` |
| Batch idempotency | ✅ Implemented | Fail-on-exist; `--overwrite` override |
| Dry-run mode | ✅ Implemented | Extract + quality-gate, no grading call |
| Anonymization flags | ✅ Partial | `--anonymize` flag exists, not systemic |
| Rate limiting (per IP) | ✅ Basic | `app/server.py` (20 req/sec per IP) |
| Citation tracking | ✅ Implemented | Structured objects, [R1], [F1] labels |

### 🔄 In-Progress / Partial

| Feature | Status | Blockers |
|---------|--------|----------|
| PII redaction in logs | ⚠️ Partial | Needs systemic approach; currently flags only |
| Authentication / Authorization | ⚠️ Missing | Rate limiter present; auth entirely absent |
| DB schema constraints | ⚠️ Missing | MVP blocker per code review backlog |
| Error message clarity | ⚠️ Generic | Many errors lack context or suggestions |
| Batch status tracking | ⚠️ None | Simple JSON file works; no query interface |

### 📋 Backlog Only (Not Started)

**Grading:**
- Multi-rubric assignments
- Tunable quality gate thresholds per assignment
- Rubric versioning & manifest-based resolution
- Additional Adherence checks (all questions answered, completeness)
- Explainability audit trails for downgrades

**Calibration:**
- Instructor-specific calibration libraries
- Calibration consistency tracking across graders
- Calibration audit trail & impact logging

**Extraction:**
- OCR for scanned PDFs (flagged NEEDS_REVIEW only)
- Robustness testing of bullet/glyph stripping
- Manifest-driven ingestion (submissions.json with student_id mapping)
- Extraction method audit trail (surface in batch report)

**Batch Processing:**
- Atomic batch writes with rollback
- Batch resumption after timeout
- Batch timeout & checkpoint logic
- Per-category score distribution in report

**Analytics (P2, requires rubric versioning first):**
- Longitudinal student tracking
- Trend detection (improving/declining/flat)
- Cohort-level performance aggregation
- Performance report generation

**Security:**
- SQL injection & input validation
- Secrets hardening (env validation)
- Prompt injection & LLM safety controls
- File upload security for CSV/PDF

---

## D) New ChatGPT Thread Prompt

**Copy-paste below to start a fresh thread:**

---

### Project Brief

**Project Blackboard** is a FastAPI-backed feedback and grading system designed to handle all types of assignments across multiple courses. The system ingests student submissions (text/DOCX/PDF), retrieves relevant rubric/calibration/feedback content via vector similarity, and generates AI-assisted grading feedback with structured scores and citations.

**Current Architecture:**
- **Ingestion:** Multi-format text extraction → cleaning → quality gates (min 30 words, 20% content ratio)
- **Grading:** Vector retrieval of rubric/calibration/feedback examples → LLM prompt → structured response (score_low, score_high, feedback, citations)
- **Batch Processing:** `grade_batch.py` processes directories of submissions; applies deterministic paragraph-count rule (< 3 → downgrade Adherence); idempotent output with `--dry-run` support
- **Persistence:** Supabase Postgres + pgvector for embeddings; separate calibration_examples table for instructor exemplars
- **Score Ranges:** IQR-based with confidence widening (feature-flagged; uses calibration hits only)

**System Constraints:**
- One rubric per assignment_id (multi-rubric is future work)
- Discrete scoring only (3 levels: ~15, ~11.25, ~0)
- No OCR; scanned PDFs marked NEEDS_REVIEW
- Batch output is local JSON; no global query interface yet
- Quality gate thresholds hardcoded (min_words=30, min_ratio=0.2)
- Paragraph count is the only Adherence rule; other structural checks deferred

**What's Stable:**
- FastAPI server running on localhost:8000
- Vector retrieval working reliably
- Batch processor idempotent; dry-run mode functional
- Calibration table & score range computation operational (feature-flagged)
- Citations structured and trackable

**What's Known to Be Missing (by priority):**
1. **[MVP Blocker]** DB schema constraints (NOT NULLs, uniqueness)
2. **[MVP Blocker]** Hallucinated citations check (LLM safety)
3. **[Post-MVP]** SQL injection & input validation
4. **[Post-MVP]** Systemic PII redaction in logs
5. **[Post-MVP]** Authentication & authorization (basic rate limit exists)

**What's Deferred (intentional):**
- Rubric versioning & manifest-based resolution
- Multi-rubric support
- Advanced Adherence rules (answer completeness, question coverage)
- Instructor explainability dashboards
- Longitudinal student performance tracking (requires stable rubric versioning)
- OCR & batch resumption logic

---

### Immediate Goals for This Conversation

1. **[Choose one or more]:**
   - **A)** Implement missing MVP blockers (DB constraints, hallucination detection)
   - **B)** Address post-MVP security (SQL injection, PII redaction, auth)
   - **C)** Extend grading logic (add new Adherence rules, rubric resolution manifest)
   - **D)** Improve batch UX (rubric versioning, batch status tracking, better error messages)
   - **E)** Analytics foundation (design student performance tracking schema)
   - **F)** Something else (specify below)

2. **Constraints for this conversation:**
   - Assume the FastAPI server and DB are running and stable
   - No changes to the live API surface unless explicitly needed
   - Avoid rehashing prior environment setup or Supabase connectivity issues
   - Focus on code logic, schema design, or feature implementation

3. **Deliverables expected:**
   - Clear problem statement & acceptance criteria
   - Implementation plan (files to create/modify, test approach)
   - Copy-paste-ready code or SQL schema (if applicable)

---

**Ready to begin? State which goal (A–F) you want to tackle and any refinements to the constraints above.**

---

