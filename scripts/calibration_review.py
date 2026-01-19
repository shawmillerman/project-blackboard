#!/usr/bin/env python3
"""
Calibration Review CLI
Iterates through batch grading outputs, captures instructor actuals, flags for calibration.

Usage:
  python scripts/calibration_review.py \
    --batch-id ba101_wk1_full \
    --calibration-id ba101_week1_cal_20260118 \
    [--start-from 5]  # Resume from submission N (default: auto-detect from review_session.jsonl)
"""

import argparse
import json
import sys
import os
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


def load_batch_rollup(batch_id: str) -> List[Dict[str, Any]]:
    """Load batch_rollup.jsonl from artifacts/runs/batches/{batch_id}/reports/debug/"""
    rollup_path = Path(f"artifacts/runs/batches/{batch_id}/reports/debug/batch_rollup.jsonl")
    if not rollup_path.exists():
        raise FileNotFoundError(f"Batch rollup not found: {rollup_path}")
    
    records = []
    with rollup_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def load_canonical_record(batch_id: str, original_filename: str) -> Optional[Dict[str, Any]]:
    """Load per-submission grading JSON from canonical directory"""
    # Try to find matching canonical record by original_filename
    canonical_dir = Path(f"artifacts/runs/batches/{batch_id}/grading/canonical")
    if not canonical_dir.exists():
        return None
    
    # Try exact match first (replacing extension with .json)
    stem = Path(original_filename).stem
    canonical_path = canonical_dir / f"{stem}.json"
    
    if canonical_path.exists():
        with canonical_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    
    return None


def enrich_record_with_grade_data(record: Dict[str, Any], batch_id: str) -> Dict[str, Any]:
    """
    Ensure record has grade.input and grade.suggested_feedback.
    If missing from rollup, try loading from canonical record.
    """
    if record.get("status") != "graded":
        # Skip non-graded records
        return record
    
    grade = record.get("grade", {})
    
    # Check if essential fields are present
    if grade.get("input") and grade.get("suggested_feedback"):
        return record
    
    # Try loading from canonical record
    canonical = load_canonical_record(batch_id, record.get("original_filename", ""))
    if canonical and canonical.get("grade"):
        # Merge grade data from canonical
        record["grade"] = canonical["grade"]
        return record
    
    # If still missing, this record cannot be reviewed
    return record


def display_submission(record: Dict[str, Any], index: int, total: int) -> None:
    """Show AI grading output in terminal"""
    print(f"\n{'='*80}")
    print(f"Submission {index+1}/{total}: {record.get('original_filename', 'UNKNOWN')}")
    print(f"Status: {record.get('status', 'UNKNOWN')}")
    print(f"{'='*80}")
    
    grade = record.get("grade", {})
    
    # Show submission text (first 400 chars)
    input_text = grade.get("input", "N/A")
    print(f"\nStudent Text (first 400 chars):")
    print(input_text[:400] + ("..." if len(input_text) > 400 else ""))
    
    print(f"\n--- AI GRADING ---")
    score_low = grade.get('score_low', 'N/A')
    score_high = grade.get('score_high', 'N/A')
    points_poss = grade.get('points_possible', 40)
    print(f"AI Score Range: {score_low} - {score_high} (out of {points_poss} points)")
    print(f"\nSuggested Feedback:")
    print(grade.get('suggested_feedback', 'N/A'))
    
    citations_count = len(grade.get('citations', []))
    print(f"\nCitations: {citations_count} sources")
    
    structural = record.get('structural_adjustments', [])
    if structural:
        print(f"Structural Adjustments: {structural}")


def validate_score(score_str: str, points_possible: float) -> Optional[float]:
    """Validate and convert score input"""
    try:
        score = float(score_str)
        if 0 <= score <= points_possible:
            return score
        else:
            print(f"✗ Score must be between 0 and {points_possible}")
            return None
    except ValueError:
        print("✗ Score must be a number")
        return None


def capture_actuals(
    points_possible: float = 40.0,
) -> Dict[str, Any]:
    """Prompt instructor for actual grade + feedback"""
    actual_score = None
    while actual_score is None:
        score_input = input(f"\nYour actual score (0-{points_possible}): ").strip()
        if not score_input:
            print("✗ Score is required")
            continue
        actual_score = validate_score(score_input, points_possible)
    
    actual_feedback = input("Your actual feedback: ").strip()
    
    return {
        "actual_score": actual_score,
        "actual_feedback": actual_feedback,
        "reasoning": None,
    }


def capture_reasoning(
    actual_score: float,
    ai_score_low: Optional[float],
    ai_score_high: Optional[float],
    flag_for_calibration: bool
) -> Optional[str]:
    """Conditionally prompt for reasoning if score differs or flagged for calibration"""
    should_prompt = False
    
    if ai_score_low is not None and ai_score_high is not None:
        if actual_score < ai_score_low or actual_score > ai_score_high:
            print(f"\n⚠ Note: Your score ({actual_score}) differs from AI range ({ai_score_low}-{ai_score_high})")
            should_prompt = True
    
    if flag_for_calibration:
        should_prompt = True
    
    if should_prompt:
        print("\n--- Optional: Why is this a good calibration example? ---")
        print("(e.g., edge case, common pattern, nuance the AI should learn, etc.)")
        print("Keep it brief: 50-150 words. Focus on the key insight, not full explanation.")
        return input("Your reasoning (or press Enter to skip): ").strip() or None
    
    return None


def ask_calibration_flag() -> bool:
    """Ask if this should be added to calibration bank"""
    while True:
        response = input("\nAdd to calibration bank? (y/n): ").strip().lower()
        
        if response == 'y':
            return True
        elif response == 'n':
            return False
        else:
            print("Please enter 'y' or 'n'")


def append_review_session(review: Dict[str, Any], calibration_dir: Path) -> None:
    """Append single review to review_session.jsonl"""
    session_path = calibration_dir / "review_session.jsonl"
    with session_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(review) + "\n")


def append_calibration_example(example: Dict[str, Any], calibration_dir: Path) -> None:
    """Append single calibration example to calibration_payload.jsonl"""
    payload_path = calibration_dir / "calibration_payload.jsonl"
    with payload_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(example) + "\n")


def count_existing_reviews(calibration_dir: Path) -> int:
    """Count lines in review_session.jsonl to enable auto-resume"""
    session_path = calibration_dir / "review_session.jsonl"
    if not session_path.exists():
        return 0
    
    count = 0
    with session_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def update_canonical_record(batch_id: str, record: Dict[str, Any], actuals: Dict[str, Any], flag: bool) -> None:
    """Update canonical grading record with instructor review"""
    stem = Path(record.get("original_filename", "")).stem
    canonical_path = Path(f"artifacts/runs/batches/{batch_id}/grading/canonical/{stem}.json")
    
    if not canonical_path.exists():
        print(f"⚠ Warning: Canonical record not found at {canonical_path}, skipping in-place update")
        return
    
    try:
        with canonical_path.open("r", encoding="utf-8") as f:
            canonical_record = json.load(f)
        
        canonical_record["instructor_review"] = {
            "actual_score": actuals["actual_score"],
            "actual_feedback": actuals["actual_feedback"],
            "reasoning": actuals.get("reasoning"),
            "reviewed_at": datetime.now().isoformat(),
            "flagged_for_calibration": flag
        }
        
        with canonical_path.open("w", encoding="utf-8") as f:
            json.dump(canonical_record, f, indent=2)
    except Exception as e:
        print(f"⚠ Warning: Failed to update canonical record: {e}")


def build_ingest_payload(calibration_dir: Path, assignment_id: str, course: str = "BA101") -> Dict[str, Any]:
    """Build /calibration/ingest payload from calibration_payload.jsonl"""
    payload_path = calibration_dir / "calibration_payload.jsonl"
    
    if not payload_path.exists():
        return {"assignment_id": assignment_id, "course": course, "source": "instructor_review", "examples": []}
    
    examples = []
    with payload_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                ex = json.loads(line)
                examples.append({
                    "submission_text": ex["submission_text"],
                    "feedback_text": ex["instructor_feedback"],
                    "grade_numeric": ex["instructor_score"],
                    "metadata": ex.get("metadata", {})
                })
    
    return {
        "assignment_id": assignment_id,
        "course": course,
        "source": f"instructor_review_{datetime.now().strftime('%Y%m%d')}",
        "examples": examples
    }


def post_to_calibration_api(payload: Dict[str, Any], server: str = "http://localhost:8000") -> Dict[str, Any]:
    """POST to /calibration/ingest"""
    resp = requests.post(f"{server}/calibration/ingest", json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Calibration ingest failed: {resp.status_code} {resp.text[:500]}")
    return resp.json()


def main():
    ap = argparse.ArgumentParser(description="Review batch grading outputs and capture instructor actuals for calibration")
    ap.add_argument("--batch-id", required=True, help="Batch ID to review")
    ap.add_argument("--calibration-id", required=True, help="Calibration session ID")
    ap.add_argument("--start-from", type=int, default=None, help="Start from submission N (default: auto-resume)")
    ap.add_argument("--server", default="http://localhost:8000", help="API server URL")
    ap.add_argument("--ingest", action="store_true", help="POST flagged examples to /calibration/ingest after review")
    args = ap.parse_args()
    
    # Setup calibration directory
    calibration_dir = Path(f"artifacts/runs/calibration/{args.calibration_id}")
    calibration_dir.mkdir(parents=True, exist_ok=True)
    
    # Auto-resume: count existing reviews
    existing_count = count_existing_reviews(calibration_dir)
    start_from = args.start_from if args.start_from is not None else existing_count
    
    if existing_count > 0 and args.start_from is None:
        print(f"ℹ Auto-resuming: found {existing_count} existing reviews, starting from submission {existing_count + 1}")
    
    # Load batch records
    try:
        records = load_batch_rollup(args.batch_id)
    except FileNotFoundError as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
    
    print(f"Loaded {len(records)} records from batch {args.batch_id}")
    
    if start_from >= len(records):
        print(f"✗ Start position {start_from} is beyond available records ({len(records)})")
        sys.exit(1)
    
    # Review loop
    reviewed_count = 0
    flagged_count = 0
    
    for idx in range(start_from, len(records)):
        record = records[idx]
        
        # Enrich with grade data if needed
        record = enrich_record_with_grade_data(record, args.batch_id)
        
        # Skip if not graded or missing essential data
        if record.get("status") != "graded":
            print(f"\nSkipping {record.get('original_filename')}: status={record.get('status')}")
            continue
        
        grade = record.get("grade", {})
        if not grade.get("input") or not grade.get("suggested_feedback"):
            print(f"\n✗ Skipping {record.get('original_filename')}: missing grade.input or grade.suggested_feedback")
            print(f"  (Cannot review without AI grading data)")
            continue
        
        # Display and capture
        display_submission(record, idx, len(records))
        
        points_possible = grade.get("points_possible", 40.0)
        ai_score_low = grade.get("score_low")
        ai_score_high = grade.get("score_high")
        
        # Step 1: Capture actual score and feedback
        actuals = capture_actuals(points_possible=points_possible)
        
        # Step 2: Ask if flagging for calibration
        flag = ask_calibration_flag()
        
        # Step 3: Capture reasoning if applicable (score differs OR flagged)
        reasoning = capture_reasoning(
            actual_score=actuals["actual_score"],
            ai_score_low=ai_score_low,
            ai_score_high=ai_score_high,
            flag_for_calibration=flag
        )
        actuals["reasoning"] = reasoning
        
        # Validate if flagging for calibration
        if flag:
            if actuals["actual_score"] is None:
                print("✗ Cannot flag for calibration: actual_score is missing")
                flag = False
            elif not actuals["actual_feedback"]:
                retry = input("✗ actual_feedback is empty. Add anyway? (y/n): ").strip().lower()
                if retry != 'y':
                    flag = False
        
        # Build review record
        review = {
            "original_filename": record.get("original_filename"),
            "batch_id": args.batch_id,
            "assignment_id": record.get("assignment_id"),
            "ai_score_low": grade.get("score_low"),
            "ai_score_high": grade.get("score_high"),
            "ai_feedback": grade.get("suggested_feedback"),
            "actual_score": actuals["actual_score"],
            "actual_feedback": actuals["actual_feedback"],
            "reasoning": actuals.get("reasoning"),
            "flagged_for_calibration": flag,
            "reviewed_at": datetime.now().isoformat()
        }
        
        # Save review
        append_review_session(review, calibration_dir)
        reviewed_count += 1
        
        # Update canonical record in-place
        update_canonical_record(args.batch_id, record, actuals, flag)
        
        # If flagged, build and save calibration example
        if flag:
            cal_example = {
                "submission_text": grade.get("input"),
                "instructor_feedback": actuals["actual_feedback"],
                "instructor_score": actuals["actual_score"],
                "assignment_id": record.get("assignment_id"),
                "rubric_id": grade.get("rubric_id"),
                "metadata": {
                    "original_filename": record.get("original_filename"),
                    "batch_id": args.batch_id,
                    "paragraph_count": record.get("paragraph_count"),
                    "structural_adjustments": record.get("structural_adjustments", []),
                    "ai_score_low": grade.get("score_low"),
                    "ai_score_high": grade.get("score_high"),
                    "instructor_reasoning": actuals.get("reasoning"),
                }
            }
            append_calibration_example(cal_example, calibration_dir)
            flagged_count += 1
        
        # Continue?
        if idx < len(records) - 1:
            cont = input("\nContinue to next? (y/n/q to quit): ").strip().lower()
            if cont == 'q' or cont == 'n':
                break
    
    # Summary with next-steps preview
    print(f"\n{'='*80}")
    print(f"✓ You've reviewed all {reviewed_count} submissions.")
    print(f"✓ Flagged {flagged_count} for calibration bank")
    print(f"✓ Session saved to: {calibration_dir}")
    
    # Preview next steps
    if flagged_count > 0:
        print(f"\n{'='*80}")
        print(f"NEXT STEPS:")
        if args.ingest:
            print(f"→ Post {flagged_count} flagged examples to calibration API")
            print(f"→ Server: {args.server}")
            cont = input("\nProceed with calibration ingestion? (y/n): ").strip().lower()
            if cont != 'y':
                print("⊘ Ingestion skipped. Run again with --ingest to ingest later.")
                return
        else:
            print(f"→ To ingest these examples to the calibration bank, run:")
            print(f"   ./.venv/bin/python scripts/calibration_review.py \\")
            print(f"     --batch-id {args.batch_id} \\")
            print(f"     --calibration-id {args.calibration_id} \\")
            print(f"     --start-from {len(records)} \\  # Already reviewed, will skip to ingestion")
            print(f"     --ingest")
            return
    else:
        print("\n⊘ No examples flagged for calibration. Session complete.")
        return
    
    # Ingest to calibration API
    if args.ingest and flagged_count > 0:
        print(f"\n--- Ingesting to Calibration Bank ---")
        try:
            assignment_id = records[0].get("assignment_id", "unknown")
            course_id = records[0].get("course_id", "BA101")
            
            payload = build_ingest_payload(calibration_dir, assignment_id, course_id)
            result = post_to_calibration_api(payload, args.server)
            
            # Save ingestion result
            result_path = calibration_dir / "ingestion_result.json"
            with result_path.open("w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            
            print(f"✓ Ingested {result.get('inserted', 0)} examples to calibration bank")
            print(f"✓ Ingestion result saved to {result_path}")
        except Exception as e:
            print(f"✗ Calibration ingestion failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
