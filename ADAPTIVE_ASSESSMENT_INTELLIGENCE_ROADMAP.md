# Adaptive Assessment Intelligence — Implementation Roadmap

**Version:** 1.0  
**Date:** January 21, 2026  
**Status:** Active Priority Initiative

---

## Overview

This roadmap tracks the phased implementation of the **Adaptive Assessment Intelligence (AAI)** system—the core IP and algorithmic foundation of ProjectBlackboard. See [docs/ADAPTIVE_ASSESSMENT_INTELLIGENCE_ARCHITECTURE.md](docs/ADAPTIVE_ASSESSMENT_INTELLIGENCE_ARCHITECTURE.md) for full architectural specification.

**Goal:** Build a defensible, explainable, and scalable grading system that learns instructor voice, adapts to term-phase expectations, and powers both grading workflows and student QA interactions.

---

## Current State Assessment

### What Exists Today

- Basic grading pipeline in [app/grading.py](app/grading.py)
- Calibration review scripts in [scripts/calibration_review.py](scripts/calibration_review.py) and [scripts/test_calibration_review.py](scripts/test_calibration_review.py)
- Rubric ingestion and retrieval infrastructure ([app/ingest.py](app/ingest.py), [app/retrieval.py](app/retrieval.py))
- Draft feedback generation (LLM-based)
- Ad-hoc calibration tracking (not formalized)

### Gaps

- No structured voice/rigor config files
- Calibration signals are coarse (final grade only, not per-criterion)
- No week-of-term or phase-aware rigor modeling
- Limited traceability (no evidence → judgment → feedback mapping)
- No evaluation harness or golden sets
- No student QA mode
- No multi-instructor/multi-course isolation or versioning

---

## Phase 0: Schema & Config Foundation (MVP)

**Timeline:** 2 weeks  
**Goal:** Establish the "text file as source of truth" foundation.

### Tasks

- [ ] **Define schemas** (YAML/JSON):
  - `voice_config.yaml`: Tone, must/never, pedagogical priorities, style examples
  - `rigor_profile.json`: Per-phase weights, band widths, feedback styles, penalty policies
  - `rubric.yaml`: Hierarchical criteria, descriptors, point ranges
  - `outcomes.yaml`: Learning objectives mapped to rubric criteria
- [ ] **Create one example config set** for BA101 / one instructor
- [ ] **Refactor [app/grading.py](app/grading.py)** to consume only config files (no hardcoded defaults)
- [ ] **Instrument logging**: Capture inputs/outputs for each pipeline stage
- [ ] **Manual test**: Run grading pipeline on 5 submissions with config-only mode

### Success Criteria

- Grading pipeline reads all behavior from config files
- One complete config set for BA101
- Stage-level logs for debugging

### Dependencies

None

---

## Phase 1: Structured Calibration Loop

**Timeline:** 3 weeks  
**Goal:** Capture rich calibration signals per criterion and reason code.

### Tasks

- [ ] **Design calibration data schema** (per-criterion deltas, reason codes, feedback diffs)
- [ ] **Build calibration capture UI/workflow**:
  - Instructor sees draft grade/feedback
  - Can edit per-criterion scores and feedback text
  - Selects reason codes (missed criterion, tone, rigor, fairness, etc.)
- [ ] **Implement calibration store** (SQLite or JSONL append-only)
- [ ] **Add phase segmentation**: Tag entries with term phase (formative/transition/summative)
- [ ] **Implement exponential decay** on old calibration signals
- [ ] **Regularization**: Blend instructor calibration with course-level priors (mixing weight adapts with data volume)
- [ ] **Outlier detection**: Flag edits >2 SD from instructor's pattern; require confirmation
- [ ] **Test calibration loop** on 20 submissions across multiple weeks

### Success Criteria

- Calibration store captures per-criterion deltas and reason codes
- Decay and regularization reduce overfitting (qualitative assessment)
- Outliers flagged correctly (manual review)

### Dependencies

Phase 0 complete

---

## Phase 2: Progressive Rigor (Week-of-Term Modeling)

**Timeline:** 3 weeks  
**Goal:** Adapt grading strictness and feedback style across term phases.

### Tasks

- [ ] **Extend assignment metadata** with `term_phase` and `week_number`
- [ ] **Build rigor profile configs** for formative/transition/summative phases:
  - Criterion weight adjustments (e.g., formatting strictness increases)
  - Grade band width narrowing over time
  - Feedback style shifts (coaching → concise standards)
  - Penalty policy escalation (soft → strict)
- [ ] **Refactor grading pipeline** to apply phase-specific rules
- [ ] **Test rigor consistency**:
  - Same submission graded in week 2 vs. week 10 with phase-appropriate configs
  - Verify predictable grade/feedback shifts
- [ ] **Build override mechanism** for anomalous assignments (e.g., midterm in week 5)
- [ ] **Cross-phase calibration checks**: Ensure instructor calibration doesn't bleed across phases

### Success Criteria

- Grading outputs shift predictably across phases (qualitative review)
- <5% variance in grade bands for same submission when phase config is fixed
- Override mechanism works for edge cases

### Dependencies

Phase 1 complete

---

## Phase 3: Trace & Explainability

**Timeline:** 2 weeks  
**Goal:** Produce audit-trail traces linking evidence → judgment → feedback.

### Tasks

- [ ] **Design trace schema** (criterion → evidence spans → retrieved rules → score → adjustments → feedback sentence)
- [ ] **Instrument pipeline** to emit trace logs per run
- [ ] **Build trace viewer** (web UI or JSON export for instructors)
- [ ] **Evidence extraction**: Highlight submission text spans supporting each criterion
- [ ] **Confidence scoring**: Flag low-evidence criteria for human review
- [ ] **Test traces** on 10 submissions; verify completeness and correctness

### Success Criteria

- 100% of criteria have evidence → judgment → feedback mapping in traces
- Instructors can view and understand traces (usability test)
- Low-evidence flags reduce false-confidence grades

### Dependencies

Phase 2 complete

---

## Phase 4: Evaluation Harness

**Timeline:** 3 weeks  
**Goal:** Build automated quality assurance and regression testing.

### Tasks

- [ ] **Create golden sets** per phase (formative/transition/summative):
  - 5–10 submissions per phase with instructor-approved grade bands and feedback
  - 5–10 student QA transcripts with expected answers/refusals
- [ ] **Implement metrics**:
  - Band hit rate (% grades in predicted band)
  - Rubric coverage (% criteria cited)
  - Evidence citation rate
  - Voice fidelity (TBD: automated or survey-based)
  - Refusal correctness (precision/recall)
- [ ] **Build regression test suite**:
  - Same submission → stable band across runs
  - Adjacent-week scenarios → appropriate rigor shift
  - Config edits → predictable output deltas
- [ ] **Fairness checks**: Grade distribution parity across student cohorts (demographic data permitting)
- [ ] **Automate tests** in CI pipeline

### Success Criteria

- 85%+ band hit rate on golden sets
- 95%+ rubric coverage
- 0 false negatives on academic integrity refusals
- Regression tests pass on every commit

### Dependencies

Phase 3 complete (traces enable debugging failures)

---

## Phase 5: Student QA Mode

**Timeline:** 3 weeks  
**Goal:** Enable students to query syllabus/rubric/outcomes in instructor's voice.

### Tasks

- [ ] **Adapt grading pipeline** for QA queries (no scoring, just answer generation)
- [ ] **Implement refusal rules**:
  - Decline grading hypotheticals
  - Refuse academic integrity violations (writing assignments)
  - Reject off-syllabus questions
- [ ] **Scope enforcement**: Only syllabus, rubric, outcomes, policies
- [ ] **Voice/rigor integration**: Use same configs as grading mode; modulate tone per phase
- [ ] **Citation requirement**: Link every answer to syllabus/rubric clause
- [ ] **Logging & audit**: Store all student queries; flag anomalies for instructor review
- [ ] **Build student-facing UI** (chat interface)
- [ ] **Test with 50 student queries** (mix of in-scope, out-of-scope, adversarial)

### Success Criteria

- 100% refusal precision on academic integrity violations
- 95%+ in-scope questions answered correctly (per golden set)
- Tone consistency with instructor grading feedback (qualitative)

### Dependencies

Phase 4 complete (golden QA sets)

---

## Phase 6: Multi-Instructor/Multi-Course Scaling

**Timeline:** 4 weeks  
**Goal:** Prepare for production deployment with multiple instructors and courses.

### Tasks

- [ ] **Isolation architecture**: Ensure no calibration cross-contamination between instructors/courses
- [ ] **Config versioning**: Semver + Git + mandatory changelogs for voice/rigor/rubric files
- [ ] **Rollback capability**: Revert to prior config versions; re-run grading
- [ ] **PII redaction**: Anonymize student names/IDs in traces and calibration logs
- [ ] **Data retention policies**: Auto-purge old traces per institutional rules
- [ ] **Access control**: Role-based permissions (instructor, admin, auditor)
- [ ] **Admin dashboard**: Monitor grade distributions, calibration volume, refusal rates, fairness metrics
- [ ] **Performance optimization**: Batch processing, retrieval caching, vector index tuning
- [ ] **Load testing**: 1000 submissions/hour target
- [ ] **Documentation**: Instructor onboarding guide, config editing tutorials

### Success Criteria

- 5+ instructors/courses running simultaneously with no cross-contamination
- <10s latency per grading run (p95)
- 1000 submissions/hour throughput
- Instructor satisfaction survey >4/5 on config usability

### Dependencies

Phases 1–5 complete

---

## Phase 7: Advanced Features (Future)

**Not scheduled; prioritize after Phase 6 complete**

- Multi-modal submissions (code, images, video)
- Peer comparison feedback (anonymized relative performance)
- Adaptive assignments (personalized practice suggestions)
- Instructor collaboration (share/fork voice configs, co-calibrate)
- Predictive analytics (early warning for at-risk students)

---

## Milestones & Timeline Summary

| Phase | Duration | Completion Target |
|-------|----------|-------------------|
| Phase 0: Schema & Config | 2 weeks | Week of Feb 3, 2026 |
| Phase 1: Calibration Loop | 3 weeks | Week of Feb 24, 2026 |
| Phase 2: Progressive Rigor | 3 weeks | Week of Mar 17, 2026 |
| Phase 3: Trace & Explainability | 2 weeks | Week of Mar 31, 2026 |
| Phase 4: Evaluation Harness | 3 weeks | Week of Apr 21, 2026 |
| Phase 5: Student QA Mode | 3 weeks | Week of May 12, 2026 |
| Phase 6: Multi-Instructor Scaling | 4 weeks | Week of Jun 9, 2026 |

**Total: ~20 weeks to production-ready AAI system**

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| Overfitting to instructor quirks | Medium | High | Phase segmentation, decay, outlier detection | TBD |
| Config schema changes break existing data | High | Medium | Versioning, migration scripts, backward compat tests | TBD |
| Student gaming QA mode | Medium | High | Refusal rules, logging, instructor review queue | TBD |
| Scalability bottlenecks at Phase 6 | Medium | High | Early load testing, caching, batch optimization | TBD |
| PII leakage in traces | Low | Critical | Redaction, access control, audit | TBD |
| Instructor adoption resistance (config editing too complex) | Medium | High | Intuitive UI, templates, onboarding support | TBD |

---

## Dependencies & Blockers

- **External:** None currently
- **Internal:** Phase N+1 requires Phase N completion (sequential dependencies)
- **Resource:** Requires 1 FTE engineer + part-time ML/NLP consultation for Phases 4–5

---

## Success Metrics (End-of-Phase-6)

- **Accuracy:** 85%+ grade band hit rate on golden sets across all phases
- **Coverage:** 95%+ rubric criteria cited in feedback
- **Voice fidelity:** 90%+ instructor approval (survey)
- **Consistency:** <5% grade variance for identical submissions across adjacent weeks
- **Safety:** 0 false negatives on academic integrity refusals
- **Auditability:** 100% grades traceable to evidence + rubric + config
- **Scale:** 5+ instructors/courses, 1000 submissions/hour
- **Satisfaction:** Instructor NPS >50

---

## Communication & Governance

- **Weekly standups:** Progress check, blocker resolution
- **End-of-phase demos:** Stakeholder review, sign-off to proceed
- **Monthly strategic reviews:** Roadmap adjustments, prioritization
- **Documentation updates:** Keep architecture doc in sync with implementation reality

---

## Links & References

- **Architecture:** [docs/ADAPTIVE_ASSESSMENT_INTELLIGENCE_ARCHITECTURE.md](docs/ADAPTIVE_ASSESSMENT_INTELLIGENCE_ARCHITECTURE.md)
- **Related Docs:**
  - [RUBRIC_AS_CODE.md](RUBRIC_AS_CODE.md)
  - [CALIBRATION_REVIEW_TEST_REPORT.md](CALIBRATION_REVIEW_TEST_REPORT.md)
  - [code_review.md](code_review.md)
  - [project_states/PROJECT_STATE_FOR_CHATGPT.md](project_states/PROJECT_STATE_FOR_CHATGPT.md)

---

**Roadmap Owner:** ProjectBlackboard Core Team  
**Next Review:** End of Phase 0 (Week of Feb 3, 2026)
