# Innovation Lab

A living document for moonshot ideas, future features, and strategic directions for our AI-native learning platform.

---

## 1. AI-Driven Student Profiles

**Vision:**
Persistent student profiles aggregate scores, effort, and engagement across all subjects, flagging students who are strong candidates for targeted writing support. Profiles enable:
- Cross-class and cross-grade progress tracking
- Custom feedback and interventions
- Calibration banks for nuanced grading

**Strategic Impact:**
- Enables proactive, individualized support at scale
- Not present in Canvas/Brightspace; requires AI-native architecture
- Supports longitudinal growth and actionable insights

---

## 2. Push Notification Nudges for Instructors

**Feature:**
- AI suggests messages to instructors based on student activity (e.g., login frequency, assignment completion)
- Escalating urgency: encouraging nudge → warning → critical alert
- Group notifications for policy changes
- Teachers can edit and send, preserving a human touch

**Example Messages:**
- "Great start to the quarter. I noticed you hadn't logged in for awhile. It's not too late to get caught up. You got this!"
- "You are not able to turn in a week's worth of homework in the last week of class."
- "I'm no longer taking late assignments for weeks 1-3. If you're missing any, be sure you are completing enough to still get the high score you deserve."

---

## 3. Cross-Class/Grade Progress Tracking

**Feature:**
- Use unique student identifiers to link writing samples and reports across classes and grades
- Enable cross-sharing of student data between teachers and grade levels
- Visualize progress from one grade/class to another

**Strategic Impact:**
- Provides a holistic view of student growth
- Not available in current LMS platforms

---

## 4. Smart Session Management for Accurate Activity Logs

**Problem:**
Current LLM and LMS reporting tools often overstate student activity due to lack of accurate session tracking.

**Solution:**
- Implement auto-logout after a set period of inactivity to ensure accurate time-on-task reporting
- Design session logic to minimize user friction:
  - Short inactivity (e.g., 15 minutes): auto-logout, but allow quick re-entry without 2FA
  - Longer inactivity (e.g., 1 hour): require full re-authentication (e.g., 2FA)
- Focus on seamless return-to-workflow, so students can resume where they left off without unnecessary barriers

**Development Focus:**
- Map out detailed session workflows
- Balance security, accuracy, and user experience
- Make this a core focus for the dev team

---

## 5. Additional AI-First Feature Ideas

- Early warning system for at-risk students
- Adaptive learning paths based on profile insights
- Peer matching for collaborative improvement
- Automated goal setting and progress nudges
- Dynamic rubric generation based on student needs

---

**This document is a living space for high-impact, AI-native features that set us apart from legacy LMS platforms.**
