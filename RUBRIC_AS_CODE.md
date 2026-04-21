# Rubric as Code: Fairness and Consistency in AI-Assisted Assessment

> **Note:** This document describes the foundational philosophy of ProjectBlackboard. For the full implementation architecture of our calibration and voice-learning system, see the **[Adaptive Assessment Intelligence (AAI)](ADAPTIVE_ASSESSMENT_INTELLIGENCE_ROADMAP.md)** initiative.

---

## The Problem We Solve

Traditional AI grading tools are black boxes. Instructors cannot audit how an algorithm decides a student deserves a C instead of a B. Students don't understand why they got their grade. Worst of all, grading becomes inconsistent across time—the same work might receive different feedback depending on the day, the instructor's mood, or the order submissions are processed.

Grading is the highest-stakes communication in education. It shapes student self-concept, academic trajectory, and opportunity. **Equity demands that grading be fair, transparent, and auditable.**

## The Solution: Rubric as Code

**Project Blackboard** expresses pedagogical rigor directly in executable code. Instead of describing rubrics in prose, we encode them as:
- Deterministic scoring rules
- Version-controlled criteria
- Auditable AI reasoning
- Instructor-validated calibration

By making the rubric *code*, we ensure every student—regardless of submission timing, format, or AI model version—receives grading that is:

| Principle | What It Means |
|-----------|---------------|
| **Transparent** | What you see is what you get. Every citation, every score range, every deduction is traceable. |
| **Consistent** | Same criteria applied to all students, all week, all semester. No hidden AI drift. |
| **Auditable** | Every grading decision is logged with metadata. Instructors can review trends; students can request explanations. |
| **Human-Centered** | AI assists with draft grades and feedback. Instructors remain the decision-makers. |
| **Pedagogically Grounded** | Grading references actual course materials, not generic algorithms. Feedback is specific and actionable. |

---

## Core Systems & Design Decisions

### 1. **Rubric-as-Code Architecture**

**What it does:**
- Rubric criteria are stored with semantic embeddings, enabling AI to match student work to rubric intent
- Scoring logic (e.g., "paragraph count < 3 → downgrade Adherence") is implemented as deterministic code
- Every rubric change is version-controlled and tracked

**Why it matters:**
- Rubrics are usually static PDFs that collect dust. Encoding them as code forces precision and ensures they're actually applied.
- Version control provides an audit trail: "On Jan 15, we changed the Content criteria. Here's why."
- Deterministic rules prevent AI from making arbitrary distinctions (e.g., "This is B+ material" vs. "This is A- material" with no principled difference).

**Example in code:**
```python
# If submission has fewer than 3 paragraphs, downgrade Adherence
if paragraph_count < 3:
    adherence_score = 11.25  # Needs Improvement instead of Meets Expectations
    adjustments.append(f"adherence_downgraded_paragraphs:{paragraph_count}")
```

---

### 2. **Component-Level Scoring**

**What it does:**
- Instead of a single opaque number (e.g., "85/100"), students see three dimensions:
  - **Adherence to Directions** (15 points): Did you follow the assignment brief?
  - **Content Quality** (15 points): Is your answer substantive and well-reasoned?
  - **Style Guide Compliance** (10 points): Is your writing clear, organized, and professional?
- Total: 40 points

**Why it matters:**
- Students understand *exactly* where they succeeded and where to improve
- Instructors can calibrate differently per component (e.g., "For this assignment, I prioritize Content; Style is secondary")
- AI generates component-specific feedback tied to each dimension

**Example from a real submission:**
```
Directions: 15/15 (Meets Expectations)
→ "You clearly addressed all three prompts and structured your response logically."

Content: 11.25/15 (Needs Improvement)
→ "You identified the factors correctly but didn't explain how they interact or reference the textbook."

Style: 10/10 (Meets Expectations)
→ "Your writing is clear and professional; good use of transitions."

Total: 36.25/40
```

---

### 3. **Calibration Bank: Instructor-Controlled Exemplars**

**What it does:**
- As you grade, you flag submissions as exemplars (e.g., "This is a strong example of meeting expectations for Content Quality")
- These exemplars are stored with your actual grades and feedback
- Future AI grading uses these exemplars to calibrate its suggestions
- Week-specific calibration for course-relevant examples; fallback to course-level if needed

**Why it matters:**
- AI grading is only as good as its training ground. Generic models don't know *your* standards.
- By providing instructor-validated examples, we create a feedback loop: Better calibration → Better AI suggestions → Fairer grades
- Instructors maintain full control; no "black box" algorithms deciding what counts as good work

**Workflow:**
1. Grade submission → Enter your actual score and feedback
2. Decide: "Flag as calibration example?" → Yes/No
3. If yes, your feedback becomes part of the calibration bank
4. Next week, when AI grades similar submissions, it references *your* examples, not generic ones

---

### 4. **Feedback Traceability: Citations and Source Attribution**

**What it does:**
- Every piece of AI-generated feedback includes citations to its sources:
  - `[R1]` = Rubric chunk (e.g., "Content Quality criteria from Week 1 rubric")
  - `[F2]` = Feedback library (e.g., "Encouraging feedback for missing examples")
  - `[C2]` = Calibration exemplar (e.g., "Similar to the submission you graded last week")

**Why it matters:**
- Students can see the reasoning: "Oh, this feedback comes from the Content rubric, not just the AI's opinion."
- Instructors can audit: "Did the AI use the right calibration examples?"
- Promotes trust through transparency

**Example:**
```
Suggested Feedback:
"You identified the key factors correctly [R1], which shows good grasp of the concepts. 
To strengthen your response, please explain where you would source each factor [F2], 
similar to the exemplar [C2] that scored well on this dimension."
```

---

### 5. **Structural Determinism: Rules Over Heuristics**

**What it does:**
- Grading rules are explicit and logged:
  - "Paragraph count < 3 → Apply Adherence downgrade"
  - "Word count < 30 → Flag for manual review"
  - "Extraction confidence < 0.8 → Quality gate: NEEDS_REVIEW"

**Why it matters:**
- No hidden AI "gut feelings." All decisions are explainable.
- Instructors can debate and refine the rules (e.g., "Should paragraph count threshold be 2 or 3?")
- Makes it easy to identify systematic biases (e.g., "PDF submissions consistently score lower than DOCX")

**Logged Example:**
```json
"structural_adjustments": ["adherence_downgraded_paragraphs:2"],
"quality_status": "OK_FOR_GRADING",
"quality_reasons": []
```

---

### 6. **Student Voice Preservation: Extracting Authentic Responses**

**What it does:**
- Submission files are processed to remove boilerplate (assignment instructions, headers, etc.)
- Authentic student response text is preserved
- Paragraph breaks and structure are maintained (especially in DOCX tables)
- Cleaned text is stored separately for traceability

**Why it matters:**
- AI grades the *student's actual answer*, not the assignment prompt
- Prevents AI from being confused by instructions mixed into the response
- Students see their authentic work used in calibration, not a mangled version

**Example of cleanup:**
```
Before:
"Week 1 Business Activity: Factors in Producing a Surfboard
Use the information from Chapter 1...
[10 lines of instructions]
Land and natural resources provide..."

After:
"Land and natural resources provide...
[actual student response, paragraphs preserved]"
```

---

### 7. **Extraction Quality Gates: Preventing Garbage-In, Garbage-Out**

**What it does:**
- Before grading, submissions are evaluated:
  - Word count threshold (min 30 words)
  - Retention ratio (min 15% of text survives boilerplate removal)
  - Extraction warnings (e.g., "header/footer detected")
- Submissions with issues are flagged as `NEEDS_REVIEW` instead of auto-graded

**Why it matters:**
- Corrupted PDFs, OCR failures, or empty submissions are caught *before* grading
- Instructor can manually review questionable cases
- Maintains data integrity: Bad data in → Can't produce fair grades

**Example gate:**
```python
if word_count < 30:
    reasons.append("low_word_count:15")  # Flagged for review
    return "NEEDS_REVIEW", reasons
```

---

### 8. **Audit Trail & Grading Traces: Complete Provenance**

**What it does:**
- Every grading decision is logged in the database with metadata:
  - Request ID (unique identifier)
  - Submission text and AI feedback
  - Timestamp and duration
  - Rubric ID and assignment context
  - Which calibration examples were used

**Why it matters:**
- Instructors can analyze trends: "Did I grade harder on Fridays?" (Accountability)
- Students can request transparency: "Show me how my grade was generated" (Trust)
- Disputes can be resolved with evidence: "Here's the exact rubric and examples used"

**Stored data includes:**
```json
{
  "request_id": "12ded3f5-90a2-4e21-8956-37bd57d4812f",
  "assignment_id": "ba101_week_1",
  "rubric_id": "ba101_week1_v2",
  "course": "BA101",
  "timestamp": "2026-01-19T14:17:23",
  "citations": [
    {"cite": "R1", "source": "rubric", "distance": 0.65},
    {"cite": "C2", "source": "calibration", "distance": 0.76}
  ]
}
```

---

### 9. **Instructor Review Loop: AI as Assistant, Not Authority**

**What it does:**
- Workflow: AI generates draft grade → Instructor reviews and adjusts → Flagged submissions feed back into calibration
- Interactive review session: See AI output, enter actual grade, provide feedback
- Flagged submissions automatically ingested into calibration bank

**Why it matters:**
- AI speeds up grading without replacing instructor judgment
- Creates virtuous cycle: Better instructor feedback → Better calibration → Better AI suggestions
- Maintains human agency and responsibility

**Workflow:**
```
1. AI generates: Score range 21-40, suggested feedback
2. Instructor grades: "Actually, this is 36.25/40"
3. Instructor reviews: "Yes, flag this for calibration"
4. System ingests: Example added to calibration bank for future grading
```

---

### 10. **Dry-Run & Testing Capability: De-Risk Before Commit**

**What it does:**
- Instructors can run batch extraction and grading in "dry-run" mode
- Validates extraction and grading logic without actually storing grades
- Allows inspection of results before final commit

**Why it matters:**
- Reduces risk of systematic errors affecting all students
- Catches configuration issues early
- Builds confidence before going live

**Command:**
```bash
python scripts/grade_batch.py input_dir \
  --batch-id ba101_test \
  --dry-run  # No grades saved
```

---

### 11. **Auto-Resume Capability: Session State Preservation**

**What it does:**
- Grading sessions save state after each submission
- If interrupted (Ctrl+C), session automatically resumes from last completed submission
- No loss of progress; just redo the interrupted submission

**Why it matters:**
- Reduces cognitive load (no need to track which submission you're on)
- Prevents session-to-session inconsistency from instructor fatigue
- Makes long grading sessions more sustainable

---

### 12. **Course-Material Grounding: Pedagogy-First AI**

**What it does:**
- Feedback library tied to actual course concepts (e.g., Chapter 1 content)
- AI references textbook chapters and course themes, not generic advice
- Rubric explicitly defines course standards

**Why it matters:**
- Feedback is coherent with course design
- Students see that AI understands the domain
- Prevents "one-size-fits-all" feedback that doesn't fit your course

**Example:**
```
AI Feedback:
"You identified the factors correctly [R1: Week 1 rubric], 
which demonstrates understanding of Chapter 1. To improve, 
explain how these factors work together, as discussed in 
Section 1.3 of the textbook."
```

---

### 13. **Syllabus-as-Code: Learning Outcomes Alignment**

**What it does:**
- Encodes course learning outcomes (LOs) as structured data and rules
- Aligns grading and feedback to specific LOs per week/assignment
- Produces an LO-alignment report alongside grades (e.g., which outcomes were demonstrated)

**Why it matters:**
- Makes assessment explicitly tied to what the course promises students will learn
- Improves fairness by applying the same LO criteria to all students
- Helps students reflect on progress: not just a grade, but which outcomes they’ve advanced

**Data model (example):**
```json
{
  "course_id": "BA101",
  "version": "2026.01",
  "learning_outcomes": [
    {
      "id": "LO1",
      "title": "Identify factors of production",
      "weeks": [1],
      "signals": {
        "keywords_any": ["land", "labor", "capital", "entrepreneurship"],
        "rubric_components": {"content": 0.6, "directions": 0.3, "style": 0.1}
      },
      "success_criteria": [
        "Names all four factors",
        "Explains how they interact in a business context"
      ]
    },
    {
      "id": "LO2",
      "title": "Apply course materials to reasoning",
      "weeks": [1],
      "signals": {
        "requires_reference": true,
        "keywords_any": ["Chapter 1", "textbook", "section"],
        "rubric_components": {"content": 0.7, "directions": 0.2, "style": 0.1}
      },
      "success_criteria": [
        "References textbook concepts correctly",
        "Connects concepts to the assignment prompt"
      ]
    }
  ]
}
```

**How it plugs into grading:**
- Pre-load syllabus config for the course/week
- During grading, evaluate LO signals (keywords, references, rubric component coverage)
- Generate an LO-alignment summary per submission, e.g.,
  - "LO1: met (strong), LO2: partially met (no explicit textbook reference)"
- Optionally adjust component feedback emphasis: if LO2 requires references and none are detected, prompt a deduction to 11.25 in Content

**Instructor experience:**
- See component scores AND LO alignment in the review UI
- Calibration examples store LO tags for better future guidance
- Students receive feedback that names the outcomes they demonstrated or missed

**Minimal implementation plan:**
1) Define `docs/syllabus_ba101.json` with LOs, signals, weeks
2) Load syllabus in `app/config.py` and pass into `suggest_feedback()`
3) Compute LO alignment in `app/grading.py` (simple keyword/reference checks)
4) Return `learning_outcomes_alignment` in API response; persist in grading trace
5) Surface alignment in the calibration review display

Effort: MVP 2–4 hours; full alignment scoring with embeddings and citation verification 1–2 days.


## Design Principles

### **Transparency Over Opacity**
- Show reasoning, not just scores
- Citations to sources
- Auditable logs

### **Consistency Over Convenience**
- Same criteria for all students
- Deterministic rules, not AI judgment calls
- Version-controlled rubrics

### **Pedagogy Over Automation**
- Course-specific calibration, not generic models
- Instructor-validated exemplars
- Feedback tied to learning objectives

### **Human Agency Over Algorithmic Authority**
- AI assists; instructors decide
- Flagging system for calibration control
- Manual review option for edge cases

---

## Business Value Propositions

### **For School Administrators**
- **Defensibility:** Every grade decision is traceable and auditable. Supports accreditation reviews and fairness audits.
- **Compliance:** Documentation demonstrates equitable assessment practices. Reduces liability for grade disputes.
- **Scalability:** Handles 100+ submissions/week while maintaining rigor. Reduces instructor workload by 60-70%.

### **For Instructors**
- **Consistency:** "I know I'm grading the same way every time." Confidence that bias is minimized.
- **Efficiency:** Draft feedback generated automatically. Instructor reviews and customizes, not starting from scratch.
- **Control:** AI assists, but you remain the decision-maker. No algorithmic black box taking away your authority.

### **For Students**
- **Transparency:** "I understand exactly why I got this grade." Reduces anxiety and disputes.
- **Fairness:** "I know everyone is graded by the same standards." Promotes trust in assessment.
- **Actionability:** Component feedback shows exactly what to improve. Next assignment, I'll focus on Content Quality.

### **For EdTech Vendors & Researchers**
- **Pedagogically Grounded:** Not a shortcut algorithm, but a principled system grounded in educational research.
- **Auditable & Interpretable:** Meets regulatory requirements for transparency in AI/education.
- **Human-Centered Design:** Demonstrates thoughtful integration of AI as a tool, not a replacement.

---

## Future Work & Roadmap

### **Phase 2: Multi-Rubric Support**
- Support assignments with different component structures (e.g., 2 components vs. 3)
- Rubric versioning: Track changes over time, re-grade with old rubric if needed

### **Phase 3: Student Self-Assessment Integration**
- Students provide self-grades before instructor review
- Compare self-assessment to AI assessment to identify misconceptions
- Feedback loop: "You thought you did well on Content, but the rubric emphasizes explanation depth"

### **Phase 4: Cross-Course Calibration**
- Share anonymized calibration exemplars across instructors/sections
- Learn: "What does 'meets expectations' mean across BA101 sections?"
- Promote consistency at course-level

### **Phase 5: Predictive Analytics**
- Identify students at risk of low performance early
- Tailor feedback to address specific misconceptions
- Early intervention based on pattern recognition

### **Phase 6: Accessible Assessment**
### **Phase 7: Syllabus-as-Code (Production)**
- Store syllabus LOs per course/week with versioning
- Add LO alignment scoring with embeddings and explicit citation checks
- Include LO tags in calibration examples and analytics dashboards

- Multi-language support for international students
- Accessible PDF/document parsing for diverse submission formats
- Rubric customization for courses with different accessibility needs

---

## Conclusion

**Rubric as Code** is a commitment to fairness in assessment. By encoding pedagogical principles directly into executable systems, we make grading transparent, consistent, and auditable. Students know how they'll be graded. Instructors control the standards. AI assists with speed and consistency, but never replaces human judgment.

The result: Assessment that is fair, defensible, and educationally sound.

---

## References & Further Reading

- Wiggins, G., & McTighe, J. (2005). *Understanding by Design* — The importance of rubrics grounded in learning objectives
- Brookfield, S. D., & Preskill, S. (2005). *Discussion as a Way of Teaching* — Transparency in assessment builds trust
- Anson, C. M., & Schwegler, R. A. (2010). *Longman Handbook for Writers and Readers* — Specificity in grading feedback
- AI in Education Research: [Refer to relevant papers on AI fairness, algorithmic transparency, and learning assessment]

---

**Document Version:** 1.0  
**Last Updated:** January 21, 2026  
**Status:** Active Design Document
