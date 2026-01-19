# Feature Backlog

## Grading Logic

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

## Rubrics

**P0: Rubric resolution mechanism**
- Currently hardcoded assignment_id → rubric_id flow. Need robust resolution: (course_id, assignment_id, week) → rubric version.
- Store in a manifest or lookup table (e.g., in `data/` or Supabase).

**P0: Rubric versioning**
- No mechanism to track which submissions were graded with which rubric version.
- Add rubric_version to batch metadata and grading record.

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

**P1: Instructor-specific calibration library**
- Support per-instructor calibration sets: instructor can flag exemplar submissions for training/consistency.
- Store calibration examples separately from production grades.

**P1: Calibration consistency tracking**
- Track grader score range for same submission across calibration vs. production to measure drift.

**P2: Calibration audit trail**
- When instructor reviews a submission marked for calibration, log feedback, accept/reject, and impact on grader thresholds.

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
