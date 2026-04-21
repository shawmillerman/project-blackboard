#!/usr/bin/env python3
"""
Assessment Workflow – Pre-Screen (optional)
Iterates through NEEDS_REVIEW submissions, shows extracted text and quality issues,
lets instructor decide: approve for grading, or skip.

Updates canonical records with instructor decisions before grading proceeds.

Usage:
  python scripts/pre_screen_review.py \
    --batch-id ba101_wk1_full \
    [--start-from 5]  # Resume from submission N
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


def load_batch_rollup(batch_id: str) -> List[Dict[str, Any]]:
    """Load batch_rollup.jsonl from artifacts/runs/batches/{batch_id}/reports/debug/"""
    rollup_path = Path(f"artifacts/runs/batches/{batch_id}/reports/debug/batch_rollup.jsonl")
    if not rollup_path.exists():
        raise FileNotFoundError(f"Batch rollup not found: {rollup_path}")
    
    records: List[Dict[str, Any]] = []
    with rollup_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_canonical_record(batch_id: str, original_filename: str) -> Optional[Dict[str, Any]]:
    """Load per-submission grading JSON from canonical directory"""
    stem = Path(original_filename).stem
    canonical_path = Path(f"artifacts/runs/batches/{batch_id}/grading/canonical/{stem}.json")
    
    if not canonical_path.exists():
        return None
    
    try:
        with canonical_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def load_extracted_text(cleaned_text_path: str) -> Optional[str]:
    """Load the cleaned extracted text"""
    path = Path(cleaned_text_path)
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return None
    return None


def count_existing_screens(pre_screen_dir: Path) -> int:
    """Count lines in pre_screen_session.jsonl to enable auto-resume"""
    session_path = pre_screen_dir / "pre_screen_session.jsonl"
    if not session_path.exists():
        return 0
    
    count = 0
    try:
        with session_path.open("r", encoding="utf-8") as f:
            count = sum(1 for _ in f)
    except Exception:
        pass
    return count


def display_submission(record: Dict[str, Any], index: int, total: int, extracted_text: Optional[str]) -> None:
    """Show submission and quality issues in terminal"""
    print(f"\n{'='*80}")
    print(f"Submission {index + 1} of {total}")
    print(f"{'='*80}")
    print(f"Filename: {record.get('original_filename')}")
    print(f"Assignment: {record.get('assignment_id')}")
    print(f"Course: {record.get('course_id')}")
    print(f"Week: {record.get('week')}")
    
    print(f"\n[QUALITY ISSUES]")
    quality_reasons = record.get("quality_reasons", [])
    if quality_reasons:
        for reason in quality_reasons:
            print(f"  • {reason}")
    else:
        print("  (none recorded)")
    
    print(f"\n[EXTRACTION WARNINGS]")
    warnings = record.get("extraction_warnings", [])
    if warnings:
        for warning in warnings:
            print(f"  • {warning}")
    else:
        print("  (none)")
    
    print(f"\n[EXTRACTED TEXT]")
    if extracted_text:
        # Show first 500 chars or full text if shorter
        display_text = extracted_text[:500]
        if len(extracted_text) > 500:
            display_text += f"\n... ({len(extracted_text) - 500} more characters)"
        print(display_text)
    else:
        print("  (empty or could not load)")


def ask_decision() -> str:
    """Ask instructor decision: approve for grading, or skip"""
    while True:
        response = input(
            "\nDecision: (a) Approve for grading, (s) Skip, (n) Next without deciding, (q) Quit: "
        ).strip().lower()
        
        if response in ['a', 's', 'n', 'q']:
            return response
        print("Please enter 'a', 's', 'n', or 'q'")


def update_canonical_record(batch_id: str, record: Dict[str, Any], decision: str) -> None:
    """Update canonical record with pre-screen decision"""
    stem = Path(record.get("original_filename", "")).stem
    canonical_path = Path(f"artifacts/runs/batches/{batch_id}/grading/canonical/{stem}.json")
    
    if not canonical_path.exists():
        print(f"⚠ Warning: Canonical record not found at {canonical_path}, skipping update")
        return
    
    try:
        with canonical_path.open("r", encoding="utf-8") as f:
            canonical_record = json.load(f)
        
        # Mark pre-screen decision
        canonical_record["pre_screen_decision"] = {
            "decision": decision,  # "approve" or "skip"
            "reviewed_at": datetime.now().isoformat()
        }
        
        # Update quality_status if approved
        if decision == "approve":
            canonical_record["quality_status"] = "OK_FOR_GRADING"
            canonical_record["status"] = "ready"  # Mark ready for grading
        elif decision == "skip":
            canonical_record["status"] = "skipped"  # Mark as skipped
        
        with canonical_path.open("w", encoding="utf-8") as f:
            json.dump(canonical_record, f, indent=2)
    except Exception as e:
        print(f"✗ Error updating canonical record: {e}")


def append_screen_session(screen: Dict[str, Any], pre_screen_dir: Path) -> None:
    """Append single pre-screen decision to pre_screen_session.jsonl"""
    session_path = pre_screen_dir / "pre_screen_session.jsonl"
    with session_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(screen) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Assessment Workflow: Pre-Screen NEEDS_REVIEW submissions (optional)")
    ap.add_argument("--batch-id", required=True, help="Batch ID to pre-screen")
    ap.add_argument("--pre-screen-id", default=None, help="Pre-screen session ID (default: batch-id)")
    ap.add_argument("--start-from", type=int, default=None, help="Start from submission N (default: auto-resume)")
    args = ap.parse_args()
    
    pre_screen_id = args.pre_screen_id or args.batch_id
    
    # Setup pre-screen directory
    pre_screen_dir = Path(f"artifacts/runs/pre_screen/{pre_screen_id}")
    pre_screen_dir.mkdir(parents=True, exist_ok=True)
    
    # Auto-resume: count existing screens
    existing_count = count_existing_screens(pre_screen_dir)
    start_from = args.start_from if args.start_from is not None else existing_count
    
    # Load batch records
    try:
        records = load_batch_rollup(args.batch_id)
    except FileNotFoundError as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
    
    # Filter for NEEDS_REVIEW submissions
    needs_review_records = [
        (idx, rec) for idx, rec in enumerate(records)
        if rec.get("status") == "needs_review"
    ]
    
    if not needs_review_records:
        print(f"✓ No NEEDS_REVIEW submissions found in batch {args.batch_id}")
        return
    
    print(f"Loaded {len(records)} total records from batch {args.batch_id}")
    print(f"Found {len(needs_review_records)} NEEDS_REVIEW submissions")
    
    if existing_count > 0 and args.start_from is None:
        print(f"ℹ Auto-resuming: found {existing_count} existing screens, starting from submission {existing_count + 1}")
    
    if start_from >= len(needs_review_records):
        print(f"✗ Start position {start_from} is beyond available NEEDS_REVIEW submissions ({len(needs_review_records)})")
        sys.exit(1)
    
    # Review loop
    screened_count = 0
    approved_count = 0
    skipped_count = 0
    
    for screen_idx in range(start_from, len(needs_review_records)):
        record_idx, record = needs_review_records[screen_idx]
        
        # Load extracted text
        cleaned_text_path = record.get("cleaned_text_path")
        extracted_text = None
        if cleaned_text_path:
            extracted_text = load_extracted_text(cleaned_text_path)
        
        # Display and capture decision
        display_submission(record, screen_idx, len(needs_review_records), extracted_text)
        
        decision_input = ask_decision()
        
        if decision_input == 'q':
            print("\n⊘ Review stopped by user")
            break
        
        if decision_input == 'n':
            print("  ⊘ Skipped (deferred decision)")
            continue
        
        # Map decision input to decision string
        decision = "approve" if decision_input == 'a' else "skip"
        
        # Build screen record
        screen = {
            "original_filename": record.get("original_filename"),
            "batch_id": args.batch_id,
            "assignment_id": record.get("assignment_id"),
            "quality_reasons": record.get("quality_reasons", []),
            "extraction_warnings": record.get("extraction_warnings", []),
            "decision": decision,
            "screened_at": datetime.now().isoformat()
        }
        
        # Save screen decision
        append_screen_session(screen, pre_screen_dir)
        screened_count += 1
        
        # Update canonical record
        update_canonical_record(args.batch_id, record, decision)
        
        if decision == "approve":
            approved_count += 1
            print(f"  ✓ Approved for grading")
        elif decision == "skip":
            skipped_count += 1
            print(f"  ✓ Marked as skipped")
        
        # Continue?
        if screen_idx < len(needs_review_records) - 1:
            cont = input("\nContinue to next? (y/n/q to quit): ").strip().lower()
            if cont == 'q' or cont == 'n':
                break
    
    # Summary
    print(f"\n{'='*80}")
    print(f"✓ Pre-screen complete")
    print(f"  • Screened: {screened_count}")
    print(f"  • Approved for grading: {approved_count}")
    print(f"  • Skipped: {skipped_count}")
    print(f"  • Session saved to: {pre_screen_dir}")
    print(f"\nNEXT STEPS:")
    print(f"  1. Run grading: python scripts/grade_batch.py <dir> ... --grade")
    print(f"  2. Review grades: python scripts/calibration_review.py --batch-id {args.batch_id} --calibration-id <cal-id>")


if __name__ == "__main__":
    main()
