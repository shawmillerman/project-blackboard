# Code Review Backlog

## MVP (Blocking)
- [ ] Missing DB schema constraints and migrations to enforce uniqueness and NOT NULLs.
- [ ] Persistent logs or DB audit records may contain raw student submissions / PII without redaction.
- [ ] Ingest pipeline lacks transactional rollback, risking partial-persisted state on failure.
- [ ] LLM output may include hallucinated citations not present in retrieval results.

## Post-MVP
- [ ] Input validation and SQL injection prevention gaps across server and DB layers.
- [ ] Secrets management and environment hardening (env validation, no secret leakage).
- [ ] Authentication, authorization, and rate limiting missing or insufficient on critical endpoints.
- [ ] Prompt injection and LLM safety controls insufficient for untrusted user inputs.
- [ ] File upload security and data validation for CSV/PDF/plain text.

## Hardening
- [ ] Inconsistent normalization before embedding that can break deduplication and retrieval relevance.

## Scale
- [ ]

## Nice-to-Have
- [ ]



