# Code Review Charter and Playbook

This section defines the repeatable process, constraints, and prompts used for reviewing this codebase. Findings and decisions are documented below.


0) Prep rules (30 seconds)
Goal: keep Copilot from rewriting your app.
Prompt #1:
“You are my senior reviewer. Constraints: minimize diff, preserve behavior, prefer small PR-sized changes, avoid refactors unless they reduce risk, propose exact file edits, and call out tradeoffs.”
1) Repo orientation and request flow map (5 minutes)
Prompt #2:
“Map the architecture of this repo. Identify entrypoints, request flow from input to response, key modules, external services, data stores, and configuration sources. Reference filenames. End with 10 clarifying questions about what you still cannot infer.”
Output you want:
a bullet “flow” of the app
a shortlist of “core files”
unknowns called out


2) Risk register, ranked (the real value)
Prompt #3:
“Create a risk register ranked by severity: Security, Correctness, Reliability, Performance/Cost, Maintainability. For each risk: describe impact, likely cause, and the smallest safe remediation. Reference specific files.”
This becomes your backlog.
3) Structured deep dives (run in this order)
You now review by category, not by file.
3A) Security and secrets
Prompt #4:
“Security review. Focus on: secrets management, logging of sensitive data, auth and access control, injection risks, unsafe defaults, dependency risk. Give findings ranked by severity and show minimal patches.”
3B) Correctness and data integrity
Prompt #5:
“Correctness review. Trace a request end-to-end and identify schema mismatches, inconsistent keys, unchecked None values, silent exception handling, and brittle parsing. Show minimal patches.”
3C) Reliability and error handling
Prompt #6:
“Reliability review. Identify failure modes: network timeouts, retry needs, DB connection lifecycle, rate limits, error responses, and observability gaps. Propose a consistent error-handling approach with minimal diffs.”
3D) Performance and cost
Prompt #7:
“Performance/cost review. Identify unnecessary repeated calls, opportunities for caching, batching, and payload reduction. Prioritize the changes with the best ROI.”
3E) Maintainability
Prompt #8:
“Maintainability review. Identify duplication, poor boundaries, confusing naming, dead code, missing typing, and config sprawl. Propose a 3-step refactor plan that is safe and optional.”
4) Patch plan as PR-sized chunks (this is how you ship)
Prompt #9:
“Convert the risk register into a patch plan of small PRs. For each PR: goal, files touched, exact change list, and test plan. Keep each PR under ~200 lines if possible.”
Now you have a buildable roadmap.
5) Verification loop (don’t skip this)
For each PR chunk you apply:
Prompt “n”:
“Given these changes, what could break? Suggest a quick manual test plan and any unit tests worth adding.”

Micro-script for reviewing a single file 
When you open a file like app/qa.py:
“Review this file. List the top 5 risks and top 5 quick wins. Then propose minimal diffs, explain why each change matters, and what to test.”
If you highlight a block of code:
“Explain what this code does, identify edge cases and failure modes, and propose the smallest safe improvement.”


# MVP Definition

# Review Summary (High-Level)

# MVP Patch List (Approved)

# Decisions & Tradeoffs

# PR Execution Log
