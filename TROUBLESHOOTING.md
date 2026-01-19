# Troubleshooting

This project depends on:
- A Python virtual environment (.venv)
- Environment variables loaded from .env
- A reachable Postgres database (Supabase)
- Uvicorn + FastAPI startup (lifespan runs DB checks)

When the server fails to start, follow this checklist in order.

> This document is a troubleshooting runbook.
> Only run the commands in the section that matches your current problem.
> Do not run everything top to bottom.


---

## 0) Confirm you are in the repo root

You should see: app/, .env, .venv, requirements.txt.

```bash
pwd
ls


1) Activate the virtual environment

If your prompt does not show (.venv), activate it:

source .venv/bin/activate
which python
python --version

2) Start the server the reliable way

Prefer module invocation so you use the venv’s packages:

python -m uvicorn app.server:app --reload


## Incident log
- 2025-01-13: Supabase project auto-paused, DB host stopped resolving

---

## Monitoring Assessment Workflow runs

- Uvicorn runs continuously; it does not print a final “OK”. Long gaps can occur while grading calls to `/tier2/feedback-suggest` complete.

Quick progress checks:

```bash
# Tail per-file rollup (appears during batch runs)
tail -n 10 artifacts/runs/batches/<batch_id>/reports/debug/batch_rollup.jsonl

# Count canonical grading records written so far
ls -1 artifacts/runs/batches/<batch_id>/grading/canonical | wc -l

# Check final batch summary when available
cat artifacts/runs/batches/<batch_id>/reports/final/batch_report.json
```
---

## Quality Gates: "NEEDS_REVIEW" Files

**Issue:** Files flagged as `NEEDS_REVIEW` due to `short_ratio` threshold.

**Root Cause:** PDFs with heavy boilerplate (headers, footers, instructions) can have low retention ratios even when student responses are valid. Example: 1764 chars raw → 345 chars cleaned = 19.5% ratio.

**Quality Gate Thresholds (2026-01-19):**
- `min_words`: 30 words (rejects extremely short responses)
- `min_ratio`: 0.15 (15% retention after boilerplate removal)

**Why 0.15?** Allows concise but complete responses. Previous threshold of 0.20 was too strict, flagging valid 3-paragraph submissions as NEEDS_REVIEW.

**Investigation Steps:**
1. Check cleaned text: `cat artifacts/extraction_store/{filename}_extracted.txt`
2. Verify word count and paragraph structure
3. If content is valid, file will pass with current threshold
4. If still flagged, lower `min_ratio` in `apply_quality_gates()` function

**To reprocess flagged files:**
```bash
# Find needs_review files
python -c "from pathlib import Path; import json; [print(json.load(open(f))['original_filename']) for f in Path('artifacts/runs/batches/{batch_id}/grading/canonical').glob('*.json') if json.load(open(f))['status'] == 'needs_review']"

# Re-run with updated threshold
python scripts/grade_batch.py {directory} --batch-id {batch_id} --grade --overwrite
```