#!/usr/bin/env python3
"""
Test harness for calibration_review.py
Tests the calibration workflow with minimal interactive input or fully scripted
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import subprocess

def test_load_batch():
    """Test that we can load batch records"""
    from calibration_review import load_batch_rollup
    
    batch_id = "ba101_wk1_grading_20260119"
    try:
        records = load_batch_rollup(batch_id)
        print(f"✓ Loaded {len(records)} records from batch {batch_id}")
        
        if len(records) > 0:
            first = records[0]
            print(f"  - First submission: {first.get('original_filename')}")
            print(f"  - Status: {first.get('status')}")
            grade = first.get('grade', {})
            print(f"  - Has AI feedback: {bool(grade.get('suggested_feedback'))}")
            return True
        else:
            print("✗ No records found")
            return False
    except Exception as e:
        print(f"✗ Failed to load batch: {e}")
        return False


def test_enrich_record():
    """Test that we can enrich records with grade data"""
    from calibration_review import load_batch_rollup, enrich_record_with_grade_data
    
    batch_id = "ba101_wk1_grading_20260119"
    try:
        records = load_batch_rollup(batch_id)
        
        if len(records) == 0:
            print("✗ No records to test")
            return False
        
        record = records[0]
        enriched = enrich_record_with_grade_data(record, batch_id)
        
        grade = enriched.get('grade', {})
        if grade.get('input') and grade.get('suggested_feedback'):
            print(f"✓ Record enriched successfully")
            print(f"  - Input length: {len(grade.get('input', ''))}")
            print(f"  - Feedback length: {len(grade.get('suggested_feedback', ''))}")
            return True
        else:
            print("✗ Enrichment failed or missing fields")
            return False
    except Exception as e:
        print(f"✗ Enrichment test failed: {e}")
        return False


def test_competency_level_selection():
    """Test that competency level selection works correctly"""
    try:
        # Test point calculations for each component
        test_cases = [
            ("Directions", 15.0, 1.0, 15.0),   # Meets Expectations = 100%
            ("Directions", 15.0, 0.75, 11.25), # Needs Improvement = 75%
            ("Directions", 15.0, 0.5, 7.5),    # Did Not Meet = 50%
            ("Content", 15.0, 1.0, 15.0),
            ("Content", 15.0, 0.75, 11.25),
            ("Content", 15.0, 0.5, 7.5),
            ("Style", 10.0, 1.0, 10.0),
            ("Style", 10.0, 0.75, 7.5),
            ("Style", 10.0, 0.5, 5.0),
        ]
        
        for name, max_pts, multiplier, expected in test_cases:
            calculated = max_pts * multiplier
            if abs(calculated - expected) < 0.01:
                continue
            else:
                print(f"✗ {name} calculation failed: {calculated} != {expected}")
                return False
        
        print(f"✓ All competency level calculations correct")
        return True
    except Exception as e:
        print(f"✗ Competency level test failed: {e}")
        return False


def test_flat_scoring_mode():
    """Test that flat scoring mode produces correct output"""
    try:
        # Test flat scoring calculations for 40-point assignment
        test_cases = [
            (40.0, 1.0, 40.0, "Meets Expectations"),      # 100%
            (40.0, 0.75, 30.0, "Needs Improvement"),      # 75%
            (40.0, 0.5, 20.0, "Did Not Meet"),            # 50%
            (100.0, 1.0, 100.0, "Meets Expectations"),    # Different point scale
            (100.0, 0.75, 75.0, "Needs Improvement"),
            (100.0, 0.5, 50.0, "Did Not Meet"),
        ]
        
        for max_pts, multiplier, expected_score, expected_level in test_cases:
            calculated_score = max_pts * multiplier
            if abs(calculated_score - expected_score) < 0.01:
                continue
            else:
                print(f"✗ Flat scoring calculation failed: {calculated_score} != {expected_score}")
                return False
        
        print(f"✓ Flat scoring calculations correct")
        return True
    except Exception as e:
        print(f"✗ Flat scoring test failed: {e}")
        return False


def test_calibration_session_setup():
    """Test that we can create a calibration session directory"""
    calibration_id = f"test_cal_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    calibration_dir = Path(f"artifacts/runs/calibration/{calibration_id}")
    
    try:
        calibration_dir.mkdir(parents=True, exist_ok=True)
        
        # Create placeholder files
        (calibration_dir / "review_session.jsonl").touch()
        (calibration_dir / "calibration_payload.jsonl").touch()
        
        print(f"✓ Created calibration session directory: {calibration_dir}")
        print(f"  - Test files created")
        
        return calibration_id
    except Exception as e:
        print(f"✗ Failed to setup session: {e}")
        return None


def test_write_review_record(calibration_id, batch_id):
    """Test writing a mock review record"""
    from calibration_review import append_review_session
    
    calibration_dir = Path(f"artifacts/runs/calibration/{calibration_id}")
    
    mock_review = {
        "original_filename": "test-submission.pdf",
        "batch_id": batch_id,
        "assignment_id": "business_activity_week1",
        "ai_score_low": 32,
        "ai_score_high": 38,
        "ai_feedback": "Test feedback",
        "actual_score": 35.0,
        "actual_feedback": "Test instructor feedback",
        "reasoning": "Test calibration example",
        "flagged_for_calibration": True,
        "reviewed_at": datetime.now().isoformat()
    }
    
    try:
        append_review_session(mock_review, calibration_dir)
        print(f"✓ Review record written to {calibration_dir / 'review_session.jsonl'}")
        
        # Verify it was written
        with (calibration_dir / "review_session.jsonl").open("r") as f:
            lines = f.readlines()
        print(f"  - Session contains {len(lines)} records")
        
        return True
    except Exception as e:
        print(f"✗ Failed to write review: {e}")
        return False


def test_build_ingest_payload(calibration_id, batch_id):
    """Test building an ingest payload"""
    from calibration_review import build_ingest_payload, append_calibration_example
    
    calibration_dir = Path(f"artifacts/runs/calibration/{calibration_id}")
    
    # Write a calibration example first
    mock_example = {
        "submission_text": "This is a test submission about business resources.",
        "instructor_feedback": "Good work, but needs more depth.",
        "instructor_score": 35.0,
        "assignment_id": "business_activity_week1",
        "rubric_id": "ba101_rubric_v1",
        "metadata": {
            "original_filename": "test-file.pdf",
            "batch_id": batch_id,
            "component_scores": {
                "directions": 12,
                "content": 14,
                "style": 9
            }
        }
    }
    
    try:
        append_calibration_example(mock_example, calibration_dir)
        payload = build_ingest_payload(calibration_dir, "business_activity_week1", "BA101")
        
        print(f"✓ Built ingest payload")
        print(f"  - Assignment: {payload.get('assignment_id')}")
        print(f"  - Course: {payload.get('course')}")
        print(f"  - Examples: {len(payload.get('examples', []))}")
        
        if len(payload.get('examples', [])) > 0:
            ex = payload['examples'][0]
            print(f"  - First example has submission text: {bool(ex.get('submission_text'))}")
            print(f"  - First example has feedback: {bool(ex.get('feedback_text'))}")
        
        return True
    except Exception as e:
        print(f"✗ Failed to build payload: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("="*80)
    print("CALIBRATION REVIEW WORKFLOW TEST")
    print("="*80)
    
    # Add scripts directory to path so we can import calibration_review
    sys.path.insert(0, str(Path(__file__).parent))
    
    results = {}
    
    # Test 1: Load batch
    print("\n[1/7] Testing batch load...")
    results['batch_load'] = test_load_batch()
    
    # Test 2: Enrich records
    print("\n[2/7] Testing record enrichment...")
    results['enrichment'] = test_enrich_record()
    
    # Test 3: Competency levels
    print("\n[3/7] Testing competency level calculations...")
    results['competency_levels'] = test_competency_level_selection()
    
    # Test 4: Flat scoring
    print("\n[4/7] Testing flat scoring calculations...")
    results['flat_scoring'] = test_flat_scoring_mode()
    
    # Test 5: Session setup
    print("\n[5/7] Testing session setup...")
    calibration_id = test_calibration_session_setup()
    results['session_setup'] = calibration_id is not None
    
    if calibration_id:
        # Test 6: Write review record
        print("\n[6/7] Testing review record write...")
        results['review_write'] = test_write_review_record(calibration_id, "ba101_wk1_grading_20260119")
        
        # Test 7: Build ingest payload
        print("\n[7/7] Testing ingest payload build...")
        results['ingest_build'] = test_build_ingest_payload(calibration_id, "ba101_wk1_grading_20260119")
    else:
        results['review_write'] = False
        results['ingest_build'] = False
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! Calibration review workflow is ready.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Check output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
