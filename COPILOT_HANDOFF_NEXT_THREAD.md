# Project Blackboard: Handoff Summary for Next Copilot Thread

**Date**: January 19, 2026  
**Session Focus**: Extraction logic fixes, calibration workflow completion, and validation prep  
**Current State**: Core grading-calibration pipeline functional; extraction bug fixed; ready for end-to-end validation

---

## 1. Project Overview

**Project Blackboard** is an instructor-assisted LLM grading system for BA101 (Business Activity) assignments.

**Purpose**: Automate draft feedback generation while preserving instructor control and consistency through calibration.

**Problem Solved**: Naive AI grading is unpredictable and inconsistent. Blackboard grounds grading in:
- Instructor-provided calibration exemplars (anchor submissions with instructor grades/feedback)
- Structured rubrics (criteria, weights, philosophy)
- Week-specific calibration (fallback to course-level when insufficient week examples exist)

**For Whom**: Instructors (BA101) who need to grade 100+ submissions per week with consistency and reduced manual effort.

---

## 2. Current State of the System (As-Built)

### What Is Working

**Grading Pipeline (Single & Batch)**
- FastAPI server (`app/server.py`) with `/tier2/feedback-suggest` endpoint
- Input: submission text + assignment context (course_id, assignment_id, week)
- Output: suggested grade (score_low, score_high) + instructor feedback + citations
- Deterministic structural rules: paragraph count < 3 → downgrade Adherence score
- Quality gates: min_words=30, min_ratio=0.2 to flag suspicious extractions

**Batch Processing (`scripts/grade_batch.py`)**
- Processes directories of .txt, .docx, .pdf files
- Extracts & cleans text with proper paragraph preservation (double-newline boundaries)
- Applies quality gates (NEEDS_REVIEW or OK_FOR_GRADING)
- Optionally calls grader API and persists results
- Dry-run mode for testing without API calls
- Outputs: batch_rollup.jsonl, per-file canonical JSON, batch_report.json

**Pre-Screen Workflow (`scripts/pre_screen_review.py`)** [NEW]
- Interactive CLI to review NEEDS_REVIEW submissions before grading
- Shows extracted text and quality issues
- Instructor decides: approve for grading, or skip
- Updates canonical records with decision
- Supports auto-resume

**Calibration Workflow (`scripts/calibration_review.py`)**
- Interactive CLI for instructors to review AI grading outputs
- Captures instructor actuals: actual_score, actual_feedback, reasoning
- Flags exemplars for calibration bank
- Ingests flagged examples to `/calibration/ingest` endpoint
- Stores in `calibration_examples` table with embeddings

**Calibration Retrieval (`app/qa.py`, `app/retrieval.py`)**
- Week-specific calibration first: `retrieve_calibration_examples(assignment_id, top_k=4)`
- Fallback to course-level if week has < 3 anchors: `retrieve_calibration_examples_by_course(course, top_k=4)`
- Fallback to feedback_library (static) if no calibration exists
- Calibration examples used as prompt anchors (C1, C2, C3, C4) to guide tone and expectations
- Logged with distance scores for auditability

**Supported Input Formats**
- .txt: raw text files
- .docx: Word documents (extracts paragraphs with heading hierarchy preserved)
- .pdf: PDF files (page-by-page extraction)

**Output Artifacts**
- `artifacts/extraction_store/*.txt`: cleaned student submissions (global store)
- `artifacts/runs/batches/{batch_id}/grading/canonical/*.json`: per-file grading records with grade, citations, rubric_id
- `artifacts/runs/batches/{batch_id}/reports/final/batch_report.json`: batch summary (total, extracted, graded, failed, needs_review)
- `artifacts/runs/batches/{batch_id}/reports/debug/batch_rollup.jsonl`: line-by-line log of each file (status, extraction_method, quality_status, grade)
- `artifacts/runs/calibration/{calibration_id}/review_session.jsonl`: instructor review log (one line per reviewed submission)
- `artifacts/runs/calibration/{calibration_id}/calibration_payload.jsonl`: flagged calibration examples ready for ingest
- `artifacts/runs/calibration/{calibration_id}/ingestion_result.json`: result of /calibration/ingest call

**Database Tables**
- `rubric_chunks`: indexed rubric text with embeddings
- `feedback_library`: static instructor feedback examples (generic pool)
- `calibration_examples`: instructor-flagged exemplars with embeddings (week/course specific)
- `rubrics`: rubric definitions (title, philosophy, criteria, weights)

---

## 3. Assessment Workflow (Operational Flow)

### Prerequisites
- Supabase database is accessible and not paused
- FastAPI server is running: `python -m uvicorn app.server:app --reload`
- Rubric is ingested: run `scripts/reingest_core_rubric.py` if needed
- Calibration bank may be empty initially (uses feedback_library as fallback)

### Step-by-Step Execution

#### Phase 0: Extract & Pre-Screen (Optional; currently paused)
```bash
python scripts/grade_batch.py \
  data/ba101_submissions/week_1/raw_submissions \
  --assignment-id ba101_week_1 \
  --course-id BA101 \
  --week 1 \
  --batch-id ba101_wk1_raw_20260119 \
  --dry-run \
  --overwrite
```

**What happens:**
1. Iterates through .txt/.docx/.pdf files in input directory
2. Extracts text using `read_text()` with proper paragraph boundaries (double-newline joins)
3. Cleans with `clean_text()` (now removes instruction relics + normalizes whitespace)
4. Counts paragraphs from cleaned text
5. Applies quality gates → status = OK_FOR_GRADING or NEEDS_REVIEW
6. `--dry-run` mode: stops here, does NOT call grader
7. Persists extracted texts and records

**Then pre-screen NEEDS_REVIEW submissions:**
```bash
python scripts/pre_screen_review.py \
  --batch-id ba101_wk1_raw_20260119
```

**What happens:**
1. Loads batch_rollup.jsonl from extraction phase
2. Filters for NEEDS_REVIEW submissions (status=needs_review)
3. For each NEEDS_REVIEW:
   - Shows: filename, quality issues, extraction warnings, first 500 chars of extracted text
   - Instructor decides: (a) Approve for grading, (s) Skip, (n) Next/defer
4. Updates canonical records with decision (quality_status updated to OK_FOR_GRADING if approved)
5. Saves all decisions to pre_screen_session.jsonl
6. Auto-resumes from last screened record

**Rationale:** Cannot logically grade submissions with extraction issues. Instructor pre-screening ensures:
- Only valid submissions enter grading
- Suspicious/empty extractions are flagged upfront
- Clear audit trail of decisions

#### Phase 1: Batch Grading (Now Grade Only Approved Submissions)
```bash
python scripts/grade_batch.py \
  data/ba101_submissions/week_1/raw_submissions \
  --assignment-id ba101_week_1 \
  --course-id BA101 \
  --week 1 \
  --batch-id ba101_wk1_raw_20260119 \
  --grade \
  --overwrite
```

**What happens:**
1. Re-processes same files (checks canonical records for pre-screen decisions)
2. Skips submissions marked "skipped" from pre-screen
3. Grades submissions with status OK_FOR_GRADING (either originally or approved in pre-screen)
4. Calls `/tier2/feedback-suggest` API for each approved submission
5. Applies structural rules (paragraph count check → Adherence downgrade if needed)
6. Persists to:
   - `artifacts/extraction_store/{filename}_extracted.txt` (if not already there)
   - `artifacts/runs/batches/{batch_id}/grading/canonical/{filename}.json`
   - `artifacts/runs/batches/{batch_id}/reports/debug/batch_rollup.jsonl`

#### Phase 2: Calibration Review (Instructor-Driven)
```bash
python scripts/calibration_review.py \
  --batch-id ba101_wk1_raw_20260119 \
  --calibration-id ba101_wk1_cal_20260119 \
  --ingest
```

**What happens:**
1. Loads batch_rollup.jsonl from grading output
2. Iterates through graded submissions (status=graded)
3. For each submission:
   - Displays: original filename, student text, AI score range, AI feedback, citations
   - Captures: instructor actual_score, actual_feedback (required)
   - Asks: "Add to calibration bank?" (y/n)
   - If yes, also prompts: "Why is this a good calibration example?" (optional reasoning)
4. Auto-resumes from last reviewed record (uses `review_session.jsonl` line count)
5. Persists all reviews to `review_session.jsonl` (non-ingested log)
6. For flagged examples, builds calibration record with metadata and appends to `calibration_payload.jsonl`
7. If `--ingest` flag: POSTs flagged examples to `/calibration/ingest` endpoint
   - Endpoint embeds examples and inserts into `calibration_examples` table
   - Returns: count of inserted records
   - Saves result to `ingestion_result.json`

#### Phase 3: Next Batch Uses Calibration
When running a new batch with same `assignment_id` (ba101_week_1):
1. Grading API calls `/tier2/feedback-suggest` with new submissions
2. Retrieval logic in `suggest_feedback()`:
   - Queries `calibration_examples` for records with assignment_id=ba101_week_1
   - If ≥3 hits, uses week-specific calibration (mode=week)
   - If <3 hits, falls back to course-level: queries for metadata.course=BA101
   - If still no hits, uses `feedback_library` (generic static examples)
3. Selected calibration anchors inserted into prompt as context (C1, C2, C3, C4)
4. LLM generates feedback influenced by tone/standards in calibration examples
5. Grade persisted with calibration hit distances (for auditability)

### Validation Checklist

- [ ] Extraction_store files have proper paragraphs (multiple `\n\n` boundaries, not collapsed)
- [ ] Batch_rollup shows paragraph_count > 1 for multi-paragraph files
- [ ] Grade JSON contains citations (R1, R2, F1, F2, C1, C2 format)
- [ ] Calibration review captures actual_score and reasoning
- [ ] Ingestion returns inserted count > 0
- [ ] Next batch grading shows calibration mode in logs (week or course fallback)

---

## 4. Key Files and Folders

### Core Scripts
- `scripts/grade_batch.py` — Main batch grading runner (read_text, clean_text, extraction, quality gates, grading, persistence)
- `scripts/calibration_review.py` — Instructor review CLI (load rollup, interactive prompt, ingest to calibration API)
- `scripts/reingest_core_rubric.py` — Ingest rubric into rubric_chunks table (run if rubric_id is null)

### Application
- `app/server.py` — FastAPI app with `/tier2/feedback-suggest` and `/calibration/ingest` endpoints
- `app/qa.py` — `suggest_feedback()` function with calibration retrieval and rubric definition lookup
- `app/retrieval.py` — `retrieve_calibration_examples()`, `retrieve_calibration_examples_by_course()` (vector search queries)
- `app/ingest.py` — `ingest_pdf()`, `ingest_docx()` (used by reingest scripts)
- `app/db.py` — Database connection and insert_chunks()
- `app/embed.py` — Text embedding via OpenAI API
- `app/config.py` — Configuration (API keys, database URL)

### Data Input
- `data/ba101_documents/ba101_businessactivity_core_rubric.docx` — Rubric (ingested into rubric_chunks)
- `data/ba101_documents/feedback_library.csv` — Static feedback examples (ingested into feedback_library)
- `data/ba101_submissions/week_1/raw_submissions/` — Student submissions (.txt/.docx/.pdf)

### Output Artifacts
- `artifacts/extraction_store/` — Cleaned extracted text (global store, all batches)
- `artifacts/runs/batches/{batch_id}/grading/canonical/` — Per-file grading JSON (final records)
- `artifacts/runs/batches/{batch_id}/reports/final/batch_report.json` — Batch summary
- `artifacts/runs/batches/{batch_id}/reports/debug/batch_rollup.jsonl` — Debug log (one line per file)
- `artifacts/runs/calibration/{calibration_id}/review_session.jsonl` — Instructor review log
- `artifacts/runs/calibration/{calibration_id}/calibration_payload.jsonl` — Flagged calibration examples
- `artifacts/runs/calibration/{calibration_id}/ingestion_result.json` — Ingest API response

### Configuration & Documentation
- `feature_backlog/FEATURE_BACKLOG.md` — Product backlog (includes week-first calibration, refresh feedback_library items)
- `README_PRIVATE.md` — Project setup and troubleshooting
- `TROUBLESHOOTING.md` — Common issues and solutions

---

## 5. Known Constraints, Assumptions, and Guardrails

### Intentional Limitations

**Paragraph Preservation (JUST FIXED)**
- Extraction now uses double-newline (`\n\n`) boundaries for DOCX and PDF to preserve paragraph structure
- Single .txt files are assumed to already have proper paragraph markers

**Calibration Fallback (By Design)**
- Week-specific calibration is preferred; course-level fallback only if week < 3 anchors (MIN_WEEK_HITS=3)
- This ensures each week develops its own calibration set as volume grows
- Fallback to feedback_library only if no calibration exists at all

**Static Feedback Library**
- `feedback_library` is ingested once from CSV and not auto-updated
- Future feature: refresh feedback_library with cross-week exemplars after calibration is mature

**Rubric ID Resolution**
- Rubric_id can be null in grading outputs if rubric chunks weren't ingested with rubric_id metadata
- Workaround: run `scripts/reingest_core_rubric.py` to populate rubric_id in chunk metadata

### Instructor-Controlled Decisions

**Batch Parameters**
- `--assignment-id`, `--course-id`, `--week` are required (tags grading outputs)
- `--batch-id` must be unique per run (used for artifact folder naming)
- `--overwrite` flag enables re-running same batch_id (deletes prior outputs)

**Calibration Flagging**
- Instructor decides which submissions are exemplars (y/n prompt per file)
- Instructor provides optional reasoning (used for future analysis)

**Quality Gate Thresholds**
- Currently hardcoded: min_words=30, min_ratio=0.2 (ratio of cleaned/raw length)
- Can be overridden in future via batch config or rubric metadata

### Order Dependencies & Fragile Points

**Must Run in Order:**
1. Rubric ingest (or ensure rubric_id populated in DB)
2. Batch grading (extract, grade, persist)
3. Calibration review (review AI outputs, flag exemplars)
4. Calibration ingest (POST flagged examples to API)
5. Next batch grading (uses calibration from step 4)

**Fragile Points:**
- Supabase project can pause (connection will fail cryptically)
- FastAPI server must be running for /tier2/feedback-suggest and /calibration/ingest calls
- Extraction failures (corrupt PDF, encoding issues) silently mark submission as NEEDS_REVIEW
- Rubric_id null if rubric not ingested → grading outputs lack rubric definition context
- Paragraph collapse if extraction logic reverts (just fixed—verify during next run)

**No Atomic Batch Writes:**
- If batch process crashes mid-way, outputs are incomplete (recovery is manual)
- `--overwrite` allows safe re-runs, but no resume-from-checkpoint logic yet

---

## 6. What the Next ChatGPT Thread Should Do

### Immediate Goals (Priority Order)

**1. End-to-End Validation with Fixed Extraction (URGENT)**
   - Re-run batch grading on small subset (5-10 files) with `--overwrite`
   - Verify extraction_store files have proper paragraphs (check 2-3 files for `\n\n` boundaries)
   - Verify batch_rollup.jsonl shows paragraph_count > 1 for multi-para files
   - Confirm no errors in canonical JSON files
   - **Success Criteria**: All extracted files have 2+ paragraphs, paragraph_count reflects reality

**2. Calibration Review Flow Validation**
   - Run `calibration_review.py` on the graded batch (interactive, 10+ files)
   - Capture actual instructor scores/feedback + flag 5-10 exemplars
   - Run with `--ingest` to POST to calibration API
   - Verify `ingestion_result.json` shows inserted > 0
   - **Success Criteria**: Calibration payload ingested, calibration_examples table populated

**3. Verify Calibration Retrieval in Grading**
   - Enable `DEBUG_RETRIEVAL=true` environment variable
   - Run batch grading on a NEW batch of submissions (same assignment_id ba101_week_1)
   - Check logs for "calibration[1]" entries showing retrieved anchors
   - Verify mode=week (if ≥3 week anchors) or mode=course (if <3)
   - **Success Criteria**: Calibration anchors retrieved and visible in logs; prompt includes (C1, C2, C3)

**4. Edge Case Testing**
   - Test very short submission (< 30 words) → should mark NEEDS_REVIEW
   - Test PDF with multiple pages → should preserve page boundaries as paragraphs
   - Test DOCX with nested headings → should include heading context in chunks
   - Test submission with no paragraphs → should count as 1 paragraph, trigger Adherence downgrade if applicable
   - **Success Criteria**: All edge cases handled without crashes; status and reasons logged

**5. Data Cleanup & Prep for Real Usage**
   - Delete old batch artifacts (ba101_wk1_prod_20260118, other stale batches)
   - Verify extraction_store contains only current validated files (no "-clean" or malformed extracts)
   - Archive or document any one-time calibration sessions that were incomplete
   - **Success Criteria**: Artifacts folder is clean and ready for production grading

### Optional (If Time Permits)

- Test cross-week calibration fallback behavior (create fake week_9 calibration, verify fallback only if week_1 < 3 anchors)
- Validate rubric_id persistence through grading → calibration ingest → retrieval cycle
- Document operational runbook (step-by-step commands for instructor to follow each week)
- Refactor extraction warnings/quality reasons into structured enum (currently strings, hard to filter)

---

## 7. File Access Verification (Critical)

### Current Access Status

✅ **All repository files accessible** (path: `/Users/admin/ProjectBlackboard`)

### Files Needed for Next Thread

**Essential** (required to continue):
- `scripts/grade_batch.py` — recently fixed (double-newline joins)
- `scripts/calibration_review.py` — working state
- `app/server.py`, `app/qa.py`, `app/retrieval.py` — core grading logic
- `app/db.py`, `app/embed.py`, `app/config.py` — database & embeddings
- `data/ba101_submissions/week_1/raw_submissions/` — test data
- `data/ba101_documents/ba101_businessactivity_core_rubric.docx` — rubric
- `feature_backlog/FEATURE_BACKLOG.md` — backlog (already updated with calibration refinement items)

**Optional** (good to have, not blocking):
- `TROUBLESHOOTING.md` — for debugging issues
- `README_PRIVATE.md` — for setup context
- Git history (`git log --oneline scripts/grade_batch.py`) — to see fix commits

### Database Access Required

- **Supabase Connection**: Tables must be accessible (rubric_chunks, feedback_library, calibration_examples, rubrics)
- **OpenAI API Key**: Required for embeddings and grading (set in `app/config.py`)
- **FastAPI Server**: Must be running on localhost:8000 (or update `DEFAULT_SERVER` in grade_batch.py)

### Questions for Next Thread

**Before starting validation, confirm:**
1. Is Supabase project still running (not paused)?
2. Is FastAPI server accessible on localhost:8000?
3. Do you have OpenAI API key configured?
4. Can you access data/ba101_submissions/week_1/raw_submissions/ (contains test files)?

---

## Lessons Learned & Edge Cases

### Quality Gate Threshold Adjustment (2026-01-19)

**Issue:** Files flagged as `NEEDS_REVIEW` with valid content due to strict `min_ratio=0.20`

**Root Cause:** PDFs with heavy boilerplate (headers, footers, assignment instructions) had low retention ratios even with complete student responses.

**Example:** anon-041-raw.pdf
- Raw: 1764 chars → Cleaned: 345 chars = 19.5% ratio
- Content: Valid 3-paragraph response (61 words, concise but complete)
- Flagged: `NEEDS_REVIEW` due to ratio < 0.20

**Solution:** Reduced `min_ratio` to 0.15 (15% retention threshold)

**Rationale:**
- Concise responses are valid (short answers are acceptable in BA101)
- Word count gate (`min_words=30`) still prevents truly empty submissions
- 15% threshold allows legitimate responses while catching extraction failures

**Implementation:**
- Location: `scripts/grade_batch.py` → `apply_quality_gates()` function
- Documentation: TROUBLESHOOTING.md, code comments, git commit

**Key Takeaway:** Quality gates must balance strictness with real-world submission patterns. Overly strict thresholds create false positives that waste instructor time.

---

## Summary

**What's Ready**: Core grading-calibration pipeline functional; extraction logic fixed (paragraph preservation); batch grading and calibration review scripts operational.

**What's Next**: End-to-end validation with fixed extraction; calibration review & ingest; verify retrieval in next batch grading; edge case testing; production prep.

**Files to Access**: All files in `/Users/admin/ProjectBlackboard` are accessible. Database and API keys must be verified before proceeding.

**Estimated Time for Next Thread**: 2-3 hours for full validation + cleanup (depends on test data size and edge cases).
