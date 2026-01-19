# Repo Refactor Checklist

**Goal:** Remove all references to `out/` and `experiments/`, establish new defaults for `artifacts/` and `sandbox/`

---

## Phase 1: Directory Rename

### 1.1 Rename experiments/ → sandbox/

**Action:**
```bash
mv experiments sandbox
```

**Files to move:**
- `experiments/hello_assistant.py` → `sandbox/hello_assistant.py`

**Status:** ⬜ Not started

---

## Phase 2: Update Scripts (Defaults & References)

### 2.1 scripts/grade_batch.py

**Lines 143-148: Update directory structure**

**Current:**
```python
def run_batch(args: argparse.Namespace) -> Dict[str, Any]:
    batch_root = Path(args.output_root) / args.batch_id
    extracted_dir = batch_root / "extracted"
    grading_dir = batch_root / "grading"
    reports_dir = batch_root / "reports"
    records_dir = reports_dir / "records"
    rollup_path = reports_dir / "batch_rollup.jsonl"
```

**New:**
```python
def run_batch(args: argparse.Namespace) -> Dict[str, Any]:
    batch_root = Path(args.output_root) / args.batch_id
    grading_dir = batch_root / "grading"
    grading_intermediate_dir = grading_dir / "intermediate"
    grading_canonical_dir = grading_dir / "canonical"
    reports_dir = batch_root / "reports"
    reports_final_dir = reports_dir / "final"
    reports_debug_dir = reports_dir / "debug"
    rollup_path = reports_debug_dir / "batch_rollup.jsonl"
```

**Lines 164-165: Update directory creation**

**Current:**
```python
    if not args.dry_run:
        for d in (extracted_dir, grading_dir, reports_dir, records_dir):
            d.mkdir(parents=True, exist_ok=True)
```

**New:**
```python
    if not args.dry_run:
        for d in (grading_intermediate_dir, grading_canonical_dir, reports_final_dir, reports_debug_dir):
            d.mkdir(parents=True, exist_ok=True)
```

**Lines 209-210: Remove extracted directory logic**

**Current:**
```python
            cleaned_path = extracted_dir / f"{path.stem}_extracted.txt"
            persist_cleaned_text(cleaned_text, cleaned_path, args.overwrite)
            record["cleaned_text_path"] = str(cleaned_path)
```

**New:**
```python
            # Extraction now writes to global artifacts/extraction_store/
            extraction_store = Path("artifacts/extraction_store")
            extraction_store.mkdir(parents=True, exist_ok=True)
            cleaned_path = extraction_store / f"{path.stem}_extracted.txt"
            persist_cleaned_text(cleaned_text, cleaned_path, args.overwrite)
            record["cleaned_text_path"] = str(cleaned_path)
```

**Lines 234-235: Update record persistence path**

**Current:**
```python
            persist_record(record, records_dir / f"{path.stem}.json", args.overwrite)
```

**New:**
```python
            persist_record(record, grading_canonical_dir / f"{path.stem}.json", args.overwrite)
```

**Lines 245-246: Update record persistence path (error case)**

**Current:**
```python
                try:
                    persist_record(record, records_dir / f"{path.stem}.json", args.overwrite)
```

**New:**
```python
                try:
                    persist_record(record, grading_canonical_dir / f"{path.stem}.json", args.overwrite)
```

**Lines 260-262: Update batch report path**

**Current:**
```python
        report_path = reports_dir / "batch_report.json"
        report_path.write_text(json.dumps(batch_report, indent=2), encoding="utf-8")
```

**New:**
```python
        report_path = reports_final_dir / "batch_report.json"
        report_path.write_text(json.dumps(batch_report, indent=2), encoding="utf-8")
```

**Lines 285: Update default output-root**

**Current:**
```python
    ap.add_argument("--output-root", dest="output_root", required=True)
```

**New:**
```python
    ap.add_argument("--output-root", dest="output_root", default="artifacts/runs/batches")
```

**Status:** ⬜ Not started

---

### 2.2 scripts/extract_responses.py

**No changes needed**  
This script writes to user-specified output directories; it doesn't hardcode `out/` or reference `experiments/`.

**Status:** ✅ No action required

---

### 2.3 scripts/ingest_week1_assignment.py

**No changes needed**  
This script ingests from external paths (Desktop folder) into the database. No references to `out/` or `experiments/`.

**Status:** ✅ No action required

---

### 2.4 scripts/ingest_week9_assignment.py

**No changes needed**  
Same as ingest_week1_assignment.py.

**Status:** ✅ No action required

---

## Phase 3: Update Documentation

### 3.1 README_PRIVATE.md

**Lines 133: Update example command**

**Current:**
```markdown
  - `python scripts/grade_batch.py <SUBMISSIONS_DIR> <ASSIGNMENT_ID> <COURSE> --csv-out out/grades.csv`
```

**New:**
```markdown
  - `python scripts/grade_batch.py <SUBMISSIONS_DIR> <ASSIGNMENT_ID> <COURSE> --csv-out artifacts/ba101_grades.csv`
```

**Lines 135: Update example command**

**Current:**
```markdown
    - `python scripts/grade_batch.py data/ba101_submissions/week_1 ba101_week_1 BA101 --anonymize --csv-out out/ba101_week1_grades.csv`
```

**New:**
```markdown
    - `python scripts/grade_batch.py data/ba101_submissions/week_1 ba101_week_1 BA101 --anonymize --csv-out artifacts/ba101_week1_grades.csv`
```

**Status:** ⬜ Not started

---

### 3.2 TROUBLESHOOTING.md

**No changes needed**  
This document contains no references to `out/` or `experiments/`.

**Status:** ✅ No action required

---

### 3.3 docs/code_map.md

**No changes needed**  
Checked lines 1-250; no references to `out/` or `experiments/` found.

**Status:** ✅ No action required

---

### 3.4 CHATGPT_HANDOFF_SUMMARY.md

**Line 87: Update example command**

**Current:**
```markdown
   - Run: `python scripts/grade_batch.py <dir> --assignment-id ba101_week_1 --course-id BA101 --week 1 --batch-id wk1_full --output-root out/batches --grade`
```

**New:**
```markdown
   - Run: `python scripts/grade_batch.py <dir> --assignment-id ba101_week_1 --course-id BA101 --week 1 --batch-id wk1_full --batch-id wk1_full --grade`
```

*(Note: `--output-root` removed since it now defaults to `artifacts/runs/batches`)*

**Line 90: Update outputs**

**Current:**
```markdown
   - Outputs: `out/batches/wk1_full/extracted/`, `reports/batch_report.json`, `reports/batch_rollup.jsonl`, `reports/records/*.json`
```

**New:**
```markdown
   - Outputs: `artifacts/runs/batches/wk1_full/grading/canonical/*.json`, `reports/final/batch_report.json`, `reports/debug/batch_rollup.jsonl`
```

**Line 203: Update directory name**

**Current:**
```markdown
├── experiments/
```

**New:**
```markdown
├── sandbox/
```

**Line 204: Update file path**

**Current:**
```markdown
│   └── hello_assistant.py           # OpenAI Assistants API spike (not in use)
```

**New:**
```markdown
│   └── hello_assistant.py           # OpenAI Assistants API spike (not in use)
```

*(No change to this line, just context)*

**Lines 216-228: Update directory structure**

**Current:**
```markdown
├── out/                              # Batch processing output (gitignored)
│   ├── batches/
│   │   ├── ba101_wk1_full/          # Full 50-submission batch
│   │   │   ├── extracted/           # Cleaned text files
│   │   │   └── reports/
│   │   │       ├── batch_report.json      # Summary stats
│   │   │       ├── batch_rollup.jsonl     # Per-file records (one JSON per line)
│   │   │       └── records/               # Individual JSON per submission
│   │   └── ba101_wk1_test/          # Test batch (2 files)
│   └── ba101_week1_grades.csv       # ★ CSV export (currently open in editor)
```

**New:**
```markdown
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
```

**Line 471: Update directory reference**

**Current:**
```markdown
   Current: Each batch outputs JSON files to `out/batches/batch_id/`.  
```

**New:**
```markdown
   Current: Each batch outputs JSON files to `artifacts/runs/batches/{batch_id}/`.  
```

**Status:** ⬜ Not started

---

### 3.5 .gitignore

**Add artifacts/ pattern**

**Current:**
```
# (no out/ or artifacts/ entry exists)
```

**New:**
Add this line after the "# Logs" section (around line 50):
```
# -----------------------
# Batch processing artifacts
# -----------------------
artifacts/
```

**Status:** ⬜ Not started

---

## Phase 4: Validation

### 4.1 Grep for remaining references

**Commands:**
```bash
# Search for any remaining "out/" references (excluding migrate.py and artifacts/)
grep -r "out/" --exclude-dir=.git --exclude-dir=.venv --exclude-dir=artifacts --exclude=migrate.py .

# Search for any remaining "experiments/" references (excluding artifacts/)
grep -r "experiments/" --exclude-dir=.git --exclude-dir=.venv --exclude-dir=artifacts .
```

**Expected:** No results (except comments or string literals in non-code files)

**Status:** ⬜ Not started

---

### 4.2 Test batch grading with new defaults

**Command:**
```bash
python scripts/grade_batch.py data/ba101_submissions/week_1/clean_submissions \
  --assignment-id ba101_week_1 \
  --course-id BA101 \
  --week 1 \
  --batch-id test_refactor \
  --dry-run
```

**Expected:** Script creates directories under `artifacts/runs/batches/test_refactor/`

**Status:** ⬜ Not started

---

## Summary

**Files to edit:** 3
- [scripts/grade_batch.py](scripts/grade_batch.py) - 7 changes
- [README_PRIVATE.md](README_PRIVATE.md) - 2 changes
- [CHATGPT_HANDOFF_SUMMARY.md](CHATGPT_HANDOFF_SUMMARY.md) - 5 changes
- [.gitignore](.gitignore) - 1 addition

**Files with no changes needed:** 5
- [scripts/extract_responses.py](scripts/extract_responses.py)
- [scripts/ingest_week1_assignment.py](scripts/ingest_week1_assignment.py)
- [scripts/ingest_week9_assignment.py](scripts/ingest_week9_assignment.py)
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- [docs/code_map.md](docs/code_map.md)

**Directory operations:** 1
- Rename `experiments/` → `sandbox/`

---

## Minimal diffs promise

- **No architectural changes**
- **No feature additions**
- **No changes to migrate.py or artifacts/**
- All edits update paths/defaults only

---

## After completion

✅ `out/` never reappears in new code  
✅ Repo structure is self-explanatory  
✅ `sandbox/` clearly signals non-production experiments  
✅ All batch runs default to `artifacts/runs/batches/`  
✅ All extractions write to `artifacts/extraction_store/`
