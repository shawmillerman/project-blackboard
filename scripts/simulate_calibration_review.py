#!/usr/bin/env python3
"""
Interactive simulation of calibration_review.py workflow
Simulates instructor grading responses for testing without manual input
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from io import StringIO
from unittest.mock import patch


def run_calibration_review_simulation():
    """Simulate running calibration_review with mock input"""
    
    # Import after path is set
    from calibration_review import (
        load_batch_rollup,
        enrich_record_with_grade_data,
        display_submission,
        append_review_session,
        append_calibration_example,
        update_canonical_record,
        build_ingest_payload,
    )
    
    batch_id = "ba101_wk1_grading_20260119"
    calibration_id = f"sim_cal_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    calibration_dir = Path(f"artifacts/runs/calibration/{calibration_id}")
    
    print(f"\n{'='*80}")
    print(f"CALIBRATION REVIEW SIMULATION")
    print(f"Batch: {batch_id}")
    print(f"Session: {calibration_id}")
    print(f"{'='*80}")
    
    # Setup
    calibration_dir.mkdir(parents=True, exist_ok=True)
    (calibration_dir / "review_session.jsonl").touch()
    (calibration_dir / "calibration_payload.jsonl").touch()
    
    # Load records
    records = load_batch_rollup(batch_id)
    print(f"\nLoaded {len(records)} records")
    
    # Simulate reviewing first 3 records
    num_to_review = min(3, len(records))
    reviewed_count = 0
    flagged_count = 0
    
    # Mock input responses for 3 submissions
    # Competency levels: 1=Meets (100%), 2=Needs Improvement (75%), 3=Did Not Meet (50%)
    mock_responses = [
        # Submission 1: Meets/Meets/Meets = 15+15+10 = 40, don't flag
        {
            "directions_level": "1",  # Meets Expectations (15)
            "content_level": "1",     # Meets Expectations (15)
            "style_level": "1",       # Meets Expectations (10)
            "feedback": "Excellent work! You've clearly identified all key resources needed for the surfboard business and explained how they work together. Your understanding of both capital and entrepreneurial skills is particularly strong.",
            "calibrate": "n",
        },
        # Submission 2: Meets/Needs Improvement/Meets = 15+11.25+10 = 36.25, flag for calibration
        {
            "directions_level": "1",  # Meets Expectations (15)
            "content_level": "2",     # Needs Improvement (11.25)
            "style_level": "1",       # Meets Expectations (10)
            "feedback": "Good identification of resources and funding sources. You could improve by more clearly explaining how the business owner coordinates all these resources and takes on the entrepreneurial risk.",
            "calibrate": "y",
            "reasoning": "Common pattern: students understand resources but don't fully explain entrepreneur's coordinating role."
        },
        # Submission 3: Did Not Meet/Did Not Meet/Needs Improvement = 7.5+7.5+7.5 = 22.5, flag for calibration
        {
            "directions_level": "3",  # Did Not Meet (7.5)
            "content_level": "3",     # Did Not Meet (7.5)
            "style_level": "2",       # Needs Improvement (7.5)
            "feedback": "Your response misses several key resource types that a surfboard manufacturer would need. You mention materials and labor but don't address capital equipment, entrepreneurial decision-making, or how these work together.",
            "calibrate": "y",
            "reasoning": "Edge case: shows incomplete understanding of resource coordination."
        }
    ]
    
    for idx in range(num_to_review):
        record = records[idx]
        record = enrich_record_with_grade_data(record, batch_id)
        
        if record.get("status") != "graded":
            print(f"\nSkipping submission {idx+1}: not graded")
            continue
        
        grade = record.get("grade", {})
        if not grade.get("input") or not grade.get("suggested_feedback"):
            print(f"\nSkipping submission {idx+1}: missing grade data")
            continue
        
        print(f"\n{'─'*80}")
        print(f"SUBMISSION {idx+1}/{num_to_review}: {record.get('original_filename')}")
        print(f"{'─'*80}")
        
        # Display submission
        points_possible = grade.get("points_possible", 40.0)
        print(f"\nStudent Text (first 300 chars):")
        print(grade.get("input", "N/A")[:300] + "...")
        print(f"\nAI Suggested Feedback:")
        print(grade.get("suggested_feedback", "N/A"))
        print(f"\nScore Range: {grade.get('score_low')} - {grade.get('score_high')} (out of {points_possible})")
        
        # Simulate instructor responses
        responses = mock_responses[idx]
        print(f"\n--- Simulated Instructor Input (Competency Levels) ---")
        
        # Map competency level to points and level name
        level_map = {
            "1": ("Meets Expectations", 1.0),
            "2": ("Needs Improvement", 0.75),
            "3": ("Did Not Meet", 0.5),
        }
        
        directions_level_name, directions_mult = level_map[responses["directions_level"]]
        content_level_name, content_mult = level_map[responses["content_level"]]
        style_level_name, style_mult = level_map[responses["style_level"]]
        
        directions_score = 15.0 * directions_mult
        content_score = 15.0 * content_mult
        style_score = 10.0 * style_mult
        actual_score = directions_score + content_score + style_score
        
        print(f"Directions: {directions_level_name} ({directions_score}/15)")
        print(f"Content: {content_level_name} ({content_score}/15)")
        print(f"Style: {style_level_name} ({style_score}/10)")
        print(f"Total Score: {actual_score}/40")
        print(f"Feedback: {responses['feedback']}")
        
        # Build review
        actuals = {
            "actual_score": actual_score,
            "actual_feedback": responses["feedback"],
            "reasoning": responses.get("reasoning"),
            "component_scores": {
                "directions": directions_score,
                "content": content_score,
                "style": style_score,
            },
            "component_levels": {
                "directions": directions_level_name,
                "content": content_level_name,
                "style": style_level_name,
            }
        }
        
        flag = responses["calibrate"] == "y"
        print(f"Flag for calibration: {'Yes' if flag else 'No'}")
        
        # Save review
        review = {
            "original_filename": record.get("original_filename"),
            "batch_id": batch_id,
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
        
        append_review_session(review, calibration_dir)
        reviewed_count += 1
        
        # Update canonical record
        try:
            update_canonical_record(batch_id, record, actuals, flag)
        except Exception as e:
            print(f"Warning: Could not update canonical record: {e}")
        
        # If flagged, save calibration example
        if flag:
            metadata = {
                "original_filename": record.get("original_filename"),
                "batch_id": batch_id,
                "paragraph_count": record.get("paragraph_count"),
                "ai_score_low": grade.get("score_low"),
                "ai_score_high": grade.get("score_high"),
                "instructor_reasoning": actuals.get("reasoning"),
            }
            if actuals.get("component_scores"):
                metadata["component_scores"] = actuals["component_scores"]
            if actuals.get("component_levels"):
                metadata["component_levels"] = actuals["component_levels"]
            
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
            print(f"✓ Added to calibration bank")
    
    # Summary
    print(f"\n{'='*80}")
    print(f"SIMULATION COMPLETE")
    print(f"{'='*80}")
    print(f"✓ Reviewed: {reviewed_count} submissions")
    print(f"✓ Flagged: {flagged_count} for calibration")
    print(f"✓ Session: {calibration_dir}")
    
    # Show summary of session
    session_path = calibration_dir / "review_session.jsonl"
    if session_path.exists():
        with session_path.open("r") as f:
            lines = f.readlines()
        print(f"✓ Review session file: {len(lines)} records")
    
    # Show summary of calibration payload
    payload_path = calibration_dir / "calibration_payload.jsonl"
    if payload_path.exists():
        with payload_path.open("r") as f:
            lines = f.readlines()
        print(f"✓ Calibration payload file: {len(lines)} examples")
        
        # Display payload structure
        if lines:
            first_example = json.loads(lines[0])
            print(f"\nFirst calibration example:")
            print(f"  - Submission text length: {len(first_example.get('submission_text', ''))}")
            print(f"  - Instructor score: {first_example.get('instructor_score')}")
            print(f"  - Assignment: {first_example.get('assignment_id')}")
    
    # Try to build ingest payload
    payload = build_ingest_payload(calibration_dir, "business_activity_week1", "BA101")
    print(f"\n✓ Ingest payload ready:")
    print(f"  - Assignment: {payload.get('assignment_id')}")
    print(f"  - Course: {payload.get('course')}")
    print(f"  - Source: {payload.get('source')}")
    print(f"  - Examples: {len(payload.get('examples', []))}")
    
    return calibration_id


def run_flat_scoring_simulation():
    """Simulate flat scoring mode (single score without component breakdown)"""
    
    from calibration_review import (
        load_batch_rollup,
        enrich_record_with_grade_data,
        append_review_session,
        append_calibration_example,
        build_ingest_payload,
    )
    
    batch_id = "ba101_wk1_grading_20260119"
    calibration_id = f"sim_flat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    calibration_dir = Path(f"artifacts/runs/calibration/{calibration_id}")
    
    print(f"\n{'='*80}")
    print(f"FLAT SCORING SIMULATION")
    print(f"Batch: {batch_id}")
    print(f"Session: {calibration_id}")
    print(f"{'='*80}")
    
    # Setup
    calibration_dir.mkdir(parents=True, exist_ok=True)
    (calibration_dir / "review_session.jsonl").touch()
    (calibration_dir / "calibration_payload.jsonl").touch()
    
    # Load records
    records = load_batch_rollup(batch_id)
    print(f"\nLoaded {len(records)} records")
    
    # Simulate reviewing 2 submissions with flat scoring
    num_to_review = min(2, len(records))
    
    # Mock flat scoring responses (competency level only)
    mock_responses = [
        {
            "overall_level": "1",  # Meets Expectations (40/40)
            "feedback": "Excellent comprehensive answer covering all resource types with clear examples.",
            "calibrate": "y",
            "reasoning": "Exemplary flat-scored response."
        },
        {
            "overall_level": "2",  # Needs Improvement (30/40)
            "feedback": "Good attempt but needs more depth on entrepreneurial coordination.",
            "calibrate": "n",
        }
    ]
    
    reviewed_count = 0
    flagged_count = 0
    
    for idx in range(num_to_review):
        record = records[idx]
        record = enrich_record_with_grade_data(record, batch_id)
        
        if record.get("status") != "graded":
            continue
        
        grade = record.get("grade", {})
        if not grade.get("input") or not grade.get("suggested_feedback"):
            continue
        
        print(f"\n{'─'*80}")
        print(f"SUBMISSION {idx+1}/{num_to_review}: {record.get('original_filename')}")
        print(f"{'─'*80}")
        
        # Display submission (abbreviated)
        print(f"\nStudent Text (first 200 chars):")
        print(grade.get("input", "N/A")[:200] + "...")
        print(f"\nAI Score Range: {grade.get('score_low')} - {grade.get('score_high')}")
        
        # Simulate flat scoring
        responses = mock_responses[idx]
        print(f"\n--- Simulated Instructor Input (Flat Scoring) ---")
        
        level_map = {
            "1": ("Meets Expectations", 1.0),
            "2": ("Needs Improvement", 0.75),
            "3": ("Did Not Meet", 0.5),
        }
        
        overall_level_name, multiplier = level_map[responses["overall_level"]]
        actual_score = 40.0 * multiplier
        
        print(f"Overall Performance: {overall_level_name} ({actual_score}/40)")
        print(f"Feedback: {responses['feedback']}")
        
        actuals = {
            "actual_score": actual_score,
            "actual_feedback": responses["feedback"],
            "reasoning": responses.get("reasoning"),
            "overall_level": overall_level_name,
        }
        
        flag = responses["calibrate"] == "y"
        print(f"Flag for calibration: {'Yes' if flag else 'No'}")
        
        # Save review
        review = {
            "original_filename": record.get("original_filename"),
            "batch_id": batch_id,
            "assignment_id": record.get("assignment_id"),
            "ai_score_low": grade.get("score_low"),
            "ai_score_high": grade.get("score_high"),
            "ai_feedback": grade.get("suggested_feedback"),
            "actual_score": actuals["actual_score"],
            "actual_feedback": actuals["actual_feedback"],
            "reasoning": actuals.get("reasoning"),
            "flagged_for_calibration": flag,
            "reviewed_at": datetime.now().isoformat(),
            "scoring_mode": "flat",
        }
        
        append_review_session(review, calibration_dir)
        reviewed_count += 1
        
        # If flagged, save calibration example
        if flag:
            metadata = {
                "original_filename": record.get("original_filename"),
                "batch_id": batch_id,
                "scoring_mode": "flat",
                "overall_level": actuals["overall_level"],
                "instructor_reasoning": actuals.get("reasoning"),
            }
            
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
            print(f"✓ Added to calibration bank")
    
    # Summary
    print(f"\n{'='*80}")
    print(f"FLAT SCORING SIMULATION COMPLETE")
    print(f"{'='*80}")
    print(f"✓ Reviewed: {reviewed_count} submissions (flat scoring mode)")
    print(f"✓ Flagged: {flagged_count} for calibration")
    print(f"✓ Session: {calibration_dir}")
    
    payload = build_ingest_payload(calibration_dir, "business_activity_week1", "BA101")
    print(f"\n✓ Ingest payload ready:")
    print(f"  - Assignment: {payload.get('assignment_id')}")
    print(f"  - Examples: {len(payload.get('examples', []))}")
    
    return calibration_id


def main():
    # Add scripts directory to path
    sys.path.insert(0, str(Path(__file__).parent))
    
    try:
        # Run component-based simulation
        print("="*80)
        print("RUNNING COMPONENT-BASED SIMULATION")
        print("="*80)
        session_id_1 = run_calibration_review_simulation()
        
        # Run flat scoring simulation
        print("\n\n")
        session_id_2 = run_flat_scoring_simulation()
        
        print(f"\n{'='*80}")
        print(f"✓ Both simulations successful!")
        print(f"  Component-based: {session_id_1}")
        print(f"  Flat scoring: {session_id_2}")
        return 0
    except Exception as e:
        print(f"\n✗ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
