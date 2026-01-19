#!/usr/bin/env python3
"""
Assessment Workflow – Calibration Review
Iterates through batch grading outputs, captures instructor actuals, flags for calibration.

Usage:
  python scripts/calibration_review.py \
    --batch-id ba101_wk1_full \
    --calibration-id business_activity_week1_cal_20260118 \
    [--start-from 5]  # Resume from submission N (default: auto-detect from review_session.jsonl)
"""

import argparse
import json
import sys
import os
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


def load_batch_rollup(batch_id: str) -> List[Dict[str, Any]]:
    """Load graded submissions from canonical directory (deduplicated)"""
    canonical_dir = Path(f"artifacts/runs/batches/{batch_id}/grading/canonical")
    if not canonical_dir.exists():
        raise FileNotFoundError(f"Canonical grading directory not found: {canonical_dir}")
    
    records = []
    for json_file in sorted(canonical_dir.glob("*.json")):
        try:
            with json_file.open("r", encoding="utf-8") as f:
                record = json.load(f)
                # Only include graded submissions
                if record.get("status") == "graded":
                    records.append(record)
        except Exception as e:
            print(f"Warning: Failed to load {json_file.name}: {e}")
    
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
    points_possible = grade.get('points_possible', 40)
    print(f"Score Range: {grade.get('score_low', 'N/A')} - {grade.get('score_high', 'N/A')} (out of {points_possible} points)")
    print(f"\nSuggested Feedback:")
    print(grade.get('suggested_feedback', 'N/A'))
    
    citations_count = len(grade.get('citations', []))
    print(f"\nCitations: {citations_count} sources")
    
    structural = record.get('structural_adjustments', [])
    if structural:
        print(f"Structural Adjustments: {structural}")


def select_competency_level(component_name: str, max_points: float) -> Tuple[str, float]:
    """Prompt instructor to select competency level for a component"""
    levels = {
        "1": ("Meets Expectations", 1.0),  # 100% of points
        "2": ("Needs Improvement", 0.75),  # 75% of points
        "3": ("Did Not Meet", 0.5),        # 50% of points
    }
    
    print(f"\n{component_name} ({max_points} points possible):")
    print("  1) Meets Expectations (100%)")
    print("  2) Needs Improvement (75%)")
    print("  3) Did Not Meet (50%)")
    
    while True:
        choice = input(f"Select level (1-3): ").strip()
        if choice in levels:
            level_name, multiplier = levels[choice]
            points = max_points * multiplier
            print(f"  ✓ {level_name}: {points}/{max_points} points")
            return level_name, points
        else:
            print("✗ Please enter 1, 2, or 3")


def capture_actuals(
    points_possible: float = 40.0,
    ai_score_low: Optional[float] = None,
    ai_score_high: Optional[float] = None,
    flag_for_calibration: bool = False,
    use_flat_scoring: bool = False,
) -> Dict[str, Any]:
    """Prompt instructor for actual grade via competency levels + feedback, with optional reasoning
    
    Args:
        points_possible: Maximum points for the assignment (default 40)
        ai_score_low: AI's low score estimate
        ai_score_high: AI's high score estimate
        flag_for_calibration: Whether this is flagged for calibration
        use_flat_scoring: If True, use single score without component breakdown
    """
    
    if use_flat_scoring:
        # Flat scoring mode: single competency level for total score
        print("\n--- Overall Competency Level (Flat Scoring) ---")
        overall_level, actual_score = select_competency_level("Overall Performance", points_possible)
        
        result = {
            "actual_score": actual_score,
            "overall_level": overall_level,
        }
    else:
        # Component-based scoring: Directions (15), Content (15), Style (10)
        print("\n--- Component Competency Levels ---")
        
        directions_level, directions_score = select_competency_level("Adherence to Directions", 15.0)
        content_level, content_score = select_competency_level("Content Quality", 15.0)
        style_level, style_score = select_competency_level("Style Guide Compliance", 10.0)
        
        actual_score = directions_score + content_score + style_score
        print(f"\n✓ Total Score: {actual_score}/{points_possible}")
        
        result = {
            "actual_score": actual_score,
            "component_scores": {
                "directions": directions_score,
                "content": content_score,
                "style": style_score,
            },
            "component_levels": {
                "directions": directions_level,
                "content": content_level,
                "style": style_level,
            },
        }
    
    actual_feedback = input("\nYour actual feedback: ").strip()
    result["actual_feedback"] = actual_feedback
    
    # Conditional reasoning prompt: triggered if score diverges from AI or flagging for calibration
    reasoning = None
    should_prompt_reasoning = False
    
    if ai_score_low is not None and ai_score_high is not None:
        if actual_score < ai_score_low or actual_score > ai_score_high:
            print(f"\n⚠ Note: Your score ({actual_score}) differs from AI range ({ai_score_low}-{ai_score_high})")
            should_prompt_reasoning = True
    
    if flag_for_calibration:
        should_prompt_reasoning = True
    
    if should_prompt_reasoning:
        print("\n--- Optional: Why is this a good calibration example? ---")
        print("(e.g., edge case, common pattern, nuance the AI should learn, etc.)")
        reasoning = input("Your reasoning (or press Enter to skip): ").strip() or None
    
    result["reasoning"] = reasoning
    return result


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
                example = {
                    "submission_text": ex["submission_text"],
                    "feedback_text": ex["instructor_feedback"],
                    "grade_numeric": ex["instructor_score"],
                    "metadata": ex.get("metadata", {})
                }
                # Include component scores if available
                if ex.get("component_scores"):
                    example["component_scores"] = ex["component_scores"]
                examples.append(example)
    
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
    ap = argparse.ArgumentParser(description="Assessment Workflow: Calibration Review (instructor validation and calibration ingest)")
    ap.add_argument("--batch-id", required=True, help="Batch ID to review")
    ap.add_argument("--calibration-id", required=True, help="Calibration session ID")
    ap.add_argument("--start-from", type=int, default=None, help="Start from submission N (default: auto-resume)")
    ap.add_argument("--server", default="http://localhost:8000", help="API server URL")
    ap.add_argument("--ingest", action="store_true", help="POST flagged examples to /calibration/ingest after review")
    ap.add_argument("--flat-scoring", action="store_true", help="Use flat scoring (single score) instead of component breakdown")
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
        
        # Capture actuals FIRST (grade + feedback)
        actuals = capture_actuals(
            points_possible=points_possible,
            ai_score_low=grade.get("score_low"),
            ai_score_high=grade.get("score_high"),
            use_flat_scoring=args.flat_scoring,
        )
        
        # THEN ask if flagging for calibration
        flag = ask_calibration_flag()
        
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
            metadata = {
                "original_filename": record.get("original_filename"),
                "batch_id": args.batch_id,
                "paragraph_count": record.get("paragraph_count"),
                "structural_adjustments": record.get("structural_adjustments", []),
                "ai_score_low": grade.get("score_low"),
                "ai_score_high": grade.get("score_high"),
                "instructor_reasoning": actuals.get("reasoning"),
                "scoring_mode": "flat" if args.flat_scoring else "component",
            }
            # Include component scores and levels if available (component-based mode)
            if actuals.get("component_scores"):
                metadata["component_scores"] = actuals["component_scores"]
            if actuals.get("component_levels"):
                metadata["component_levels"] = actuals["component_levels"]
            # Include overall level if available (flat scoring mode)
            if actuals.get("overall_level"):
                metadata["overall_level"] = actuals["overall_level"]
            
            cal_example = {
                "submission_text": grade.get("input"),
                "instructor_feedback": actuals["actual_feedback"],
                "instructor_score": actuals["actual_score"],
                "assignment_id": record.get("assignment_id"),
                "rubric_id": grade.get("rubric_id"),
                "metadata": metadata
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
