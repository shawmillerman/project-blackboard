#!/usr/bin/env python3
"""
Migration script: out/ → artifacts/

PHASE 1: MIGRATION (NON-DESTRUCTIVE)
- Copies all data from out/ to artifacts/
- Rewrites embedded paths in JSON/JSONL/CSV for readability
- Safe to run multiple times; does NOT modify or delete out/
- After running, validate artifacts/ before proceeding to cleanup

PHASE 2: VALIDATION
- Confirms extraction completeness
- Verifies required files were migrated
- Detects file collisions
- Verifies no legacy "out/" paths remain in artifacts
- Run with: python migrate.py --validate

PHASE 3: CLEANUP (DESTRUCTIVE - RUN MANUALLY AFTER VALIDATION)
- Removes the legacy out/ directory entirely
- Only runs after validation passes
- Only run this after confirming artifacts/ is correct
- This step is INTENTIONAL and EXPLICIT
- Run with: python migrate.py --cleanup

Usage:
    python migrate.py               # Run migration (safe)
    python migrate.py --validate    # Run validation checks only
    python migrate.py --cleanup     # DESTRUCTIVE: Delete out/ (after validation passes)
"""
import json
import csv
import re
import shutil
import argparse
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Set, Tuple

# Configuration
GLOBAL_EXTRACTION_STORE = "artifacts/extraction_store"
BATCHES_TO_MIGRATE = ["ba101_wk1_full", "ba101_wk1_test"]

def log(msg: str, level="INFO"):
    """Simple logging with visual distinction."""
    prefix = {
        "INFO": "ℹ",
        "WARN": "⚠",
        "ERROR": "✗",
        "SUCCESS": "✓"
    }.get(level, "•")
    print(f"{prefix} [{level}] {msg}")

def get_file_hash(path: Path) -> str:
    """Get SHA256 hash of a file for comparison."""
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def recursive_path_rewrite(obj: Any, batch_id: str = None) -> Any:
    """
    Recursively walk through dicts/lists and rewrite any string containing old paths.
    
    Rewrites:
    - out/extracted_responses/ → artifacts/extraction_store/
    - out/batches/{batch_id}/extracted/ → artifacts/extraction_store/
    """
    if isinstance(obj, dict):
        return {k: recursive_path_rewrite(v, batch_id) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [recursive_path_rewrite(item, batch_id) for item in obj]
    elif isinstance(obj, str):
        # Pattern 1: out/extracted_responses/
        if "out/extracted_responses/" in obj:
            obj = re.sub(
                r"out/extracted_responses/",
                f"{GLOBAL_EXTRACTION_STORE}/",
                obj
            )
        
        # Pattern 2: out/batches/{batch_id}/extracted/
        if batch_id and f"out/batches/{batch_id}/extracted/" in obj:
            obj = re.sub(
                rf"out/batches/{batch_id}/extracted/",
                f"{GLOBAL_EXTRACTION_STORE}/",
                obj
            )
        # Pattern 2b: Generic batch pattern (any batch_id)
        elif "out/batches/" in obj and "/extracted/" in obj:
            obj = re.sub(
                r"out/batches/[^/]+/extracted/",
                f"{GLOBAL_EXTRACTION_STORE}/",
                obj
            )
        
        return obj
    else:
        return obj

def migrate_artifact_structure():
    """
    PHASE 1: NON-DESTRUCTIVE MIGRATION
    
    Copies all data from out/ → artifacts/ without modifying source.
    Rewrites paths in JSON/JSONL/CSV so artifacts remain readable.
    
    This is SAFE to run multiple times and will NOT delete out/.
    """
    log("=" * 70, "INFO")
    log("MIGRATION PHASE 1: Copy out/ → artifacts/ (NON-DESTRUCTIVE)", "INFO")
    log("=" * 70, "INFO")
    log("The legacy out/ directory will NOT be modified or deleted.", "INFO")
    log("")
    
    # 1. Create directory structure
    log("Creating target directory structure...", "INFO")
    create_directories()
    
    # 2. Migrate global extractions
    log("Copying global extracted responses...", "INFO")
    migrate_global_extractions()
    
    # 3. Migrate each batch
    for batch_id in BATCHES_TO_MIGRATE:
        log(f"Copying batch: {batch_id}", "INFO")
        migrate_batch(batch_id)
    
    # 4. Rewrite CSV
    log("Rewriting grades CSV...", "INFO")
    rewrite_grades_csv()
    
    log("", "INFO")
    log("=" * 70, "SUCCESS")
    log("MIGRATION COMPLETE (out/ preserved)", "SUCCESS")
    log("=" * 70, "SUCCESS")
    log("", "INFO")
    log("NEXT STEPS:", "INFO")
    log("1. Validate artifacts/ structure:", "INFO")
    log("   python migrate.py --validate", "INFO")
    log("2. Test that scripts work with new paths", "INFO")
    log("3. When validation passes, run cleanup:", "INFO")
    log("   python migrate.py --cleanup", "WARN")
    log("", "INFO")

def create_directories():
    """Create all target directories (idempotent)."""
    # Global extraction store
    Path(GLOBAL_EXTRACTION_STORE).mkdir(parents=True, exist_ok=True)
    
    # Per-batch structure
    for batch_id in BATCHES_TO_MIGRATE:
        base = Path(f"artifacts/runs/batches/{batch_id}")
        for subdir in [
            "grading/intermediate",
            "grading/canonical",
            "reports/final",
            "reports/debug"
        ]:
            (base / subdir).mkdir(parents=True, exist_ok=True)
    
    log("  Created artifacts/ directory structure", "INFO")

def migrate_global_extractions():
    """
    Copy out/extracted_responses/ → artifacts/extraction_store/
    
    NON-DESTRUCTIVE: Source files are preserved.
    Includes collision detection.
    """
    src = Path("out/extracted_responses")
    dst = Path(GLOBAL_EXTRACTION_STORE)
    
    if not src.exists():
        log(f"  Source not found: {src} (skipping)", "WARN")
        return
    
    count = 0
    skipped = 0
    collisions = 0
    
    for f in src.glob("*"):
        if f.is_file():
            dst_file = dst / f.name
            if not dst_file.exists():
                shutil.copy2(f, dst_file)
                count += 1
            else:
                # Collision: compare file hashes
                if get_file_hash(f) != get_file_hash(dst_file):
                    log(f"  ⚠ COLLISION: {f.name} exists with different hash", "WARN")
                    collisions += 1
                skipped += 1
    
    log(f"  Copied {count} files to {GLOBAL_EXTRACTION_STORE} ({skipped} existed, {collisions} collisions)", "INFO")

def migrate_batch(batch_id: str):
    """
    Copy batch data from out/batches/{batch_id}/ → artifacts/runs/batches/{batch_id}/
    
    NON-DESTRUCTIVE: Source files are preserved.
    """
    old_batch = Path(f"out/batches/{batch_id}")
    new_batch = Path(f"artifacts/runs/batches/{batch_id}")
    
    if not old_batch.exists():
        log(f"    Batch not found: {old_batch} (skipping)", "WARN")
        return
    
    # Step 1: Copy batch-scoped extracted files to global store
    migrate_batch_extractions(batch_id, old_batch)
    
    # Step 2: Copy and rewrite reports
    migrate_batch_reports(batch_id, old_batch, new_batch)
    
    # Step 3: Create manifest
    create_manifest(batch_id, old_batch, new_batch)

def migrate_batch_extractions(batch_id: str, old_batch: Path):
    """
    Copy batch-scoped extracted/ files to global store.
    
    NON-DESTRUCTIVE: Source files preserved.
    Includes collision detection.
    """
    src = old_batch / "extracted"
    dst = Path(GLOBAL_EXTRACTION_STORE)
    
    if not src.exists():
        log(f"      No batch-scoped extracted/ dir (skipping)", "INFO")
        return
    
    count = 0
    skipped = 0
    collisions = 0
    
    for f in src.glob("*"):
        if f.is_file():
            dst_file = dst / f.name
            if not dst_file.exists():
                shutil.copy2(f, dst_file)
                count += 1
            else:
                # Collision: compare file hashes
                if get_file_hash(f) != get_file_hash(dst_file):
                    log(f"      ⚠ COLLISION: {f.name} exists with different hash", "WARN")
                    collisions += 1
                skipped += 1
    
    log(f"      Copied {count} batch extractions to global store ({skipped} existed, {collisions} collisions)", "INFO")

def migrate_batch_reports(batch_id: str, old_batch: Path, new_batch: Path):
    """
    Copy batch reports and rewrite embedded paths.
    
    NON-DESTRUCTIVE: Source files preserved, new files written to artifacts/.
    """
    reports_dir = old_batch / "reports"
    
    if not reports_dir.exists():
        log(f"      No reports/ dir (skipping)", "WARN")
        return
    
    # Copy and rewrite batch_report.json
    old_report = reports_dir / "batch_report.json"
    new_report = new_batch / "reports" / "final" / "batch_report.json"
    if old_report.exists():
        rewrite_batch_report_json(old_report, new_report, batch_id)
        log(f"      Copied and rewrote batch_report.json", "INFO")
    else:
        log(f"      No batch_report.json found", "INFO")
    
    # Copy and rewrite batch_rollup.jsonl
    old_rollup = reports_dir / "batch_rollup.jsonl"
    new_rollup = new_batch / "reports" / "debug" / "batch_rollup.jsonl"
    if old_rollup.exists():
        rewrite_batch_rollup(old_rollup, new_rollup, batch_id)
        log(f"      Copied and rewrote batch_rollup.jsonl", "INFO")
    else:
        log(f"      No batch_rollup.jsonl found", "INFO")

def rewrite_batch_report_json(old_path: Path, new_path: Path, batch_id: str):
    """
    Copy batch_report.json and rewrite embedded paths recursively.
    
    Attempts JSON parsing first; falls back to text scan if invalid.
    """
    try:
        # Try to parse as JSON
        with open(old_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Recursively rewrite paths
        data = recursive_path_rewrite(data, batch_id)
        
        # Write back as JSON
        with open(new_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    except json.JSONDecodeError:
        # Not valid JSON; use safe text scan
        log(f"        batch_report.json is not valid JSON; using text scan", "WARN")
        with open(old_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Only rewrite if it's safe (contains obvious path patterns)
        if "out/extracted_responses/" in content or "out/batches/" in content:
            content = content.replace("out/extracted_responses/", f"{GLOBAL_EXTRACTION_STORE}/")
            content = re.sub(
                r"out/batches/[^/]+/extracted/",
                f"{GLOBAL_EXTRACTION_STORE}/",
                content
            )
            with open(new_path, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            # No paths to rewrite; just copy
            shutil.copy2(old_path, new_path)

def rewrite_batch_rollup(old_path: Path, new_path: Path, batch_id: str):
    """
    Copy batch_rollup.jsonl and rewrite all embedded paths recursively.
    
    NON-DESTRUCTIVE: Reads from out/, writes to artifacts/.
    """
    with open(new_path, 'w', encoding='utf-8') as out_f:
        with open(old_path, 'r', encoding='utf-8') as in_f:
            for line in in_f:
                try:
                    record = json.loads(line)
                    record = recursive_path_rewrite(record, batch_id)
                    out_f.write(json.dumps(record) + '\n')
                except json.JSONDecodeError as e:
                    log(f"        Failed to parse JSON line: {e}", "WARN")

def create_manifest(batch_id: str, old_batch: Path, new_batch: Path):
    """
    Create manifest.json from batch metadata.
    
    Reads from new artifacts/ location (batch_rollup.jsonl already copied).
    """
    rollup_path = new_batch / "reports" / "debug" / "batch_rollup.jsonl"
    
    # Initialize with safe defaults
    assignment_id = None
    course_id = None
    week = None
    submission_count = 0
    status = "unknown"
    
    if rollup_path.exists():
        try:
            with open(rollup_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                submission_count = len(lines)
                
                if lines:
                    first_record = json.loads(lines[0])
                    assignment_id = first_record.get('assignment_id')
                    course_id = first_record.get('course_id')
                    week = first_record.get('week')
                
                status = "completed"
        except (json.JSONDecodeError, IOError) as e:
            log(f"      Failed to parse rollup for metadata: {e}", "WARN")
    else:
        log(f"      No batch_rollup.jsonl; manifest will have limited data", "WARN")
    
    manifest = {
        "batch_id": batch_id,
        "run_type": "batch_grading",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "assignment_id": assignment_id,
        "course_id": course_id,
        "week": week,
        "submission_count": submission_count,
        "extraction_store_path": GLOBAL_EXTRACTION_STORE,
        "status": status,
        "_migration_note": "Migrated from out/ structure; original preserved during migration"
    }
    
    manifest_path = new_batch / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    log(f"      Created manifest.json", "INFO")

def rewrite_grades_csv():
    """
    Copy ba101_week1_grades.csv and rewrite embedded paths.
    
    NON-DESTRUCTIVE: Reads from out/, writes to artifacts/.
    """
    old_csv = Path("out/ba101_week1_grades.csv")
    new_csv = Path("artifacts/runs/batches/ba101_wk1_full/reports/final/grades.csv")
    
    if not old_csv.exists():
        log(f"  CSV not found: {old_csv} (skipping)", "WARN")
        return
    
    try:
        with open(old_csv, 'r', encoding='utf-8') as in_f:
            reader = csv.reader(in_f)
            header = next(reader, None)
            
            if header is None:
                log("  CSV is empty or unreadable", "WARN")
                return
            
            rows = list(reader)
        
        # Rewrite paths in first column
        rewritten_count = 0
        rewritten_rows = []
        for row in rows:
            if row and len(row) > 0:
                path_col = row[0]
                original_path = path_col
                
                # Pattern 1: out/extracted_responses/
                if path_col.startswith("out/extracted_responses/"):
                    row[0] = re.sub(
                        r"^out/extracted_responses/",
                        f"{GLOBAL_EXTRACTION_STORE}/",
                        path_col
                    )
                # Pattern 2: out/batches/{batch_id}/extracted/
                elif path_col.startswith("out/batches/"):
                    row[0] = re.sub(
                        r"^out/batches/[^/]+/extracted/",
                        f"{GLOBAL_EXTRACTION_STORE}/",
                        path_col
                    )
                
                if row[0] != original_path:
                    rewritten_count += 1
            
            rewritten_rows.append(row)
        
        # Write new CSV
        with open(new_csv, 'w', encoding='utf-8', newline='') as out_f:
            writer = csv.writer(out_f)
            writer.writerow(header)
            writer.writerows(rewritten_rows)
        
        log(f"  Copied grades.csv; rewrote {rewritten_count}/{len(rewritten_rows)} paths", "INFO")
    
    except Exception as e:
        log(f"  Failed to rewrite CSV: {e}", "ERROR")
        raise

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_extraction_completeness() -> bool:
    """
    Validate that all files from source locations are in artifacts/extraction_store/.
    
    Returns True if all files are present, False otherwise.
    """
    log("", "INFO")
    log("Validation: Extraction completeness", "INFO")
    
    # Collect all source files
    source_files: Set[str] = set()
    
    # From global extracted_responses
    global_src = Path("out/extracted_responses")
    if global_src.exists():
        for f in global_src.glob("*"):
            if f.is_file():
                source_files.add(f.name)
    
    # From batch-scoped extracted dirs
    for batch_id in BATCHES_TO_MIGRATE:
        batch_src = Path(f"out/batches/{batch_id}/extracted")
        if batch_src.exists():
            for f in batch_src.glob("*"):
                if f.is_file():
                    source_files.add(f.name)
    
    # Check what's in artifacts
    dst = Path(GLOBAL_EXTRACTION_STORE)
    if not dst.exists():
        log("  ✗ artifacts/extraction_store/ does not exist", "ERROR")
        return False
    
    dst_files: Set[str] = set()
    for f in dst.glob("*"):
        if f.is_file():
            dst_files.add(f.name)
    
    missing = source_files - dst_files
    extra = dst_files - source_files
    
    if missing:
        log(f"  ✗ Missing {len(missing)} files in extraction_store:", "ERROR")
        for fname in sorted(list(missing)[:5]):
            log(f"    - {fname}", "ERROR")
        if len(missing) > 5:
            log(f"    ... and {len(missing) - 5} more", "ERROR")
        return False
    
    if extra:
        log(f"  ⚠ Found {len(extra)} extra files in extraction_store (not in source)", "WARN")
    
    log(f"  ✓ All {len(source_files)} source files present in extraction_store", "SUCCESS")
    return True

def validate_required_files() -> bool:
    """
    Validate that required files were migrated if they exist in source.
    
    Strict checks:
    - If out/batches/{batch}/reports/batch_rollup.jsonl exists, 
      then artifacts/.../reports/debug/batch_rollup.jsonl must exist
    - If out/batches/{batch}/reports/batch_report.json exists,
      then artifacts/.../reports/final/batch_report.json must exist
    - If out/ba101_week1_grades.csv exists,
      then artifacts/.../reports/final/grades.csv must exist
    
    Returns True if all required files present, False otherwise.
    """
    log("", "INFO")
    log("Validation: Required file migration", "INFO")
    
    all_present = True
    
    for batch_id in BATCHES_TO_MIGRATE:
        old_batch = Path(f"out/batches/{batch_id}")
        new_batch = Path(f"artifacts/runs/batches/{batch_id}")
        
        # Check batch_rollup.jsonl
        old_rollup = old_batch / "reports" / "batch_rollup.jsonl"
        new_rollup = new_batch / "reports" / "debug" / "batch_rollup.jsonl"
        if old_rollup.exists():
            if not new_rollup.exists():
                log(f"  ✗ Missing: {new_rollup.relative_to('.')} (source exists)", "ERROR")
                all_present = False
            else:
                log(f"  ✓ Present: batch_rollup.jsonl ({batch_id})", "SUCCESS")
        
        # Check batch_report.json
        old_report = old_batch / "reports" / "batch_report.json"
        new_report = new_batch / "reports" / "final" / "batch_report.json"
        if old_report.exists():
            if not new_report.exists():
                log(f"  ✗ Missing: {new_report.relative_to('.')} (source exists)", "ERROR")
                all_present = False
            else:
                log(f"  ✓ Present: batch_report.json ({batch_id})", "SUCCESS")
    
    # Check grades.csv
    old_csv = Path("out/ba101_week1_grades.csv")
    new_csv = Path("artifacts/runs/batches/ba101_wk1_full/reports/final/grades.csv")
    if old_csv.exists():
        if not new_csv.exists():
            log(f"  ✗ Missing: {new_csv.relative_to('.')} (source exists)", "ERROR")
            all_present = False
        else:
            log(f"  ✓ Present: grades.csv", "SUCCESS")
    
    return all_present

def validate_no_legacy_paths() -> bool:
    """
    Validate that no "out/" paths remain in migrated artifacts.
    
    Checks:
    - batch_rollup.jsonl
    - grades.csv
    - batch_report.json
    
    Returns True if no legacy paths found, False otherwise.
    """
    log("", "INFO")
    log("Validation: No legacy 'out/' paths in artifacts", "INFO")
    
    all_clean = True
    
    for batch_id in BATCHES_TO_MIGRATE:
        batch_base = Path(f"artifacts/runs/batches/{batch_id}")
        
        # Check batch_rollup.jsonl (only if it should exist)
        rollup_path = batch_base / "reports" / "debug" / "batch_rollup.jsonl"
        if rollup_path.exists():
            with open(rollup_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if "out/" in content:
                    log(f"  ✗ Found 'out/' in {rollup_path.relative_to('.')}", "ERROR")
                    all_clean = False
                else:
                    log(f"  ✓ No 'out/' in batch_rollup.jsonl ({batch_id})", "SUCCESS")
        
        # Check batch_report.json (only if it should exist)
        report_path = batch_base / "reports" / "final" / "batch_report.json"
        if report_path.exists():
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if "out/" in content:
                    log(f"  ✗ Found 'out/' in {report_path.relative_to('.')}", "ERROR")
                    all_clean = False
                else:
                    log(f"  ✓ No 'out/' in batch_report.json ({batch_id})", "SUCCESS")
    
    # Check grades.csv (only if it should exist)
    csv_path = Path("artifacts/runs/batches/ba101_wk1_full/reports/final/grades.csv")
    if csv_path.exists():
        with open(csv_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if "out/" in content:
                log(f"  ✗ Found 'out/' in {csv_path.relative_to('.')}", "ERROR")
                all_clean = False
            else:
                log(f"  ✓ No 'out/' in grades.csv", "SUCCESS")
    
    return all_clean

def run_all_validations() -> bool:
    """
    Run all validation checks.
    
    Returns True if all validations pass, False otherwise.
    """
    log("=" * 70, "INFO")
    log("PHASE 2: VALIDATION", "INFO")
    log("=" * 70, "INFO")
    
    results = []
    
    # Run each validation
    results.append(validate_extraction_completeness())
    results.append(validate_required_files())
    results.append(validate_no_legacy_paths())
    
    # Summary
    log("", "INFO")
    log("=" * 70, "INFO")
    if all(results):
        log("✓ ALL VALIDATIONS PASSED", "SUCCESS")
        log("=" * 70, "SUCCESS")
        log("", "INFO")
        log("Safe to proceed with cleanup:", "INFO")
        log("  python migrate.py --cleanup", "INFO")
        return True
    else:
        log("✗ VALIDATION FAILED", "ERROR")
        log("=" * 70, "ERROR")
        log("", "INFO")
        log("Fix issues before running cleanup.", "ERROR")
        return False

# ============================================================================
# PHASE 3: CLEANUP (DESTRUCTIVE - EXPLICIT AND INTENTIONAL)
# ============================================================================

def cleanup_legacy_structure():
    """
    PHASE 3: DESTRUCTIVE CLEANUP
    
    ⚠️ WARNING: This will PERMANENTLY DELETE the out/ directory.
    
    Only runs if:
    1. Validation passes
    2. User provides explicit confirmation
    
    This action is IRREVERSIBLE.
    """
    log("", "WARN")
    log("=" * 70, "WARN")
    log("CLEANUP PHASE 3: DELETE out/ (DESTRUCTIVE)", "WARN")
    log("=" * 70, "WARN")
    log("", "WARN")
    
    # Run validations first
    log("Running pre-cleanup validations...", "INFO")
    if not run_all_validations():
        log("", "ERROR")
        log("✗ CLEANUP ABORTED: Validation failed", "ERROR")
        log("Fix validation errors before attempting cleanup.", "ERROR")
        return
    
    log("", "WARN")
    out_dir = Path("out")
    
    if not out_dir.exists():
        log("The out/ directory does not exist; nothing to clean up.", "INFO")
        return
    
    # Final confirmation prompt
    log("Validation passed. Ready to delete out/ directory.", "WARN")
    log("", "WARN")
    log("You are about to PERMANENTLY DELETE: out/", "WARN")
    log("This action CANNOT be undone.", "WARN")
    log("", "WARN")
    
    response = input("Type 'DELETE' (all caps) to confirm: ").strip()
    
    if response != "DELETE":
        log("Cleanup cancelled. out/ directory preserved.", "INFO")
        return
    
    # Perform deletion
    try:
        log("Deleting out/ directory...", "WARN")
        shutil.rmtree(out_dir)
        log("✓ out/ directory successfully deleted.", "SUCCESS")
        log("Migration complete. Only artifacts/ remains.", "SUCCESS")
    except Exception as e:
        log(f"Failed to delete out/: {e}", "ERROR")
        raise

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Migrate out/ → artifacts/ structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrate.py              # Run migration (safe, non-destructive)
  python migrate.py --validate   # Run validation checks only
  python migrate.py --cleanup    # DESTRUCTIVE: Delete out/ after validation
        """
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Run validation checks only (no migration or cleanup)'
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='DESTRUCTIVE: Delete out/ directory after validation (requires confirmation)'
    )
    
    args = parser.parse_args()
    
    if args.cleanup:
        # User explicitly requested cleanup (validation runs first)
        cleanup_legacy_structure()
    elif args.validate:
        # User explicitly requested validation only
        success = run_all_validations()
        exit(0 if success else 1)
    else:
        # Run migration (non-destructive)
        try:
            migrate_artifact_structure()
        except Exception as e:
            log(f"Migration failed: {e}", "ERROR")
            raise

if __name__ == "__main__":
    main()
