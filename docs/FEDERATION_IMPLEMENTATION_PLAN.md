# Federation Consistency Implementation Plan

Tracks execution of `docs/FEDERATION_CONSISTENCY_RFC.md`.

## Phase 1 — Non-breaking metadata + dedupe prep

1. Add optional canonical metadata fields to registration model/DB:
   - `origin_server`, `origin_id`, `version`
2. On local creates, populate canonical defaults:
   - `origin_server=this_server`, `origin_id=id`, `version=1`
3. Include canonical metadata in `/register`, `/search`, and list responses.
4. Add search dedupe helper (server-side utility + tests) to merge duplicate canonical records.
5. Add client-side fallback dedupe support when canonical metadata appears.

## Phase 2 — Sync protocol skeleton

6. Add `/sync/snapshot` endpoint (paginated).
7. Add `/sync/changes?since=<cursor>` endpoint with created/updated/deleted events.
8. Add sync cursor persistence and per-peer state.
9. Add tombstone model and propagation for deletions.

## Phase 3 — Authority enforcement

10. Reject non-origin mutations on replicated records (`409 not_authoritative`).
11. Add optional referral/redirect to origin server in error payload.
12. Add metrics/logging:
    - sync lag
    - conflicts detected
    - tombstones applied
    - dedupe groups merged

## Tests / Release Gates

- Unit tests for canonical metadata defaults + update versioning.
- API tests for sync endpoints and authority errors.
- Integration test: bootstrap snapshot + delta replay + delete propagation.
- Regression test: conflicting duplicates resolve deterministically by `(version, updated, origin)`.
