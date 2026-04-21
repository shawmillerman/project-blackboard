# Feature Backlog

## Recently Completed

- DOCX table response paragraph preservation
	- Table-cell inner paragraphs now preserved by converting single `\n` to double `\n\n` during extraction so student paragraph breaks are retained.
	- Change: [scripts/grade_batch.py](scripts/grade_batch.py)

- Calibration review shows cleaned student text (not boilerplate)
	- During review, if `grade.input` contains assignment boilerplate, it is replaced with the cleaned extraction text for display and calibration payloads.
	- Change: [scripts/calibration_review.py](scripts/calibration_review.py)

- Rubric-as-Code documentation
	- Created comprehensive philosophy/marketing document and added Syllabus-as-Code section with data model and integration plan.
	- Files: [RUBRIC_AS_CODE.md](RUBRIC_AS_CODE.md)

- Quality gates tuned
	- `min_ratio` lowered to 0.15 (2026-01-19) to reduce false negatives on shorter PDF extractions; documented in code.
	- Change: [scripts/grade_batch.py](scripts/grade_batch.py)

## Grading Logic

**P0: Course-material usage scoring policy**
- New policy: If a response clearly does not use course materials (e.g., no textbook/Chapter references or domain concepts), cap the relevant component at 11.25 (Needs Improvement). If the response is a one-word/no answer/incomplete sentence, cap at 7.5 (Did Not Meet).
- Scope: Define detection signals (keyword/citation presence, concept usage), integrate into component scoring (primarily Content), and surface rationale in feedback.
- Tasks:
	- Implement detection heuristics (keywords/citations) with clear, overrideable flags.
	- Add explicit feedback note when deduction applied (transparency for students).
	- Add toggle/config per assignment to enable/disable this rule.
	- Update documentation and calibration review prompts to reflect policy.

**P0: Rubric version tagging and migration plan**
- Store `rubric_version` in grading traces, calibration examples, and batch metadata. Resolve rubric by (institution_id, course_id, assignment_id, term_id) → rubric_id + rubric_version.
- Provide CLI or documented flow to re-grade an existing batch with a new rubric version (`--overwrite`), with audit trail.
- Tasks:
	- Add `rubric_version` to API responses and persistence.
	- Document upgrade path and re-grade decision checklist.
	- Display rubric_version in calibration review header for clarity.

**P0: Paragraph count rule edge cases**
- Currently only checks if < 3 paragraphs. Need to handle edge cases: empty paragraphs, single-word stubs, heavily boilerplate-stripped submissions.
- May need tunable threshold per assignment (not hardcoded to 3).

**P0: Deterministic rule documentation in feedback**
- When paragraph count downgrades Adherence from Meets to Needs Improvement, include explicit explanation in feedback so students understand why.
- Currently adjusts score silently; should surface reason to instructor.

**P0: Rubric compliance validator**
- Add pre-grading check to ensure grader response matches expected rubric structure (3 categories, only 100/75/50 allowed).
- Reject non-compliant responses before persistence.

**P1: Grading response schema versioning**
- Document expected fields from `/tier2/feedback-suggest` (e.g., `score_high`, `score_low`, `citations`, `rubric_id`, `assignment_id`).
- Handle gracefully if response schema changes or fields are missing.

**P1: Quality gate thresholds as config**
- Hardcoded min_words=30, min_ratio=0.2 should be tunable per assignment/course.
- Load from rubric metadata or batch config.

**P1: Content vs. structural checks separation**
- Currently only paragraph count triggers Adherence downgrade. Future: add other structural checks (all questions answered, answer present for each prompt) without conflating with content quality.

**P2: Explain-ability for Adherence downgrade**
- When downgrade occurs, include a short audit trail in the record: original score, rule triggered, count/evidence.
- Support instructor "override" or "dismiss" in future UI.

## Multi-Institution & Dimensional Scoping

**P0: Institution ID scoping (hard stop for multi-tenant)**
- Currently no institution/school field; all data assumed single institution (Portland CC).
- Add `institution_id` as mandatory scoping field in calibration_examples, rubrics, grading_traces to prevent inter-institutional data mixing.
- All retrieval queries must filter by institution_id (not optional); enforce in schema with NOT NULL + index.
- Update API request payloads to accept `institution_id` (optional per user, default per tenant).

**P0: Term / Academic Year tracking**
- Currently no term or semester scoping; same assignment_id reused across years with potentially different rubric versions.
- Add `term_id` (e.g., "fall_2025", "spring_2026") and `academic_year` to calibration, rubrics, batch metadata, and grading_traces.
- Prevent silent rubric drift by associating rubric_version with term_started + term_ended; audit trail shows which rubric version was active per term.
- Retrieval logic should respect term boundaries (optionally include current term + immediate prior term for fallback).

**P0: Rubric version metadata (complete)**
- Add to rubrics table: `rubric_version`, `rubric_status` ("active"|"deprecated"|"draft"), `rubric_created_at`, `rubric_deprecated_at`.
- Store `rubric_version` in grading_traces and calibration_examples for full audit trail (answers "which rubric version graded this submission?").
- Manifest-driven resolution: (institution_id, course_id, assignment_id, term_id) → rubric_id + rubric_version.

**P0: Grader / Instructor ID capture**
- Currently `grading_traces.grader_id` always NULL; not captured from API.
- Add `grader_id` to `/tier2/feedback-suggest` request payload (optional); store in grading_traces and calibration_examples metadata.
- Enables instructor-specific drift detection and instructor-scoped calibration retrieval (optional feature).

**P1: Department / Program scoping**
- Add `department_code` or `department_id` to rubrics, calibration metadata, and grading_traces.
- Prevents cross-department calibration leakage in multi-department institutions (e.g., Business vs. Engineering).
- Optionally filter calibration retrieval by department.

**P1: Section / Cohort / Modality separation**
- Add optional `section_id`, `modality` ("in-person"|"online"|"hybrid"), or `cohort_id` to calibration metadata and batch records.
- Allows cohort-specific calibration if grading standards differ by modality (e.g., online students may have different engagement expectations).
- Optional filter in retrieval logic.

**P1: Campus / Location scoping**
- Add `campus_id` or `campus_code` to batch metadata, calibration metadata, and grading_traces (for multi-campus institutions).
- Data privacy + audit trail: ensures submissions from Campus A cannot accidentally be graded using Campus B's calibration.

**P2: Calibration confidence tier (evidence level)**
- Add `calibration_confidence` or `evidence_level` ("exemplar"|"typical"|"draft"|"consensus") to calibration metadata.
- "exemplar" = single instructor, high confidence; "typical" = multiple submissions, consistent; "draft" = unreviewed; "consensus" = 3+ instructor agreement.
- Use in retrieval: optionally weight or filter by confidence tier; prevent low-confidence anchors from dominating small top-k sets.

**P2: Student ID / Anonymization mapping**
- Add `student_id` or `student_anon_id` to grading_traces (for longitudinal tracking).
- Support stable anonymization scheme for privacy/FERPA compliance (see Analytics & Insights).
- Batch metadata should include student_id mapping table or manifest.

**P2: Delivery method / Synchronicity**
- Add `delivery_method` ("synchronous"|"asynchronous"|"hybrid") to calibration metadata and batch context.
- Async courses may have different feedback expectations; optional filter in retrieval to avoid cross-method contamination.

## Rubrics

**P0: Syllabus-as-Code (MVP)**
- Encode course learning outcomes (LOs) as structured config (JSON) with week mapping, detection signals, and success criteria.
- Compute LO-alignment per submission and include in grading traces and calibration metadata.
- Tasks:
	- Create `docs/syllabus_ba101.json` with LOs and signals.
	- Load syllabus in app config; pass into grading.
	- Return `learning_outcomes_alignment` in API response; show in calibration review.
	- Document instructor workflow and reporting.

**P0: Rubric resolution mechanism**
- Currently hardcoded assignment_id → rubric_id flow. Need robust resolution: (institution_id, course_id, assignment_id, term_id) → rubric_id + rubric_version.
- Store in a manifest or lookup table (e.g., `data/rubric_manifest.json` or Supabase table).
- Include term bounds so historical queries return correct rubric version.

**P0: Rubric versioning (see Multi-Institution section for full spec)**
- Add rubric_version, rubric_status, rubric_created_at, rubric_deprecated_at to rubrics table.
- Store rubric_version in batch metadata and grading_traces; all calibration examples tagged with rubric_version for audit trail.

**P1: Rubric definition storage**
- Currently rubric is ad-hoc prose. Migrate to structured format (YAML/JSON) in `data/rubrics/`.
- Include category, score levels, point values, descriptors, and metadata (author, created_date, deprecated_date).

**P1: Rubric validation and linting**
- Ensure all rubrics follow the structure (exactly 3 score levels, point values match, categories well-defined).
- Run on startup or on explicit `validate` CLI command.

**P2: Multi-rubric assignments**
- Support assignments graded against multiple rubrics (e.g., content rubric + writing rubric).
- Currently assumes one rubric per assignment_id.

## Calibration

**P0: Calibration opt-in enforcement**
- Current flag `calibration_opt_in` is in code but not integrated with server grading flow.
- Define when/how a submission is marked OK_FOR_CALIBRATION vs OK_FOR_GRADING.

**P0: Week-first calibration fallback (assignment-safe)**
- Ensure each week has its own calibration set; use course-level calibration only when that week has fewer than 3 anchors.
- When falling back, require rubric_id and rubric_version alignment (or explicit allowlist) to prevent cross-assignment contamination.
- When no calibration exists, fall back to `feedback_library` (generic examples) and log the fallback path for auditability.
- Add guardrails/tests so cross-week anchors stop being used once week-level coverage is sufficient.

**P0: Calibration ingest completeness for scoring**
- Require `grade_numeric` for calibration ingestion (or exclude ungraded examples from range calculations) and reject obviously invalid submissions/feedback (too short, empty).
- Enforce rubric-aligned metadata (`assignment_id`, `rubric_id`, `rubric_version`) on ingest to keep anchors scoped.

**P0: Calibration hit quality guardrails**
- Deduplicate calibration hits (by normalized submission text and source/chunk) and drop hits beyond a max distance threshold; optionally weight anchors by similarity when building prompts.
- Prevent small top-k sets from being dominated by near-duplicates or weak matches.

**P0: Component score propagation**
- Ensure `component_scores` stored in calibration metadata are surfaced to scoring logic so `compute_component_score_ranges` uses real component data instead of falling back to full ranges.
- Add a small adapter to lift metadata into top-level fields (or update the function to read from metadata).

**P1: Stable score ranges from full calibration set**
- Compute score ranges from the full graded calibration set for the assignment (and optionally course) instead of only the retrieved top-k; keep retrieval for prompt context but use aggregate stats for ranges.
- Reduces noise/drift when retrieval returns a narrow or unrepresentative subset.

**P1: Instructor-specific calibration library**
- Support per-instructor calibration sets: instructor can flag exemplar submissions for training/consistency.
- Store calibration examples separately from production grades.

**P1: Calibration consistency tracking**
- Track grader score range for same submission across calibration vs. production to measure drift.

**P2: Calibration audit trail**
- When instructor reviews a submission marked for calibration, log feedback, accept/reject, and impact on grader thresholds.

**P1: Refresh feedback_library with cross-week exemplars**
- Periodically rebuild `feedback_library` using curated exemplars from all weeks (once calibration coverage is stable per week).
- Include provenance metadata (week, assignment_id, batch_id) and re-embed the library so retrieval stays current.
- Add a repeatable script/notebook to pull from `calibration_examples` → `feedback_library` with versioned dumps.

## Ingestion & Extraction

**P0: Heuristic robustness of bullet/glyph stripping**
- `_strip_leading_bullets()` removes `?`, `•`, `-`, etc. Risk: may strip valid content markers in some edge cases (e.g., dialog, lists).
- Validate against real submissions; add opt-out for specific file types or patterns.

**P0: PDF boilerplate removal improvements**
- Current approach: regex patterns + keyword blocklist. Miss cases: repeated headers/footers across pages, merged columns, OCR artifacts.
- Investigate pdfplumber or PyMuPDF for better layout awareness (P2 task).

**P1: Extraction method audit trail**
- Track extraction method (pdf_pypdf, docx_paragraphs, txt_plain) and warnings (boilerplate removed, bullets stripped).
- Surface in batch report so instructors can inspect quality.

**P1: Manifest-driven ingestion**
- Support optional `submissions.json` manifest in batch folder: filename → student_id, course_id, week, etc.
- Fall back to heuristic parsing if manifest absent.

**P1: Quality gate aggregation**
- Compute per-batch statistics: % extracted cleanly, % needing review, distribution of cleaning warnings.
- Include in batch_report.json.

**P2: OCR for image-based PDFs**
- Detect scanned vs. text PDFs; conditionally apply tesseract.
- Decision: initially NO OCR by default; flag scanned PDFs as NEEDS_REVIEW.

## Batch Processing

**P0: Batch idempotency guarantees**
- Current: fail if output exists unless `--overwrite`. Verify: are per-file outputs truly skipped on re-run, or are they merged/duplicated?
- Add idempotency test: run same batch twice, verify identical output (byte-for-byte).

**P0: Dry-run completeness**
- Currently dry-run extracts and quality-gates but does NOT call grader. Is this intended? Document and test.
- Consider: should dry-run also do a test grading call (with a dry-run flag to the server)?

**P1: Batch report enhancements**
- Include per-category score distribution (e.g., how many "Meets", "Needs Improvement" per rubric category).
- List top extraction warnings and NEEDS_REVIEW reasons to guide instructor follow-up.

**P1: Atomic batch writes**
- Currently per-file writes are independent. If batch processing crashes mid-way, recovery is manual.
- Consider: write to temp dir, then atomic move to final batch_id folder on completion.

**P1: Batch status tracking**
- Support querying batch status: in-progress, completed, failed, needs-review-items.
- Store in Supabase or simple JSON file for resumability.

**P2: Batch timeout and resumption**
- Long batches (100+ files) may timeout. Support checkpoint + resume logic.

## Instructor Experience (Future)

**P1: Explainability dashboard**
- Show instructor: per-submission score breakdown, which rules triggered Adherence downgrade, citations used.
- Link back to extracted text and grader feedback.

**P1: Tone and feedback control**
- Rubric descriptors mention "encouraging" vs "critical" tone. Support instructor preference in prompt engineering.
- Store tone_style per course; apply to feedback generation.

**P1: Plagiarism and collusion detection**
- Add optional integration: flag suspiciously similar submissions.
- Mark as NEEDS_REVIEW for manual inspection.

**P2: Bulk feedback review and annotation**
- UI for instructor to tag batches with lessons learned, common misconceptions, rubric clarifications.
- Export as feedback library for next cohort.

## Analytics & Insights

**P2: Longitudinal student performance tracking (data prerequisites)**
- Support tracking the same student across multiple assignments/weeks (requires stable student_id or anon_id mapping).
- Store per-submission: student_id, assignment_id, week, all rubric category scores, points earned, feedback flags.
- Ensure rubric scoring is consistent across batches (same rubric version, same grader model config).

**P2: Trend detection for student performance**
- Implement logic to classify trend: improving (scores increasing), declining (scores decreasing), flat (consistent), inconsistent (oscillating).
- Compute trend over week-to-week assignments (e.g., Adherence scores for weeks 1–10).
- Generate per-student summary: trend direction, volatility, and median score per rubric category.

**P2: Cohort-level performance aggregation**
- Summarize class performance: distribution of scores by rubric category per week.
- Identify common weak areas (e.g., "Writing style mostly Needs Improvement in weeks 1–3").
- Support filtering by performance band (e.g., "top 25%, middle 50%, bottom 25%").

**P2: Performance report generation (non-UI)**
- Export student performance timelines as CSV or JSON: (week, assignment, student_id, category, score, feedback_summary).
- Generate instructor summaries: "X students improved, Y students declined, Z students consistent."
- Include caveats: rubric version, grader model version, sample size.

**P2: Dependencies and prerequisites**
- Requires P0 completion: rubric versioning, consistent student tracking, stable grading outputs.
- Do NOT use this feature for automated interventions (e.g., flagging students for retake). Use only for instructor reflection.
- Disable this feature if rubric versions mismatch across batch (warn instructor).

## Operational / Reliability

**P0: Supabase project paused detection**
- Currently DB init failures are cryptic. Add explicit check: on startup, try connection with helpful error message if paused.
- Document in TROUBLESHOOTING.md how to resume.

**P0: Connection diagnostics**
- Add `--check-db` flag to verify Supabase connectivity before running batch.
- Include DNS, SSL, auth checks.

**P1: Batch failure recovery**
- If grading server goes down mid-batch, support `--resume <batch_id>` to continue from last successful file.

**P1: Logging and audit trail**
- Currently INFO/WARNING logs. Add structured logging (JSON) with request_id per submission for tracing.
- Rotate logs per batch; store in batch folder.

**P1: Error message clarity**
- Many errors are generic (e.g., "extraction_method: X"). Add context: file size, format, specific extraction phase.
- Include suggestions (e.g., "file too small, check if corrupted").

**P2: Metrics and observability**
- Track: batch throughput (submissions/min), grader latency distribution, success rate by file type.
- Export to simple CSV or integrate with monitoring tool.

**P2: Database migration safety**
- Current schema includes rubric_id, assignment_id per submission. Ensure all existing submissions get tagged on upgrade.
- Test rollback scenario.

## Development Workflow & Quality

**P2: Pre-commit hooks**
- Install pre-commit framework with black (formatter), flake8 (linter), mypy (type checker)
- Add hooks for: check-added-large-files, detect-private-key, check-merge-conflict
- Prevents common mistakes before commits reach remote
- Config file: .pre-commit-config.yaml

**P2: CI/CD Pipeline**
- GitHub Actions workflow to run tests on push/PR
- Run pytest suite, linting checks, type checking
- Provide pass/fail status badges on PRs
- Config file: .github/workflows/test.yml
- Blocks merge if tests fail (optional enforcement)

**P2: Branch protection rules**
- Require PR review before merge to main
- Require CI checks to pass
- Enforce linear history (rebase only)
- No direct commits to production branches
