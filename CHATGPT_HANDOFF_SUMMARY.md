# Project Blackboard – Handoff Summary for ChatGPT

**Generated:** January 18, 2026  
**Purpose:** Comprehensive project state documentation for second-opinion technical review

---

## 1. Project Overview

### What This Application Is Intended to Do

**Project Blackboard** is an AI-assisted grading and feedback system for educational assignments. It processes student submissions (text/DOCX/PDF), retrieves contextually relevant rubric guidance and calibrated examples using vector similarity search, and generates structured feedback with numerical score ranges and citations.

The system is designed to:
- Reduce grading time for instructors while maintaining consistency
- Provide students with detailed, citation-backed feedback
- Support calibration through instructor-provided exemplar submissions
- Enable batch processing of entire assignment cohorts
- Track grading decisions for audit and improvement

### Primary Users

**Current user:** Single instructor (BA101 course) using system for pilot deployment  
**Target users (future):**
- Community college instructors across multiple business courses
- Teaching assistants performing initial grading reviews
- Program coordinators auditing grading consistency

### Current Maturity Stage

**Late MVP / Early refactor**

- Core features operational and tested on 50+ real student submissions
- Batch processing proven stable; idempotency and dry-run modes working
- Security and schema constraints identified but not yet hardened (MVP blockers documented)
- Currently in pilot with one course; not yet multi-tenant or production-ready
- No authentication layer; intended for trusted local/internal use only at this stage

---

## 2. What the App Currently Does

### Core Features That Are Implemented and Working

#### Ingestion & Text Extraction
- ✅ Accepts `.txt`, `.docx`, and `.pdf` submissions
- ✅ Extracts text using `python-docx` and `pypdf`
- ✅ Cleans text: normalizes whitespace, strips boilerplate, removes common instructional headers
- ✅ Quality gates: minimum word count (30), content-to-raw ratio (≥20%)
- ✅ Marks low-quality submissions as `NEEDS_REVIEW` without grading them

#### Vector Retrieval & Grading
- ✅ Stores embeddings in Supabase Postgres with `pgvector` extension
- ✅ Vector similarity search for rubric guidance, feedback library examples, calibration hits
- ✅ Calls OpenAI API with retrieved context to generate feedback
- ✅ Returns structured response: `score_low`, `score_high`, `suggested_feedback`, `citations`
- ✅ Structured citations with labels: `[R1]` (rubric), `[F1]` (feedback library), `[C1]` (calibration)

#### Batch Processing (`grade_batch.py`)
- ✅ Processes directories of submissions in bulk
- ✅ Idempotent: fails if `batch_id` output already exists (unless `--overwrite`)
- ✅ Dry-run mode: extract and quality-gate only, no grading API calls
- ✅ Grade mode: `--grade` flag triggers grading for `OK_FOR_GRADING` submissions
- ✅ Outputs per-file JSON records + batch-level rollup (JSONL) + summary report (JSON)
- ✅ Deterministic structural rule: < 3 paragraphs → downgrade Adherence score from Meets (15) to Needs Improvement (11.25)

#### Calibration System
- ✅ Separate `calibration_examples` table stores instructor exemplars (submission text + feedback + grade)
- ✅ Retrieval filters by `assignment_id` to match calibration examples to current assignment
- ✅ Score range computation using IQR (25th–75th percentile) with confidence-based widening
- ✅ Widens range when sample size < 5 or average similarity distance is high
- ✅ Feature-flagged: `ENABLE_SCORE_RANGE` env var (default: off)

#### API Endpoints
- ✅ **Tier 1:** `GET /tier1/course-answer` – answers questions grounded in rubric/syllabus/style guide
- ✅ **Tier 2:** `POST /tier2/feedback-suggest` – generates feedback with score ranges and citations
- ✅ **Calibration:** `POST /calibration/ingest` – ingests instructor exemplars into vector store
- ✅ Rate limiting: 20 requests per IP per 60-second window (in-memory, simple)

### Key Workflows or Flows That Exist End-to-End

1. **Calibration Setup Flow** (one-time per assignment)
   - Instructor ingests 3–8 exemplar submissions with grades via `/calibration/ingest`
   - System computes embeddings, stores in `calibration_examples` table with `assignment_id` tag

2. **Batch Grading Flow** (per cohort)
   - Run: `python scripts/grade_batch.py <dir> --assignment-id ba101_week_1 --course-id BA101 --week 1 --batch-id wk1_full --grade`
   - System extracts text, applies quality gates, calls grading API for each submission
   - Applies deterministic paragraph count rule (< 3 → downgrade Adherence)
   - Outputs: `artifacts/runs/batches/wk1_full/grading/canonical/*.json`, `reports/final/batch_report.json`, `reports/debug/batch_rollup.jsonl`

3. **Manual Grading Review Flow** (instructor QA)
   - Instructor opens `batch_rollup.jsonl` or individual `records/*.json` files
   - Reviews `suggested_feedback`, `score_low`, `score_high`, `citations`, `structural_adjustments`
   - Manually overrides or approves grades (currently manual; no UI)

### What Is Explicitly Not Implemented Yet

**Not Implemented:**
- ❌ Authentication / authorization (rate limiter exists but no user auth)
- ❌ Multi-rubric assignments (currently one rubric per `assignment_id`)
- ❌ Tunable quality gate thresholds (hardcoded: min_words=30, min_ratio=0.2)
- ❌ Rubric versioning or manifest-based resolution (no tracking of which rubric version was used)
- ❌ OCR for scanned PDFs (flagged as `NEEDS_REVIEW` only)
- ❌ Batch resumption after timeout or crash (no checkpoint logic)
- ❌ Plagiarism/collusion detection
- ❌ Instructor UI or dashboard (all interactions are CLI + JSON file review)
- ❌ Longitudinal student performance tracking (no stable student_id persistence)
- ❌ Explainability audit trail for Adherence downgrades (logged but not surfaced in report)

---

## 3. Current Focus

### What I Am Actively Working On Right Now

**Just completed:** Full batch grading of 50 BA101 Week 1 submissions with calibration-based score ranges enabled. The paragraph count rule successfully downgraded Adherence scores for submissions with < 3 paragraphs.

**Immediate next steps:**
1. **CSV export for instructor review:** Convert batch rollup to CSV with columns: `filename`, `score_low`, `score_high`, `suggested_feedback`, `structural_adjustments`, `adherence_score`
2. **Instructor QA cycle:** Review CSV with instructor; collect feedback on accuracy, tone, and usefulness of generated feedback
3. **Code review backlog prioritization:** Decide which MVP blockers to tackle first (DB schema constraints vs. hallucinated citations check)

### Why This Work Matters in the Overall Roadmap

**Immediate impact:** The CSV export enables the instructor to efficiently review 50 graded submissions in a spreadsheet, which is critical for validating system accuracy before expanding to other assignments or courses.

**Strategic importance:** This is the first full end-to-end test of the grading pipeline with real student data. Success here validates:
- Calibration-based score ranges are meaningful
- Paragraph count rule is effective and non-disruptive
- Feedback quality is instructor-approved

Failure here (low instructor satisfaction) would require revisiting prompt engineering, retrieval quality, or structural rules before proceeding to production hardening.

### Any Open Design Questions or Uncertainties

**Open questions:**
1. **Should paragraph count checks apply to all assignments or only reflections?**  
   - Current: Hardcoded for all assignments  
   - Risk: Some assignments may intentionally allow brief responses (e.g., bullet lists)  
   - Proposed solution: Add `min_paragraphs` to assignment metadata or rubric config

2. **How to handle rubric versioning when an assignment is reused across terms?**  
   - Current: No tracking; `rubric_id` is static  
   - Risk: Instructor updates rubric mid-term; old submissions are graded against new rubric without audit trail  
   - Proposed solution: Add `rubric_version` + `created_at` to rubric records; embed version in grading traces

3. **Should score ranges be presented as "confidence intervals" or "typical ranges"?**  
   - Current: Labeled as "Range based on N graded calibration examples, [low/high] confidence"  
   - Uncertainty: Instructors may misinterpret as statistical confidence (e.g., 95% CI) vs. descriptive range  
   - Proposed solution: Change label to "Typical score range based on similar past submissions"

4. **Is the paragraph count rule too aggressive?**  
   - Current: < 3 paragraphs → automatic downgrade from 15 to 11.25 (25% penalty)  
   - Concern: Some submissions may have dense single paragraphs that are high-quality  
   - Proposed experiment: Log paragraph count violations without applying penalty; review false positives with instructor

---

## 4. File Structure Map

```
ProjectBlackboard/
│
├── app.py                           # Shim entrypoint (legacy; routes to app/server.py)
├── app/
│   ├── __init__.py
│   ├── server.py                    # ★ FastAPI app; all routes registered here
│   ├── calibration_api.py           # Calibration ingestion endpoint + logic
│   ├── config.py                    # Environment variable loading (OPENAI_API_KEY, DB config, feature flags)
│   ├── db.py                        # Database connection, table creation, insert/query helpers
│   ├── embed.py                     # OpenAI embedding API calls (text-embedding-3-small)
│   ├── grading.py                   # ★ Score range computation (IQR + confidence widening)
│   ├── qa.py                        # Rubric Q&A + feedback suggestion logic (calls LLM)
│   ├── retrieval.py                 # Vector similarity search wrappers (pgvector queries)
│   ├── ingest.py                    # Ingestion router (delegates to format-specific ingestors)
│   ├── ingest_csv.py                # CSV feedback library ingestion
│   ├── ingest_text_file.py          # Plain text file ingestion
│   ├── ingest_structured.py         # Structured JSON-like format ingestion
│   ├── chunking.py                  # Text chunking logic (para-based, token-limited)
│   └── docx_reader.py               # DOCX parsing with heading extraction
│
├── scripts/
│   ├── grade_batch.py               # ★ Batch grading CLI (extraction, quality gates, grading, structural rules)
│   ├── extract_responses.py         # ★ Extract student responses from two-column templates (DOCX/PDF)
│   ├── ingest_week1_assignment.py   # One-time ingestion script for Week 1 assignment prompt
│   └── ingest_week9_assignment.py   # One-time ingestion script for Week 9 assignment prompt
│
├── data/
│   ├── ba101_documents/             # Test fixtures: rubrics, syllabi, style guides
│   │   ├── ba101_style_guide_v1.txt
│   │   ├── ba101_syllabus_2026.txt
│   │   └── feedback_library.csv
│   └── ba101_submissions/           # Sample student submissions for testing
│       ├── week_1/
│       │   ├── raw_submissions/     # Original files from LMS
│       │   └── clean_submissions/   # Extracted/cleaned text for testing
│       └── week_2/
│
├── docs/
│   └── code_map.md                  # ★ Architecture diagram and request flow documentation
│
├── sandbox/
│   └── hello_assistant.py           # OpenAI Assistants API spike (not in use)
│
├── feature_backlog/
│   └── FEATURE_BACKLOG.md           # ★ Prioritized feature backlog with P0/P1/P2 labels
│
├── project_states/
│   └── PROJECT_STATE_FOR_CHATGPT.md # ★ Detailed state summary (341 lines; comprehensive)
│
├── setup-dev-environment/
│   ├── 02_venv_auto_activation.md   # Venv setup instructions
│   └── 03_python_path_verification.md
│
├── artifacts/                        # Batch processing output (gitignored)
│   ├── extraction_store/            # Global extraction outputs (all cleaned student responses)
│   ├── runs/
│   │   └── batches/
│   │       ├── ba101_wk1_full/      # Full 50-submission batch
│   │       │   ├── grading/
│   │       │   │   └── canonical/   # Per-file grading records (*.json)
│   │       │   └── reports/
│   │       │       ├── final/       # batch_report.json (summary stats)
│   │       │       └── debug/       # batch_rollup.jsonl (detailed per-line records)
│   │       └── ba101_wk1_test/      # Test batch (2 files)
│   └── ba101_week1_grades.csv       # ★ CSV export
│
├── code_review_backlog.md           # ★★ Security/compliance issues (MVP blockers noted)
├── TROUBLESHOOTING.md               # Ops runbook for server startup issues
├── README_PRIVATE.md                # Public-facing repo documentation (intentionally minimal)
└── requirements.txt                 # Python dependencies
```

### Central, Fragile, or Recently Modified Files

| File | Role | Status |
|------|------|--------|
| [app/server.py](app/server.py) | FastAPI app; all routes, rate limiting, lifespan events | ★★ Stable, central |
| [app/grading.py](app/grading.py) | Score range computation (IQR + widening heuristics) | ★ Recently modified; feature-flagged |
| [scripts/grade_batch.py](scripts/grade_batch.py) | Batch processor; extraction, quality gates, structural rules | ★★ Central, actively used |
| [app/qa.py](app/qa.py) | LLM prompt construction + feedback generation | ★ Core logic; prompt engineering critical |
| [app/db.py](app/db.py) | DB connection + table creation | ⚠️ Fragile; missing schema constraints (MVP blocker) |
| [code_review_backlog.md](code_review_backlog.md) | Security/compliance issues tracker | ★★★ Critical for hardening roadmap |
| [feature_backlog/FEATURE_BACKLOG.md](feature_backlog/FEATURE_BACKLOG.md) | Prioritized feature requests | ★★ Reference for planning |

---

## 5. Architecture Notes

### High-Level Architecture Decisions Already Made

1. **Embedding-first retrieval:**  
   All grading context is retrieved via vector similarity (cosine distance). No keyword search or full-text fallback. This decision optimizes for semantic relevance but risks missing exact-match queries.

2. **Single rubric per assignment:**  
   Each `assignment_id` maps to exactly one `rubric_id`. Multi-rubric support (e.g., separate content + writing rubrics) is deferred to feature backlog.

3. **Discrete rubric scoring:**  
   Only 3 score levels allowed per rubric category:  
   - **Meets Expectations:** 15 points  
   - **Needs Improvement:** 11.25 points (75% of Meets)  
   - **Does Not Meet:** 0 points  
   Continuous scores or custom point values are not supported.

4. **Calibration as separate table:**  
   Instructor exemplars are stored in `calibration_examples` table, separate from production grades. This enables instructor-specific tone/consistency tracking (future) without polluting main grading data.

5. **Batch-local output:**  
   Each batch produces its own directory hierarchy (`batch_id/extracted/`, `grading/`, `reports/`). No global query interface or database persistence of batch results yet.

6. **Text extraction over OCR:**  
   PDF/DOCX parsing uses `pypdf` and `python-docx`. OCR for scanned PDFs is explicitly deferred; scanned files are flagged as `NEEDS_REVIEW` only.

7. **Paragraph count as sole Adherence rule:**  
   Currently the only structural check is paragraph count (< 3 → downgrade). Other checks (e.g., all questions answered, minimum response per question) are feature backlog.

### Data Flow, API Boundaries, Persistence Layers

#### Ingestion Flow

```
Raw file (.txt/.docx/.pdf)
  → read_text() [extraction method: txt_plain | docx_paragraphs | pdf_pypdf]
    → clean_text() [normalize whitespace, strip bullets]
      → apply_quality_gates() [check min words, content ratio, extraction warnings]
        → Quality Status: OK_FOR_GRADING | OK_FOR_CALIBRATION | NEEDS_REVIEW
          → [Optional] Persist cleaned text to extracted/
```

#### Grading Flow

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

#### Persistence Layer

- **Database:** Supabase Postgres with `pgvector` extension
- **Tables:**
  - `rubric_chunks` – rubric guidance, syllabus, style guides
  - `feedback_library` – instructor-authored feedback examples
  - `calibration_examples` – instructor-graded exemplar submissions
  - `grading_traces` – all grading API requests/responses (for training data collection)
- **Metadata:** All records include `source`, `assignment_id`, `course_id`, `chunk_index`, `created_at`
- **Access:** Vector similarity queries via `app/retrieval.py`; no direct SQL in business logic

### Known Constraints or Intentional Tradeoffs

| Constraint | Rationale | Impact |
|-----------|-----------|--------|
| **Hardcoded quality gates** | Simplicity for MVP; avoids premature config complexity | Cannot tune thresholds per assignment without code change |
| **No OCR** | OCR adds latency + cost; scanned PDFs are rare in target courses | Scanned submissions require manual intervention |
| **In-memory rate limiting** | Avoids Redis/external dependency for MVP | Rate limits reset on server restart; not suitable for multi-instance |
| **No authentication** | Trusted internal use only; instructor runs server locally | Not production-ready; cannot expose to internet |
| **Batch-local output** | Simplifies debugging; avoids premature database design | No global query interface; must manually inspect directories |
| **Single LLM provider (OpenAI)** | Focus on quality over flexibility | Vendor lock-in; cost risk if usage scales |

---

## 6. Known Issues, Risks, or Tech Debt

### Bugs, Limitations, or Areas That Feel Shaky

**Documented in [code_review_backlog.md](code_review_backlog.md):**

#### MVP Blockers (High Risk)
1. **Missing DB schema constraints:** No `UNIQUE` or `NOT NULL` constraints on tables; risk of duplicate/malformed data
2. **Hallucinated citations:** LLM may return citation labels ([R1], [F1]) not present in retrieved context; no validation check
3. **Partial-persisted state on failure:** Ingestion lacks transactional rollback; crash mid-batch leaves inconsistent data

#### Post-MVP Priorities
1. **SQL injection & input validation:** Minimal validation of user inputs; DB queries not fully parameterized
2. **PII exposure in logs:** Raw student submissions may appear in application logs or DB audit records without redaction
3. **Secrets hardening:** `.env` file not validated on startup; risk of leaking secrets in error messages

### Temporary Hacks or TODOs That Matter

**In code:**
- **One TODO in [app/server.py:273](app/server.py#L273):**  
  ```python
  grader_id=None,  # TODO: extract from auth if available
  ```
  **Impact:** Cannot attribute grading decisions to specific instructors/TAs yet.

**Known heuristic risks:**
- **Bullet stripping in text extraction:** `_strip_leading_bullets()` removes `?`, `•`, `-`, etc. May strip valid content markers in edge cases (e.g., dialog, Q&A format).
- **PDF boilerplate removal:** Regex patterns target known templates; may miss novel header/footer patterns or incorrectly remove valid content.

### Scaling, Security, or Correctness Concerns Already Identified

**Scaling:**
- **No batch timeout or resumption logic:** Long batches (100+ files) may timeout; no checkpoint + resume mechanism.
- **In-memory rate limiting:** Cannot scale to multiple server instances without shared state (Redis).

**Security:**
- **No authentication/authorization:** Anyone with server URL can call grading API (acceptable for local/internal use; blocker for public deployment).
- **Prompt injection risk:** User-provided submission text is directly embedded in LLM prompt; no sanitization or safety controls.

**Correctness:**
- **Paragraph count heuristic may be too aggressive:** Some high-quality submissions may have dense single paragraphs; current rule penalizes these without nuance.
- **Score range computation assumes normal distribution:** IQR-based ranges work well for symmetric distributions but may be misleading for skewed grade distributions.

---

## 7. Planned Next Steps

### What I Believe the Next 3–5 Steps Should Be

1. **[Immediate] Generate CSV export for instructor review**  
   Convert `batch_rollup.jsonl` to CSV with columns: `filename`, `score_low`, `score_high`, `suggested_feedback`, `structural_adjustments`, `adherence_score`. This enables efficient spreadsheet-based review.

2. **[MVP Blocker] Add DB schema constraints**  
   - Add `UNIQUE` constraints on `(assignment_id, chunk_index)` for rubric chunks  
   - Add `NOT NULL` constraints on `source`, `assignment_id`, `course_id`  
   - Create migration script (SQL) and document rollback plan  
   - Test with existing data to ensure no violations

3. **[MVP Blocker] Implement hallucinated citations check**  
   - After LLM response, validate that all citation labels ([R1], [F1], [C1]) exist in retrieved context  
   - If hallucination detected: log warning, strip invalid citations from feedback, flag record as `needs_review`  
   - Add unit tests for citation validation logic

4. **[Post-MVP] Add rubric versioning**  
   - Add `rubric_version` and `rubric_created_at` columns to rubric table  
   - Store `rubric_version` in grading traces for audit trail  
   - Design manifest file (`data/rubrics/assignment_rubric_map.json`) to resolve `(course, assignment_id, week) → rubric_version`

5. **[Post-MVP] Systemic PII redaction**  
   - Add `--anonymize` flag to batch processor to redact student names/IDs from logs  
   - Implement PII detection regex (names, emails, IDs) in `app/ingest.py`  
   - Log redactions as warnings for instructor review

### Any Forks in the Road Where Multiple Approaches Exist

**Fork 1: Rubric versioning implementation**
- **Approach A:** Add `rubric_version` column to existing tables; backfill with `v1` for legacy data  
  - **Pros:** Simple; minimal code change  
  - **Cons:** No audit trail for when rubric changed; cannot compare grades across versions  
- **Approach B:** Create separate `rubric_versions` table with `(rubric_id, version, created_at, deprecated_at)`  
  - **Pros:** Full audit trail; supports rubric evolution over time  
  - **Cons:** More complex schema; requires foreign key constraints

**Fork 2: Paragraph count rule refinement**
- **Approach A:** Keep current rule (< 3 → downgrade) but make threshold configurable per assignment  
  - **Pros:** Preserves existing logic; adds flexibility  
  - **Cons:** Still binary; doesn't account for paragraph density  
- **Approach B:** Replace paragraph count with "completeness check" (e.g., verify response length per question)  
  - **Pros:** More nuanced; avoids false positives  
  - **Cons:** Requires parsing assignment questions; complex to generalize

**Fork 3: Score range presentation**
- **Approach A:** Keep current labeling ("Range based on N graded calibration examples, [low/high] confidence")  
  - **Pros:** Transparent; shows sample size  
  - **Cons:** May mislead instructors into thinking it's a confidence interval  
- **Approach B:** Change to "Typical score range based on similar past submissions"  
  - **Pros:** Clearer intent; avoids statistical jargon  
  - **Cons:** Loses transparency about sample size

---

## 8. What ChatGPT Should Review or Challenge

### Assumptions I May Be Making

1. **Assumption:** Paragraph count is a reliable proxy for submission completeness.  
   **Challenge:** What if students write comprehensive responses in 1–2 dense paragraphs? Should the rule account for paragraph density (words per paragraph) instead of raw count?

2. **Assumption:** IQR-based score ranges are meaningful and actionable for instructors.  
   **Challenge:** Are instructors interpreting these ranges as "acceptable variation" or "grader uncertainty"? Should we test alternative presentations (e.g., median + confidence level)?

3. **Assumption:** Calibration examples should be filtered by `assignment_id` only (not by `course_id` or `week`).  
   **Challenge:** Should calibration be more granular (e.g., per-instructor per-assignment) or more general (e.g., course-wide)?

4. **Assumption:** Discrete 3-level scoring is sufficient for all rubric categories.  
   **Challenge:** Some categories (e.g., Writing Quality) may benefit from finer gradations (5-point scale). Should rubric schema support variable scoring levels?

5. **Assumption:** Batch processing should fail if output directory already exists (unless `--overwrite`).  
   **Challenge:** Is this too conservative? Should batches support incremental processing (e.g., skip already-graded files)?

### Design Choices I Want a Second Opinion On

1. **Calibration confidence heuristics ([app/grading.py:85-95](app/grading.py#L85-L95)):**  
   Current widening rules:
   - Sample size < 3 → very wide range  
   - Sample size 3–5 → moderate widening  
   - Sample size > 8 → tight range  
   **Question:** Are these thresholds arbitrary? Should widening be parameterized or data-driven (e.g., based on actual variance)?

2. **Paragraph count penalty severity:**  
   Current: < 3 paragraphs → downgrade from 15 to 11.25 (25% penalty).  
   **Question:** Is this penalty too harsh? Should it be 10% (13.5) or graduated based on paragraph count (1 para → 0 points, 2 para → 11.25)?

3. **Citation label scheme (`[R1]`, `[F1]`, `[C1]`):**  
   **Question:** Are these labels clear to instructors? Should we use full labels (`[Rubric-1]`, `[Feedback-1]`, `[Calibration-1]`) or icons?

4. **Quality gate thresholds (min_words=30, min_ratio=0.2):**  
   **Question:** Are these values appropriate for all assignment types? Should reflections have different thresholds than case studies?

5. **Batch output structure (local directories vs. database):**  
   Current: Each batch outputs JSON files to `artifacts/runs/batches/{batch_id}/`.  
   **Question:** When should we transition to database persistence? What's the right trigger (e.g., batch count > 10, multi-instructor use, need for global queries)?

### Areas Where Alternative Approaches Might Exist

1. **Text extraction:**  
   Current: `pypdf` + `python-docx` (basic parsing).  
   **Alternative:** Use `pdfplumber` for table-aware PDF extraction or `textract` for robust cross-format support.  
   **Tradeoff:** More dependencies + complexity vs. better extraction quality.

2. **Embedding model:**  
   Current: OpenAI `text-embedding-3-small`.  
   **Alternative:** Use open-source models (e.g., `sentence-transformers`) or domain-specific embeddings.  
   **Tradeoff:** Cost/latency vs. control/privacy.

3. **LLM provider:**  
   Current: OpenAI GPT-4.  
   **Alternative:** Use Anthropic Claude (better instruction following), Azure OpenAI (enterprise compliance), or open-source models (e.g., Llama).  
   **Tradeoff:** Quality vs. cost vs. privacy.

4. **Rate limiting:**  
   Current: In-memory per-IP counter.  
   **Alternative:** Use Redis for distributed rate limiting or API gateway (e.g., Kong, AWS API Gateway).  
   **Tradeoff:** Simplicity vs. scalability.

5. **Batch processing:**  
   Current: Synchronous CLI script (`grade_batch.py`).  
   **Alternative:** Use async task queue (e.g., Celery, RQ) or serverless functions (e.g., AWS Lambda).  
   **Tradeoff:** Simplicity vs. fault tolerance vs. scalability.

---

## Appendix: Relevant Code Snippets

### Score Range Computation ([app/grading.py:43-95](app/grading.py#L43-L95))

**Why relevant:** This is the core logic for calibration-based score ranges. Heuristics for widening are critical to review.

**What question it helps answer:** Are the confidence adjustments reasonable? Should sample-size thresholds be configurable?

```python
def compute_score_range_from_calibration_hits(
    calibration_hits: List[Dict[str, Any]],
    points_possible: float = 40.0,
) -> Tuple[Optional[float], Optional[float], str]:
    """
    Returns: (score_low, score_high, explanation_text)
    Uses ONLY grade_numeric values from calibration hits (deterministic).
    - Base range uses IQR: [p25, p75]
    - Widens range when sample is small or distances suggest low similarity
    - Clamps to [0, points_possible]
    """
    # ... (see file for full implementation)
    
    # Widening rules (MVP-friendly):
    widen = 0.0
    if n == 3:
        widen += 0.18 * pts  # 18% of points_possible
    elif n <= 5:
        widen += 0.12 * pts  # 12%
    elif n <= 8:
        widen += 0.06 * pts  # 6%
    # else: n > 8, no sample-size widening
    
    # Distance-based widening
    if avg_dist is not None:
        if avg_dist > 0.4:
            widen += 0.10 * pts  # 10%
        elif avg_dist > 0.3:
            widen += 0.05 * pts  # 5%
```

### Structural Rules Application ([scripts/grade_batch.py:109-126](scripts/grade_batch.py#L109-L126))

**Why relevant:** This implements the paragraph count downgrade rule. Penalty severity and applicability scope are design decisions to review.

**What question it helps answer:** Is the 25% penalty appropriate? Should this rule apply to all assignments or only some?

```python
def apply_structural_rules(grade_data: Dict[str, Any], paragraph_count: int) -> Tuple[Dict[str, Any], List[str]]:
    """Apply deterministic structural rules to grading output.
    
    If paragraph count < 3, downgrade Adherence from Meets Expectations (15) to Needs Improvement (11.25).
    Returns adjusted grade_data and list of adjustments applied.
    """
    adjustments: List[str] = []
    adjusted_data = grade_data.copy()
    
    if paragraph_count < 3:
        score_high = grade_data.get("score_high")
        if score_high is not None and score_high >= 15:
            adjusted_data["adherence_score"] = 11.25
            adjusted_data["adherence_original"] = score_high
            adjustments.append(f"adherence_downgraded_paragraphs:{paragraph_count}")
    
    return adjusted_data, adjustments
```

### Citation Extraction Logic ([app/qa.py](app/qa.py))

**Why relevant:** Citations are critical for transparency. Hallucination risk is high; validation logic should be reviewed.

**What question it helps answer:** How can we detect and handle hallucinated citations?

**Note:** Full code not shown here; see [app/qa.py](app/qa.py) for prompt construction and citation parsing.

---

## Summary

**This document provides:**
- Comprehensive project overview and maturity assessment
- Complete inventory of implemented features and known gaps
- Architecture decisions, constraints, and tradeoffs
- Known issues, tech debt, and security risks
- Planned next steps with alternative approaches
- Specific design questions for technical review

**ChatGPT should use this document to:**
- Validate architectural decisions
- Challenge assumptions about scoring, calibration, and structural rules
- Propose alternative approaches to known issues
- Identify blind spots or unconsidered risks
- Recommend prioritization of MVP blockers vs. feature backlog

**End of handoff summary.**
