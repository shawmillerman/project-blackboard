# Calibration Review Workflow – Quick Reference

## Overview
The calibration review workflow allows instructors to review AI-graded submissions, provide actual grades, and flag exemplary or problematic submissions to improve the calibration bank.

---

## Running the Calibration Review

### Basic Usage
```bash
python scripts/calibration_review.py \
  --batch-id ba101_wk1_grading_20260119 \
  --calibration-id ba101_week1_cal_20260119
```

### With Auto-Resume (default)
```bash
# Automatically resumes from where you left off
python scripts/calibration_review.py \
  --batch-id ba101_wk1_grading_20260119 \
  --calibration-id business_activity_week1_cal_20260119
```

### Start from a Specific Submission
```bash
python scripts/calibration_review.py \
  --batch-id ba101_wk1_grading_20260119 \
  --calibration-id business_activity_week1_cal_20260119 \
  --start-from 5
```

### With API Ingestion
```bash
python scripts/calibration_review.py \
  --batch-id ba101_wk1_grading_20260119 \
  --calibration-id business_activity_week1_cal_20260119 \
  --ingest
```

---

## Workflow Steps

### 1. Review Submission
For each graded submission, you see:
- Student's original text (first 400 chars)
- AI suggested feedback
- AI score range (low - high out of 40 points)

### 2. Score Submission (Competency Levels)
Select a competency level for each component:
- **Adherence to Directions (15 points max)**
  - 1) Meets Expectations: 15 points (100%)
  - 2) Needs Improvement: 11.25 points (75%)
  - 3) Did Not Meet: 7.5 points (50%)

- **Content Quality (15 points max)**
  - 1) Meets Expectations: 15 points (100%)
  - 2) Needs Improvement: 11.25 points (75%)
  - 3) Did Not Meet: 7.5 points (50%)

- **Style Guide Compliance (10 points max)**
  - 1) Meets Expectations: 10 points (100%)
  - 2) Needs Improvement: 7.5 points (75%)
  - 3) Did Not Meet: 5 points (50%)

- **Total Points Possible: 40 points (range: 20-40)**

Example:
```
Adherence to Directions (15 points possible):
  1) Meets Expectations (100%)
  2) Needs Improvement (75%)
  3) Did Not Meet (50%)
Select level (1-3): 1
  ✓ Meets Expectations: 15/15 points

Content Quality (15 points possible):
  1) Meets Expectations (100%)
  2) Needs Improvement (75%)
  3) Did Not Meet (50%)
Select level (1-3): 2
  ✓ Needs Improvement: 11.25/15 points

Style Guide Compliance (10 points possible):
  1) Meets Expectations (100%)
  2) Needs Improvement (75%)
  3) Did Not Meet (50%)
Select level (1-3): 1
  ✓ Meets Expectations: 10/10 points

✓ Total Score: 36.25/40
```

### 3. Enter Feedback
Provide your actual feedback:
```
Your actual feedback: This shows good understanding. Consider explaining...
```

### 4. Optional: Flag for Calibration
If your score differs from the AI range OR you want to add this as an exemplary example:
```
Add to calibration bank? (y/n): y
```

If flagged, you can provide reasoning:
```
Why is this a good calibration example?
(e.g., edge case, common pattern, nuance the AI should learn, etc.)
Your reasoning (or press Enter to skip): This exemplifies excellent resource identification
```

### 5. Continue or Quit
After each submission:
```
Continue to next? (y/n/q to quit): y
```

---

## Output Files

Each calibration session creates:

### `review_session.jsonl`
All reviews in JSON Lines format:
```json
{
  "original_filename": "anon-001-raw.pdf",
  "batch_id": "ba101_wk1_grading_20260119",
  "assignment_id": "business_activity_week1",
  "ai_score_low": 21.0,
  "ai_score_high": 40.0,
  "ai_feedback": "AI feedback text",
  "actual_score": 37.0,
  "actual_feedback": "Your feedback text",
  "reasoning": "Your reasoning if flagged",
  "flagged_for_calibration": false,
  "reviewed_at": "2026-01-19T14:24:11.220997"
}
```

### `calibration_payload.jsonl`
Flagged examples ready for ingestion:
```json
{
  "submission_text": "Student's answer...",
  "instructor_feedback": "Your feedback...",
  "instructor_score": 39.0,
  "assignment_id": "business_activity_week1",
  "rubric_id": null,
  "metadata": {
    "original_filename": "anon-002-raw.docx",
    "component_scores": {
      "directions": 15.0,
      "content": 15.0,
      "style": 9.0
    },
    "instructor_reasoning": "Exemplary response..."
  }
}
```

### `ingestion_result.json` (if using --ingest)
Result from API:
```json
{
  "status": "ok",
  "inserted": 2,
  "assignment_id": "business_activity_week1"
}
```

---

## Testing

### Unit Tests
```bash
python scripts/test_calibration_review.py
```
Tests individual components:
- Batch loading
- Record enrichment
- Session setup
- Review writing
- Payload building

### Integration Simulation
```bash
python scripts/simulate_calibration_review.py
```
Simulates full workflow with mock instructor responses

---

## Tips & Troubleshooting

### Resuming a Session
If interrupted, run the same command again:
```bash
python scripts/calibration_review.py \
  --batch-id ba101_wk1_grading_20260119 \
  --calibration-id ba101_week1_cal_20260119
```
The script auto-detects how many reviews are done and resumes from the next submission.

### Finding Available Batches
```bash
ls artifacts/runs/batches/
```

### Checking Calibration Sessions
```bash
ls artifacts/runs/calibration/
```

### Reviewing What You've Flagged
```bash
cat artifacts/runs/calibration/{calibration_id}/calibration_payload.jsonl
```

### Re-ingesting Failed Examples
If ingestion fails, try again with:
```bash
python scripts/calibration_review.py \
  --batch-id {batch_id} \
  --calibration-id {calibration_id} \
  --start-from {total_records} \
  --ingest
```

---

## Best Practices for Calibration Examples

When flagging examples for calibration:

1. **Exemplary Responses**
   - Provide clear reasoning: "Comprehensive answer with specific details"
   - These improve the AI's understanding of high-quality responses

2. **Gap Analysis**
   - Identify what's missing: "Student understands resources but not entrepreneur's role"
   - These help the AI recognize common gaps

3. **Edge Cases**
   - Unusual but valid answers: "Alternative phrasing that is also correct"
   - These improve AI's robustness

4. **Score Divergence**
   - When your score significantly differs from AI range, flag it
   - These help calibrate the AI's scoring confidence

---

## Server Configuration

Default API server: `http://localhost:8000`

To use a different server:
```bash
python scripts/calibration_review.py \
  --batch-id ba101_wk1_grading_20260119 \
  --calibration-id business_activity_week1_cal_20260119 \
  --server http://api.example.com:8000 \
  --ingest
```

---

## Data Persistence

All sessions are saved to:
```
artifacts/runs/calibration/{calibration_id}/
```

This directory contains:
- Review audit trail (review_session.jsonl)
- Flagged examples ready for ingest (calibration_payload.jsonl)
- API response record (ingestion_result.json)

---

## Status

✅ **Calibration review workflow is tested and ready for use**

See [CALIBRATION_REVIEW_TEST_REPORT.md](CALIBRATION_REVIEW_TEST_REPORT.md) for detailed test results.
