---
name: mrs-server-dev
description: Work on the MRS server (FastAPI + SQLite): API changes, auth/validation, search behavior, tests, and release-readiness checks. Use when modifying server endpoints, contracts, or server-side security policy.
---

# MRS Server Dev Skill

## Use this workflow
1. Activate env: `source .venv/bin/activate`
2. Run tests first: `pytest -q`
3. Make focused change
4. Re-run tests
5. Verify local server behavior with curl for changed endpoint

## Project specifics
- Stack: FastAPI, Pydantic v2, SQLite
- Entry point: `python -m mrs_server.main`
- DB init: `python scripts/init_db.py`
- Key contracts: `/register`, `/release`, `/search`, `/.well-known/mrs`

## Security-critical rules
- Treat `service_point` as untrusted input.
- Keep strict URI validation in sync with client policy.
- Never weaken auth/ownership checks without explicit rationale + tests.

## Required checks before shipping
- `pytest -q` passes
- `/search` result schema includes required fields expected by client
- invalid `service_point` samples are rejected
