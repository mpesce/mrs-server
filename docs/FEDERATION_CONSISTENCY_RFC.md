# Federation Consistency RFC (Draft)

**Status:** Draft for v0.5.x planning  
**Goal:** Prevent stale/conflicting duplicates across MRS servers while enabling bootstrap and sync.

## Problem
Naive cross-server dataset transfer creates duplicate registrations and inconsistency when records change or are deleted. Search can return conflicting copies unless authority and merge rules are explicit.

## Design Principles
1. **Single-writer authority:** each registration has one canonical origin server.
2. **Replicas are read-only:** non-origin servers do not mutate canonical records.
3. **Deterministic dedupe:** search merges duplicate copies consistently.
4. **Incremental sync:** bootstrap snapshot + delta changes, not full overwrite each time.

## Data Model Extensions
Add fields to registration records:

- `origin_server` (string, required) — canonical server URL
- `origin_id` (string, required) — stable ID on origin server
- `version` (integer, required) — monotonic version incremented by origin on write
- `updated` (ISO8601, required) — last canonical update timestamp
- `replicated_from` (string, optional) — source server URL for this replica
- `last_synced_at` (ISO8601, optional) — replica sync metadata

### Canonical identity
Canonical record key:
`(origin_server, origin_id)`

## Ownership / Write Rules
- Create on origin server assigns:
  - `origin_server = this server`
  - `origin_id = registration.id`
  - `version = 1`
- Updates/deletes are allowed **only** on origin server.
- Non-origin servers receiving update/delete for replicated record:
  - return `409 not_authoritative` OR
  - return referral/redirect to origin server.

## Search Merge Rules
When multiple servers return same canonical record:
1. Group by `(origin_server, origin_id)` when present.
2. If missing (legacy), heuristic group by normalized `service_point` + near-identical geometry.
3. Within group choose winner by:
   - highest `version`
   - then latest `updated`
   - then prefer record from `origin_server`.

## Sync Protocol (Proposed)

### 1) Bootstrap snapshot
New server pulls full snapshot from a peer.

`GET /sync/snapshot`

Returns registrations with canonical metadata + optional pagination.

### 2) Incremental delta
Periodic sync from last checkpoint.

`GET /sync/changes?since=<cursor>`

Returns created/updated/deleted events and next cursor.

### 3) Tombstones
Deletes must propagate as tombstones to prevent resurrection.

Tombstone fields:
- `origin_server`
- `origin_id`
- `version`
- `deleted_at`

Retention window configurable (e.g. 30 days+).

## Conflict Handling
Conflict = same `(origin_server, origin_id)` with divergent payloads.

Resolver:
- accept highest `version`
- if equal version + payload mismatch, flag `conflict_detected` metric and retain origin copy.

## API/Compat Plan

### Phase 1 (non-breaking)
- Add optional fields in responses.
- Add dedupe logic in search engine/client when metadata exists.
- Keep existing endpoints working.

### Phase 2
- Introduce `/sync/snapshot` and `/sync/changes` endpoints.
- Add tombstone support.

### Phase 3
- Enforce authority checks on non-origin mutation attempts.

## Operational Guidance
- Start with referral-first federation.
- Enable replication only between trusted peers.
- Keep per-peer sync logs and lag metrics.
- Expose metrics:
  - sync lag
  - conflicts detected
  - tombstones applied
  - dedupe groups merged

## Why this should come before large seeding
Large seed imports (e.g., Wikipedia-derived points) amplify duplicate and staleness problems. Authority + dedupe + delta sync must be defined first to keep the network trustworthy as data evolves.
