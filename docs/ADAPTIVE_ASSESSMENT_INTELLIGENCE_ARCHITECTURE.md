# Adaptive Assessment Intelligence — Architecture Specification

**Version:** 1.0  
**Date:** January 21, 2026  
**Status:** Design / Pre-implementation

---

## Executive Summary

The **Adaptive Assessment Intelligence (AAI)** is the core intellectual property and algorithmic foundation of ProjectBlackboard. It produces AI-assisted grade ranges and draft feedback that reflect an instructor's voice, pedagogical philosophy, rubric interpretation, and temporal expectations—then refines itself through structured calibration as instructors finalize grades.

This system is:
- **Adaptive:** Learns instructor-specific standards, tone, and judgment through calibration loops
- **Context-aware:** Models week-of-term rigor progression (formative → summative)
- **Explainable:** Traces every judgment back to rubric criteria, course outcomes, and evidence
- **Dual-purpose:** Powers both instructor grading workflows and student QA interactions

---

## Strategic Context

### The "I Am Just a Text File" Philosophy

Inspired by [ruben.substack.com/p/i-am-just-a-text-file](https://ruben.substack.com/p/i-am-just-a-text-file), we treat instructor voice, pedagogy, and grading logic as **structured, version-controlled text artifacts** rather than opaque model weights.

**Key principles:**
- Voice specs, rubric mappings, rigor profiles, and calibration data are explicit, editable files
- The model is a stateless interpreter; the files are the source of truth
- Instructors own and audit their grading logic
- Transparency enables trust, compliance, and continuous improvement

### IP & Differentiation

The defensible IP layers:
1. **Authored artifacts:** Proprietary voice specs, rubric schemas, calibration datasets, exemplar annotations
2. **Orchestration logic:** Retrieval strategies, criterion weighting, rigor ramping, trace generation, refusal rules
3. **Evaluation harness:** Golden sets, regression tests, fairness checks, and tuning loops

---

## System Architecture

### High-Level Pipeline

```
Input: Submission text, assignment metadata (course, week, phase), rubric, outcomes
  ↓
[1] Retrieval: Fetch rubric clauses, outcome snippets, policy rules, exemplar submissions
  ↓
[2] Evidence Extraction: Identify text spans supporting each criterion
  ↓
[3] Criterion Scoring: Apply rubric + course priors + instructor calibration → provisional scores
  ↓
[4] Rigor & Penalty Adjustments: Apply phase-specific rigor profile, late penalties, academic integrity flags
  ↓
[5] Grade Band Generation: Aggregate criteria → grade range + confidence
  ↓
[6] Feedback Synthesis: Generate feedback sentences mapped to criteria/outcomes in instructor voice
  ↓
[7] QA & Trace: Check coverage, citations, safety; produce audit trace
  ↓
Output: Grade band, draft feedback, trace log
  ↓
[8] Calibration Loop: Instructor edits → structured delta capture → update calibration store
```

### Core Components

#### 1. Voice Configuration (`voice_config.yaml`)

Defines instructor-specific grading persona:
- **Tone & style:** Directive vs. coaching, concise vs. detailed, formal vs. conversational
- **Must/never lists:** Required phrases, forbidden phrasing
- **Pedagogical priorities:** Effort vs. correctness, creativity vs. adherence, formatting importance
- **Rubric weight overrides:** Criterion-specific emphasis adjustments
- **Style examples:** Sample feedback snippets demonstrating desired voice

#### 2. Rigor Profile (`rigor_profile.json`)

Encodes week-of-term expectations:
- **Term phases:** Formative (weeks 1–4), transition (5–8), summative (9–12+)
- **Per-phase settings:**
  - Rubric criterion weights (e.g., strict formatting late in term)
  - Grade band width (wider early, narrower late)
  - Feedback style (coaching → concise standards-referencing)
  - Penalty policies (soft → strict for late work, academic integrity)
  - Evidence thresholds (high confidence required for summative grades)

#### 3. Calibration Store

Structured log of instructor edits:
- **Per-criterion deltas:** Suggested vs. final scores/tags per rubric criterion
- **Feedback diffs:** Highlight-level edits aligned to criterion IDs
- **Reason codes:** Why changes were made (missed criterion, tone adjustment, rigor shift, fairness, plagiarism)
- **Phase segmentation:** Separate calibration buckets for early/mid/late term with exponential decay on old signals
- **Outlier detection:** Flag unusual edits for confirmation before absorbing

#### 4. Rubric & Outcome Schema

- **Rubric:** Hierarchical criteria with descriptors, point ranges, evidence requirements
- **Outcomes:** Learning objectives mapped to rubric criteria; used for retrieval and citation
- **Policies:** Late work, academic integrity, resubmission rules; version-controlled

#### 5. Retrieval & Evidence Engine

- Retrieve relevant rubric clauses, outcome snippets, exemplar submissions, and policy rules
- Extract evidence spans from submission text supporting each criterion
- Confidence scoring: Flag low-evidence criteria for human attention
- Citation: Link every judgment to retrieved artifacts

#### 6. Trace & Provenance Log

Per-run audit trail:
- Criterion → retrieved evidence → applied rule/weight → provisional score → adjustments (rigor/penalty) → grade band
- Feedback sentences mapped back to criteria/outcomes
- Confidence scores and uncertainty flags
- Enables debugging, fairness audits, and explainability

---

## Progressive Rigor Modeling

### Problem Statement

Grading expectations shift across the term:
- **Early weeks:** Formative, lenient, coaching-heavy feedback, focus on learning
- **Later weeks:** Summative, strict, standards-driven, concise feedback

The algorithm must adapt dynamically to avoid:
- Overfitting to early leniency or late strictness
- Inconsistency across phases
- Opaque rigor shifts

### Solution: Explicit Phase Metadata

- Assignments tagged with `term_phase` (formative/transition/summative) and `week_number`
- Rigor profile defines phase-specific behavior
- Calibration segmented by phase; cross-phase consistency checks
- Override capability for anomalous assignments (e.g., high-stakes midterm in week 5)

### Implementation Levers

- **Rubric weighting:** Increase formatting/citation weight in summative phase
- **Grade band width:** Narrow bands and raise confidence thresholds late in term
- **Feedback style:** Shift from "Consider X" to "X is required per rubric criterion Y"
- **Penalty application:** Soft warnings early; strict deductions late
- **Calibration decay:** Down-weight old signals; prioritize phase-specific data

---

## Calibration Loop Design

### Underfitting vs. Overfitting

**Underfitting risks:**
- Generic rubric application without instructor-specific weighting or tone
- Missing implicit signals (formatting importance, effort vs. correctness trade-offs)

**Overfitting risks:**
- Learning week-specific quirks (one-off leniency after a tough assignment)
- Absorbing noise from fatigued or inconsistent grading sessions

### Mitigation Strategies

- **Structured edits:** Capture per-criterion adjustments and reason codes, not just final grade/feedback text
- **Regularization:** Blend instructor signals with course-level priors; mixing weight adapts with calibration volume
- **Phase segmentation:** Separate calibration stores per term phase with exponential decay
- **Outlier detection:** Flag edits >2 SD from instructor's historical pattern; require confirmation
- **Cross-validation:** Test consistency on held-out golden sets per phase

### Calibration Data Schema

```yaml
calibration_entry:
  submission_id: "anon-028"
  assignment_id: "ba101_week3_essay"
  term_phase: "formative"
  week_number: 3
  criteria_deltas:
    - criterion_id: "thesis_clarity"
      suggested_score: 3.5
      final_score: 4.0
      reason_code: "tone_adjustment"
      instructor_note: "More encouraging in early weeks"
    - criterion_id: "evidence_quality"
      suggested_score: 4.0
      final_score: 4.0
      reason_code: "accurate"
  feedback_diffs:
    - criterion_id: "thesis_clarity"
      suggested: "Your thesis lacks clarity."
      final: "Your thesis shows promise; consider sharpening X."
      reason_code: "voice_tone"
  overall_grade:
    suggested_band: [85, 90]
    final_grade: 88
  timestamp: "2026-01-15T10:23:00Z"
  phase_weight: 1.0  # Decays over time
```

---

## Student QA Mode

### Design Constraints

- Use same voice/rigor config as grading mode
- Enforce scope: Only syllabus, rubric, outcomes, policies
- Refusals:
  - Grading hypotheticals ("What grade would this get?")
  - Academic integrity violations (writing assignments for students)
  - Off-syllabus content
- Cite syllabus/rubric clauses in every answer
- Modulate tone per phase (more coaching early, more concise late)

### Safety & Guardrails

- Hard blocks on integrity violations
- Uncertainty responses when outside training data
- Logging/audit trail for all student interactions
- Instructor review capability for flagged queries

---

## Evaluation & Quality Assurance

### Golden Sets

Per term phase:
- 5–10 submissions with expected grade bands and exemplar feedback
- 5–10 student QA transcripts with expected answers and refusals

### Metrics

- **Band hit rate:** % of grades falling within predicted band
- **Rubric coverage:** % of criteria cited in feedback
- **Evidence citation rate:** % of judgments linked to submission text
- **Voice fidelity:** Similarity to instructor-authored feedback (style, tone, length)
- **Refusal correctness:** Precision/recall on inappropriate queries
- **Fairness checks:** Grade distribution parity across student cohorts

### Regression Testing

- Same submission → stable band across model versions
- Adjacent-week scenarios → appropriate rigor shift
- Voice config edits → predictable feedback changes

---

## Data Structures Summary

| Artifact | Location | Purpose | Version Control |
|----------|----------|---------|-----------------|
| `voice_config.yaml` | `config/voices/{instructor_id}/` | Instructor voice, tone, must/never lists | Git + semver |
| `rigor_profile.json` | `config/rigor/{course_id}/` | Phase-specific weights, penalties, feedback style | Git + semver |
| `rubric.yaml` | `data/rubrics/{course_id}/` | Rubric criteria, descriptors, point ranges | Git + semver |
| `outcomes.yaml` | `data/outcomes/{course_id}/` | Learning objectives, mappings to criteria | Git + semver |
| `calibration_store/` | `artifacts/calibration/{instructor_id}/` | Instructor edit logs, segmented by phase | Append-only DB + backup |
| `trace_logs/` | `artifacts/traces/{run_id}/` | Audit trails per grading run | Append-only DB |
| `golden_sets/` | `tests/golden/{course_id}/` | Eval datasets per phase | Git |

---

## Implementation Phases

### Phase 0: Schema & Config (MVP)

- Define voice/rigor/rubric/outcome schemas
- Create one example voice config for one instructor/course
- Wire grading pipeline to consume only config + rubric + outcomes (no hidden defaults)
- Instrument logging for inputs/outputs per stage

### Phase 1: Structured Calibration

- Capture per-criterion deltas and reason codes
- Build calibration store with phase segmentation and decay
- Implement regularization (blend with course priors)
- Outlier detection and confirmation prompts

### Phase 2: Progressive Rigor

- Implement phase-aware weighting and banding
- Build rigor profile configs for formative/transition/summative
- Test consistency across adjacent weeks
- Add override capability for anomalous assignments

### Phase 3: Trace & Explainability

- Produce detailed trace logs per run
- Surface traces to instructors (optional)
- Build diff views for voice/rigor config changes → output deltas

### Phase 4: Evaluation Harness

- Build golden sets per phase
- Automate regression testing
- Implement fairness checks
- Create tuning loop (edit config → rerun → score deltas → suggest edits)

### Phase 5: Student QA Mode

- Adapt pipeline for QA queries
- Implement refusal rules and safety guardrails
- Build scope enforcement (syllabus/rubric only)
- Logging and instructor review for flagged queries

### Phase 6: Multi-Instructor/Multi-Course Scaling

- Isolation and no cross-contamination of calibration data
- Voice/rigor versioning and rollback
- PII redaction and data retention policies
- Admin dashboards for quality monitoring

---

## Success Criteria

- **Accuracy:** 85%+ grade band hit rate on golden sets
- **Coverage:** 95%+ rubric criteria cited in feedback
- **Voice fidelity:** 90%+ instructor approval of tone/style (qualitative survey)
- **Consistency:** <5% variance in grade bands for same submission across adjacent weeks (controlling for rigor profile)
- **Safety:** 0 false negatives on academic integrity refusals
- **Auditability:** 100% of grades traceable to evidence + rubric + config

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Overfitting to quirks | Low trust, inconsistency | Phase segmentation, decay, outlier detection |
| Underfitting (too generic) | Low utility, manual override fatigue | Structured calibration, per-criterion signals |
| Config drift/versioning chaos | Debugging nightmares | Semver + Git + mandatory changelog |
| PII leakage in traces | Compliance violation | Redaction, retention limits, access control |
| Student gaming QA mode | Academic integrity issues | Refusal rules, logging, instructor review |
| Scalability bottlenecks | Slow grading, high cost | Retrieval optimization, batch processing, caching |

---

## Future Directions

- **Multi-modal:** Support code, images, video submissions
- **Peer comparison:** Anonymized relative performance feedback
- **Adaptive assignments:** Suggest personalized practice based on grading patterns
- **Instructor collaboration:** Share/fork voice configs, co-calibrate
- **Predictive analytics:** Early warning for at-risk students based on trajectory

---

## References

- [I Am Just a Text File](https://ruben.substack.com/p/i-am-just-a-text-file)
- Internal: `RUBRIC_AS_CODE.md`, `CALIBRATION_REVIEW_TEST_REPORT.md`, `code_review.md`, `ADAPTIVE_ASSESSMENT_INTELLIGENCE_ROADMAP.md`

---

**Document Owner:** ProjectBlackboard Core Team  
**Next Review:** Post Phase 1 implementation
