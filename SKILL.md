---
name: mrs-server-dev
description: Work on the Mixed Reality Service server codebase. Use for FastAPI endpoint changes, server-side validation/auth updates, search/register/release contract changes, database-layer behavior, and server test/release hardening.
---

# MRS Server Dev

1. Activate virtual environment.
   - `source .venv/bin/activate`

2. Run server tests before changes.
   - `pytest -q`

3. Implement focused server-side changes only.
   - Keep API contracts stable unless explicitly requested.
   - Treat `service_point` as untrusted input.

4. Re-run tests after edits.
   - `pytest -q`

5. Verify changed endpoints manually.
   - Start server: `python -m mrs_server.main --host 127.0.0.1 --port 8000`
   - Exercise changed endpoint(s) with `curl`.

6. Confirm release gates when requested.
   - Use workspace harnesses from `../scripts/` as directed.

## Critical contracts
- `/register`
- `/release`
- `/search`
- `/.well-known/mrs`

## Security rules
- Reject malformed or unsafe `service_point` URIs.
- Do not weaken auth/ownership checks without explicit approval and tests.
