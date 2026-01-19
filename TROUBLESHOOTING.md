# Troubleshooting

This project depends on:
- A Python virtual environment (.venv)
- Environment variables loaded from .env
- A reachable Postgres database (Supabase)
- Uvicorn + FastAPI startup (lifespan runs DB checks)

When the server fails to start, follow this checklist in order.

> This document is a troubleshooting runbook.
> Only run the commands in the section that matches your current problem.
> Do not run everything top to bottom.


---

## 0) Confirm you are in the repo root

You should see: app/, .env, .venv, requirements.txt.

```bash
pwd
ls


1) Activate the virtual environment

If your prompt does not show (.venv), activate it:

source .venv/bin/activate
which python
python --version

2) Start the server the reliable way

Prefer module invocation so you use the venv’s packages:

python -m uvicorn app.server:app --reload


## Incident log
- 2025-01-13: Supabase project auto-paused, DB host stopped resolving
