# Mixed Reality Service (MRS) Protocol Specification

**Version:** 0.5.0-draft
**Date:** March 2026
**Author:** Mark D. Pesce (mpesce@gmail.com)
**Status:** Working Draft

---

## Abstract

The Mixed Reality Service (MRS) provides a federated protocol for binding geospatial coordinates to Universal Resource Identifiers (URIs). MRS enables agents—both AI systems and autonomous physical devices—to discover location-relevant services and metadata through a simple query interface.

MRS is to physical space what DNS is to the internet namespace: a distributed, federated system that translates coordinates into actionable service endpoints.

---

## 1. Introduction

### 1.1 Problem Statement

Autonomous systems—whether AI agents reasoning about physical space or drones navigating urban environments—lack a standardized mechanism to discover what services, permissions, or metadata are associated with a given location.

Current approaches rely on proprietary databases, manual configuration, or application-specific solutions. This creates fragmentation: a drone guidance system cannot query the same infrastructure as an AI agent planning a delivery route.

### 1.2 Design Goals

MRS is designed to be:

- **Federated:** No central authority. Anyone can operate a server authoritative for their spaces.
- **Open:** Domain-based identity. No special infrastructure required to participate.
- **Simple:** Three core operations. JSON over HTTPS.
- **Agent-first:** Optimized for programmatic consumption, not human browsing.

### 1.3 Historical Context

MRS descends from Cyberspace Protocol, first proposed at WWW1 in 1994 as infrastructure for navigable 3D spaces on the web. The core insight—that spatial coordinates require a resolution service analogous to DNS—has remained constant through successive refinements for augmented reality (2016) and autonomous systems (2026).

---

## 2. Terminology

**Space:** A bounded volume in the physical world, defined by coordinates and geometry.

**Registration:** A binding between a Space and a Service Point, stored in the MRS registry.

**Service Point:** A URI that provides services or metadata relevant to the registered Space.

**Server:** An MRS protocol endpoint that maintains registrations and responds to queries.

**Authoritative Server:** A server that holds the canonical registration for a given Space. Identified by the `origin_server` field on a registration.

**Referral:** A hint from one server pointing to another server that may have relevant registrations.

**Client:** Any system that queries MRS—typically an AI agent or autonomous device.

**FOAD Flag:** "Fade Out And Disappear" — a privacy marker indicating a Space is registered but explicitly excluded from search results.

**Tombstone:** A deletion record that propagates across federated servers, ensuring released registrations are removed network-wide.

---

## 3. Data Model

### 3.1 Coordinates

MRS uses the WGS 84 coordinate system (the standard for GPS).

| Field | Type | Description |
|-------|------|-------------|
| `lat` | float | Latitude in degrees. Range: -90.0 to 90.0 |
| `lon` | float | Longitude in degrees. Range: -180.0 to 180.0 |
| `ele` | float | Elevation in meters above sea level. Default: 0. Negative values for below sea level. |

Precision: Coordinates SHOULD be transmitted with at least 6 decimal places (approximately 0.1 meter precision).

### 3.2 Geometry

A Space is defined by a location and a bounding volume. MRS supports two geometry types:

#### 3.2.1 Sphere (REQUIRED)

All MRS implementations MUST support spherical geometry.

```json
{
  "type": "sphere",
  "center": { "lat": -33.85939, "lon": 151.20458, "ele": 10.0 },
  "radius": 50.0
}
```

`radius` is in meters. Maximum value: 1,000,000 (1000 km).

#### 3.2.2 Polygon (OPTIONAL)

MRS implementations MAY support polygonal geometry for more precise boundaries.

```json
{
  "type": "polygon",
  "vertices": [
    { "lat": -33.8590, "lon": 151.2040, "ele": 0.0 },
    { "lat": -33.8590, "lon": 151.2050, "ele": 0.0 },
    { "lat": -33.8600, "lon": 151.2050, "ele": 0.0 },
    { "lat": -33.8600, "lon": 151.2040, "ele": 0.0 }
  ],
  "height": 100.0
}
```

Polygons are extruded vertically. `height` is in meters above the lowest vertex elevation.

### 3.3 Registration

A Registration binds a Space to a Service Point.

```json
{
  "id": "reg_a1b2c3d4e5f6",
  "space": {
    "type": "sphere",
    "center": { "lat": -33.85939, "lon": 151.20458, "ele": 10.0 },
    "radius": 50.0
  },
  "service_point": "https://example.com/spaces/sydney-opera-house",
  "foad": false,
  "owner": "admin@example.com",
  "origin_server": "https://mrs.example.com",
  "origin_id": "reg_a1b2c3d4e5f6",
  "version": 1,
  "created": "2026-01-15T10:30:00Z",
  "updated": "2026-01-15T10:30:00Z"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier for this registration. Format: `reg_` followed by a random token. |
| `space` | object | Yes | Geometry defining the bounded volume |
| `service_point` | URI | No* | HTTPS URI for services/metadata at this space |
| `foad` | boolean | Yes | If true, space is registered but excluded from search results |
| `owner` | string | Yes | Domain-based identity of the registrant (e.g. `user@domain`) |
| `origin_server` | string | Yes | URL of the server where this registration was created |
| `origin_id` | string | Yes | The `id` on the origin server (same as `id` on the authoritative server) |
| `version` | integer | Yes | Monotonically increasing version number; starts at 1, incremented on each update |
| `created` | ISO 8601 | Yes | Timestamp of initial registration |
| `updated` | ISO 8601 | Yes | Timestamp of last modification |

*`service_point` is REQUIRED if `foad` is false. If `foad` is true, `service_point` SHOULD be omitted.

`service_point` MUST use the `https://` scheme. Servers MUST reject service points using other schemes (e.g. `http://`, `javascript:`, `data:`). Service points MUST NOT contain URI fragments (`#`), embedded credentials, or control characters.

### 3.4 Tombstone

A Tombstone records the deletion of a registration so that federated servers can propagate the removal.

```json
{
  "origin_server": "https://mrs.example.com",
  "origin_id": "reg_a1b2c3d4e5f6",
  "version": 3,
  "deleted_at": "2026-03-01T12:00:00Z"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `origin_server` | string | Yes | The authoritative server for the deleted registration |
| `origin_id` | string | Yes | The registration ID on the origin server |
| `version` | integer | Yes | Set to the registration's last version + 1 |
| `deleted_at` | ISO 8601 | Yes | When the deletion occurred |

The combination of `(origin_server, origin_id)` uniquely identifies a tombstone.

---

## 4. Protocol Operations

All operations use HTTPS. Request and response bodies are JSON with Content-Type `application/json`.

Errors are returned as JSON with a `detail` field describing the problem:

```json
{
  "detail": "service_point is required unless foad is true"
}
```

For structured errors (e.g. federation conflicts), `detail` MAY be an object:

```json
{
  "detail": {
    "error": "not_authoritative",
    "message": "This server is not authoritative for the registration",
    "origin_server": "https://origin.example.com",
    "origin_id": "reg_abc123"
  }
}
```

### 4.1 Register

Creates a new Registration.

**Request:** `POST /register`

**Authentication:** Required.

```json
{
  "space": {
    "type": "sphere",
    "center": { "lat": -33.85939, "lon": 151.20458, "ele": 10.0 },
    "radius": 50.0
  },
  "service_point": "https://example.com/spaces/my-space",
  "foad": false
}
```

**Response (success):** `201 Created`

```json
{
  "status": "registered",
  "registration": {
    "id": "reg_a1b2c3d4e5f6",
    "space": {
      "type": "sphere",
      "center": { "lat": -33.85939, "lon": 151.20458, "ele": 10.0 },
      "radius": 50.0
    },
    "service_point": "https://example.com/spaces/my-space",
    "foad": false,
    "owner": "user@example.com",
    "origin_server": "https://mrs.example.com",
    "origin_id": "reg_a1b2c3d4e5f6",
    "version": 1,
    "created": "2026-01-26T08:30:00Z",
    "updated": "2026-01-26T08:30:00Z"
  }
}
```

**Validation rules:**

- `service_point` is REQUIRED unless `foad` is true.
- `service_point` MUST be an HTTPS URL. No fragments, credentials, or control characters.
- `radius` MUST be positive and MUST NOT exceed the server's configured maximum (see Section 4.6).
- The server MUST reject duplicate registrations. A registration is a duplicate if it matches an existing registration on all of: `owner`, `center` (lat, lon, ele), `radius`, `service_point`, and `foad`. Duplicate rejection returns `409 Conflict` with the existing registration's ID.
- The server MAY enforce a per-user registration limit.

**Error responses:**

| Status | Condition |
|--------|-----------|
| 400 | Missing service_point (when foad=false), radius exceeds maximum, per-user limit reached |
| 401 | Missing or invalid authentication |
| 409 | Duplicate registration already exists |
| 422 | Request body fails schema validation (invalid coordinates, bad URL scheme, etc.) |

### 4.2 Update

Modifies an existing Registration. Only the owner may update a registration, and only on its authoritative server.

**Request:** `PUT /register/{id}`

**Authentication:** Required.

```json
{
  "space": {
    "type": "sphere",
    "center": { "lat": -33.85939, "lon": 151.20458, "ele": 10.0 },
    "radius": 75.0
  },
  "service_point": "https://example.com/spaces/my-space-v2",
  "foad": false
}
```

**Response (success):** `200 OK`

Same shape as POST /register, with `version` incremented and `updated` timestamp refreshed.

**Error responses:**

| Status | Condition |
|--------|-----------|
| 400 | Same validation rules as register |
| 401 | Missing or invalid authentication |
| 403 | Authenticated user is not the owner |
| 404 | Registration ID not found |
| 409 | Server is not authoritative (registration originated elsewhere). Response includes `origin_server` and `origin_id` |

### 4.3 Release

Removes a Registration and records a Tombstone for federation propagation.

**Request:** `POST /release`

**Authentication:** Required. Only the owner may release a registration, and only on its authoritative server.

```json
{
  "id": "reg_a1b2c3d4e5f6"
}
```

**Response (success):** `200 OK`

```json
{
  "status": "released",
  "id": "reg_a1b2c3d4e5f6"
}
```

When a registration is released:

1. The registration is deleted from the registrations table.
2. A tombstone is created with `version` set to the registration's last version + 1.
3. The tombstone's `deleted_at` is set to the current UTC time.

Tombstones are retained so that federated servers can learn about deletions via the sync protocol (Section 4.8).

**Error responses:**

| Status | Condition |
|--------|-----------|
| 401 | Missing or invalid authentication |
| 403 | Authenticated user is not the owner |
| 404 | Registration ID not found |
| 409 | Server is not authoritative |

### 4.4 Search

Queries for Registrations intersecting a location.

**Request:** `POST /search`

**Authentication:** Not required.

```json
{
  "location": { "lat": -33.85939, "lon": 151.20458, "ele": 10.0 },
  "range": 100.0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `location` | object | Yes | Center point for search (lat, lon, ele) |
| `range` | float | Yes | Search radius in meters. Must be > 0 and ≤ 1,000,000 |

**Response:** `200 OK`

```json
{
  "status": "ok",
  "results": [
    {
      "id": "reg_a1b2c3d4e5f6",
      "space": {
        "type": "sphere",
        "center": { "lat": -33.85939, "lon": 151.20458, "ele": 10.0 },
        "radius": 50.0
      },
      "service_point": "https://example.com/spaces/my-space",
      "foad": false,
      "distance": 12.5,
      "owner": "user@example.com",
      "origin_server": "https://mrs.example.com",
      "origin_id": "reg_a1b2c3d4e5f6",
      "version": 1,
      "created": "2026-01-15T10:30:00Z",
      "updated": "2026-01-15T10:30:00Z"
    }
  ],
  "referrals": [
    {
      "server": "https://sydney.mrs.example.org",
      "hint": "Authoritative for Sydney metropolitan area"
    }
  ]
}
```

**Behavior:**

- **FOAD exclusion:** Registrations with `foad: true` are NEVER returned in search results.
- **Spatial filtering:** The server uses bounding-box pre-filtering for efficiency, then performs sphere-circle intersection to determine actual overlap.
- **Distance:** `distance` is the haversine distance in meters from the query point to the registration's sphere center.
- **Ordering:** Results are sorted by volume (smallest bounding sphere first), then by distance (nearest first). This ensures the most specific, closest results appear first.
- **Limit:** Results are capped at the server's configured maximum (default: 100).
- **Referrals:** The server includes referrals to known peer servers. Referrals are hints, not guarantees—a referred server may or may not have additional results.

### 4.5 Server Metadata

Returns information about the server, its capabilities, and its federation peers.

**Request:** `GET /.well-known/mrs`

**Authentication:** Not required.

**Response:** `200 OK`

```json
{
  "mrs_version": "0.5.0",
  "server": "https://mrs.example.com",
  "operator": "admin@example.com",
  "authoritative_regions": [
    {
      "type": "sphere",
      "center": { "lat": -33.8688, "lon": 151.2093, "ele": 0 },
      "radius": 50000
    }
  ],
  "known_peers": [
    {
      "server": "https://melbourne.mrs.example.org",
      "hint": "Authoritative for Melbourne area"
    }
  ],
  "capabilities": {
    "geometry_types": ["sphere"],
    "max_radius": 1000000
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `mrs_version` | string | Protocol version implemented by this server |
| `server` | string | Canonical URL of this server |
| `operator` | string | Contact email for the server operator |
| `authoritative_regions` | array | Geometries defining the regions this server claims authority over. May be empty. |
| `known_peers` | array | Other MRS servers this server is aware of |
| `capabilities` | object | Supported geometry types and limits |

### 4.6 Public Key Retrieval

Returns the public key for an MRS identity, used to verify HTTP Signatures in federated operations.

**Request:** `GET /.well-known/mrs/keys/{identity}`

**Authentication:** Not required.

`{identity}` may be:
- A local username (e.g. `alice`) — resolved to `alice@this-server-domain`
- A full MRS identity (e.g. `alice@mrs.example.com`) — domain must match this server
- `_server` — returns the server's own signing key

**Response:** `200 OK`

```json
{
  "id": "alice@mrs.example.com",
  "public_key": {
    "type": "Ed25519",
    "key": "base64-encoded-public-key"
  },
  "created": "2026-01-15T10:30:00Z"
}
```

**Error responses:**

| Status | Condition |
|--------|-----------|
| 404 | Identity not found, or identity domain does not match this server |

### 4.7 Authentication Endpoints

MRS defines endpoints for account management and local authentication.

#### 4.7.1 Register Account

**Request:** `POST /auth/register`

```json
{
  "username": "alice",
  "password": "secure-password-123",
  "email": "alice@example.com"
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `username` | string | Yes | 1–64 characters, pattern: `[a-zA-Z0-9_-]+` |
| `password` | string | Yes | 8–128 characters |
| `email` | string | Yes | 3–254 characters, valid email format |

**Response (success):** `201 Created`

```json
{
  "token": "bearer-token-string",
  "expires_at": "2026-01-22T08:30:00Z"
}
```

The server MAY require email whitelisting. If enabled, only pre-approved email addresses may register (403 Forbidden otherwise).

Emails are normalized to lowercase. Usernames are combined with the server domain to form the MRS identity: `username@server-domain`.

**Error responses:**

| Status | Condition |
|--------|-----------|
| 400 | Validation error (bad username/password format) or user already exists |
| 403 | Email not whitelisted (when whitelist is enabled) |

#### 4.7.2 Login

**Request:** `POST /auth/login`

```json
{
  "username": "alice",
  "password": "secure-password-123"
}
```

**Response (success):** `200 OK`

```json
{
  "token": "bearer-token-string",
  "expires_at": "2026-01-22T08:30:00Z"
}
```

Tokens expire after a server-configured period (default: 1 week / 168 hours).

**Error responses:**

| Status | Condition |
|--------|-----------|
| 401 | Invalid username or password |

#### 4.7.3 Current Identity

**Request:** `GET /auth/me`

**Authentication:** Required.

**Response:** `200 OK`

```json
{
  "id": "alice@mrs.example.com",
  "created_at": "2026-01-15T10:30:00Z",
  "is_local": true
}
```

#### 4.7.4 List Own Registrations

**Request:** `GET /auth/me/registrations`

**Authentication:** Required.

**Response:** `200 OK`

```json
{
  "registrations": [
    { "...registration object..." }
  ]
}
```

Returns all registrations owned by the authenticated user, ordered by `created` descending (newest first).

### 4.8 Sync Protocol

MRS defines two endpoints for federation synchronization, enabling servers to replicate registrations and propagate deletions.

Both endpoints are public (no authentication required) to allow any peer to sync.

#### 4.8.1 Snapshot (Bootstrap Sync)

Used by a new peer to obtain a complete copy of all registrations.

**Request:** `GET /sync/snapshot`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `cursor` | string | No | Registration ID to resume from (pagination) |
| `limit` | integer | No | Number of registrations per page. Range: 1–1000. Default: 200 |

**Response:** `200 OK`

```json
{
  "status": "ok",
  "registrations": [
    { "...registration object..." }
  ],
  "next_cursor": "reg_xyz789"
}
```

Registrations are returned in ID order. If `next_cursor` is non-null, more registrations are available—pass it as the `cursor` parameter on the next request. When `next_cursor` is null, all registrations have been retrieved.

#### 4.8.2 Changes (Incremental Sync)

Used by an existing peer to catch up on changes since its last sync.

**Request:** `GET /sync/changes`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `since` | string | Yes | ISO 8601 timestamp. Returns changes after this time. |
| `limit` | integer | No | Maximum items per page. Range: 1–5000. Default: 500 |

**Response:** `200 OK`

```json
{
  "status": "ok",
  "registrations": [
    { "...registration objects updated since the cursor..." }
  ],
  "tombstones": [
    {
      "origin_server": "https://mrs.example.com",
      "origin_id": "reg_a1b2c3d4e5f6",
      "version": 3,
      "deleted_at": "2026-03-01T12:00:00Z"
    }
  ],
  "next_cursor": "2026-03-01T12:05:00+00:00"
}
```

- `registrations` contains registrations with `updated_at` after `since`, ordered by `updated_at` ascending.
- `tombstones` contains tombstones with `deleted_at` after `since`, ordered by `deleted_at` ascending.
- `next_cursor` is an ISO 8601 timestamp. Use it as the next `since` value. If no changes occurred, `next_cursor` is the current UTC time.

A syncing peer should:

1. Use snapshot to bootstrap a full copy.
2. Use changes periodically (or on demand) to stay current.
3. Apply tombstones by deleting the corresponding registration.
4. Use upsert semantics: if a registration already exists, update it only if the incoming version is higher.

---

## 5. Federation Model

MRS operates as a federated network of servers. There is no central authority or root server.

### 5.1 Authority

A server is **authoritative** for a Registration if it is the `origin_server` for that Registration. Only the authoritative server may accept updates or releases for a registration.

A server declares its authoritative *regions* (geographic areas it serves) in its metadata (see 4.5). Multiple servers may hold registrations for overlapping spaces. This is expected and valid—a city government's server might register municipal boundaries while individual property owners register their buildings.

### 5.2 Registration Provenance

Every registration carries three federation fields:

- `origin_server` — the URL of the server where the registration was first created.
- `origin_id` — the registration's ID on the origin server.
- `version` — a monotonically increasing counter, starting at 1, incremented on each update.

On the authoritative server, `origin_server` equals the server's own URL and `origin_id` equals `id`. On replicas, these fields point back to the source.

When a client attempts to update or release a registration on a non-authoritative server, the server MUST return `409 Conflict` with the `origin_server` and `origin_id`, directing the client to the authoritative server.

### 5.3 Discovery via Referral

When a server receives a search query:

1. It returns all matching Registrations it holds (both local and replicated).
2. It includes referrals to known peer servers.

Referrals are hints, not guarantees. A referred server may or may not have additional results.

### 5.4 Client-Side Resolution

The MRS client library is responsible for:

1. Issuing the initial search query
2. Following referrals (up to a configured depth limit)
3. Deduplicating results (by registration ID)
4. Detecting cycles (do not re-query servers already visited)
5. Aggregating and sorting final results

This keeps servers simple and stateless while enabling comprehensive discovery.

### 5.5 Peer Discovery

Servers discover peers through:

- **Manual configuration:** Operators configure known peers (bootstrap peers)
- **Referral accumulation:** Servers learn about peers from referrals received during queries
- **Well-known registries:** Community-maintained lists of public MRS servers (out of scope for this specification)

### 5.6 Consistency Model

MRS uses eventual consistency. When a Registration is created, updated, or released:

1. The authoritative server updates immediately.
2. Other servers learn of the change through the sync protocol (Section 4.8).
3. Deletions propagate via tombstones.

There is no global synchronization. Clients should treat results as best-effort snapshots.

### 5.7 Sync Semantics

When importing registrations from a peer:

- Use **upsert** semantics: insert if new, update if the incoming version is higher.
- For tombstones, take the higher version on conflict.
- Recompute spatial indexes (bounding boxes) on import.

---

## 6. Identity and Authentication

### 6.1 Domain-Based Identity

MRS uses domain-based identity, similar to email addresses:

```
username@domain.example
```

The domain portion identifies a server or organization. The username identifies an account within that domain.

Every MRS identity has an associated Ed25519 public key, published at a well-known location:

```
GET https://domain.example/.well-known/mrs/keys/username
```

**Response:**

```json
{
  "id": "username@domain.example",
  "public_key": {
    "type": "Ed25519",
    "key": "base64-encoded-public-key"
  },
  "created": "2026-01-15T10:30:00Z"
}
```

This enables any server to verify signatures from any MRS identity without prior coordination.

### 6.2 Authentication Methods

MRS supports two authentication methods.

#### 6.2.1 Bearer Token (Local Authentication)

For clients authenticating to their home server, Bearer tokens provide a simple mechanism:

```
Authorization: Bearer <token>
```

Tokens are issued via `/auth/login` or `/auth/register` (see Section 4.7). Tokens are opaque strings, cryptographically generated. Default expiry: 1 week (168 hours). Expired tokens are rejected with `401`.

Bearer tokens are suitable when:
- Client and server have a pre-existing relationship
- The server issued the token through its own authentication flow
- Cross-server verification is not required

#### 6.2.2 HTTP Signatures (Federated Authentication)

For cross-server operations and portable identity, MRS uses HTTP Signatures based on RFC 9421.

**Signed Request Example:**

```http
POST /register HTTP/1.1
Host: other-server.example
Content-Type: application/json
Signature-Input: sig1=("@method" "@path" "content-digest" "mrs-identity"); \
  keyid="https://myserver.example/.well-known/mrs/keys/mark"; \
  created=1706256000; alg="ed25519"
Content-Digest: sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:
Signature: sig1=:base64-encoded-signature:
MRS-Identity: mark@myserver.example

{ "space": { ... }, "service_point": "..." }
```

**Required Signed Components:**
- `@method` — HTTP method
- `@path` — Request path
- `content-digest` — Hash of request body (for POST/PUT)
- `mrs-identity` — The MRS identity making the request

**Verification Process:**

1. Extract `MRS-Identity` header to get the claimed identity
2. Parse `keyid` from `Signature-Input` to get the public key URL
3. Verify the key URL domain matches the identity domain
4. Fetch the public key from the key URL
5. Verify the signature against the signed components
6. Confirm the identity is authorized for the requested operation

HTTP Signatures are REQUIRED when:
- Registering spaces on a server other than your home server
- Server-to-server communication
- Any operation where portable, verifiable identity is needed

### 6.3 Server Identity

A server's identity uses `_server` as the username portion:

```
_server@mrs.example.com
```

The server's public key is published at:

```
GET https://mrs.example.com/.well-known/mrs/keys/_server
```

### 6.4 Key Management

#### 6.4.1 Supported Algorithms

Servers MUST support Ed25519 signatures. Servers MAY additionally support:
- RSA-PSS (2048-bit minimum)
- ECDSA (P-256 or P-384)

Keys are generated automatically when a user account is created or when the server starts for the first time (for the server key).

#### 6.4.2 Key Rotation

Identities MAY publish multiple keys for rotation purposes:

```
GET https://domain.example/.well-known/mrs/keys/username
```

**Response with multiple keys:**

```json
{
  "id": "username@domain.example",
  "keys": [
    {
      "key_id": "key-2026-01",
      "type": "Ed25519",
      "key": "base64-encoded-public-key",
      "created": "2026-01-01T00:00:00Z",
      "expires": "2027-01-01T00:00:00Z"
    },
    {
      "key_id": "key-2025-01",
      "type": "Ed25519",
      "key": "base64-encoded-old-key",
      "created": "2025-01-01T00:00:00Z",
      "expires": "2026-02-01T00:00:00Z",
      "deprecated": true
    }
  ]
}
```

The `keyid` in `Signature-Input` SHOULD include the specific key identifier when multiple keys exist:

```
keyid="https://domain.example/.well-known/mrs/keys/username#key-2026-01"
```

#### 6.4.3 Key Caching

Servers SHOULD cache fetched public keys to reduce latency. Recommended cache lifetime: 1 hour. Servers MUST refetch keys when signature verification fails, to handle key rotation.

---

## 7. Security Considerations

### 7.1 Transport Security

All MRS traffic MUST use HTTPS. Servers MUST NOT accept plaintext HTTP connections for protocol operations.

Service points MUST use the `https://` scheme. Servers MUST reject registrations with non-HTTPS service points to prevent injection of dangerous URIs (e.g. `javascript:`, `data:`).

### 7.2 Privacy

Search queries reveal the querying client's location of interest. Servers:

- MUST NOT log query locations beyond what is necessary for operation
- SHOULD NOT share query patterns with third parties
- MAY implement rate limiting to prevent location tracking attacks

### 7.3 Abuse Prevention

The FOAD flag allows space owners to register without providing services—useful for declaring "do not enter" or "do not photograph" zones. However, MRS cannot enforce these declarations. Enforcement is the responsibility of consuming applications.

Servers SHOULD enforce duplicate registration detection to prevent database pollution. Servers MAY enforce per-user registration limits.

### 7.4 Verification of Ownership

This specification does not define how ownership of physical space is verified. This is intentionally left as a social and legal problem, not a technical one.

Servers MAY implement their own verification requirements. Possible approaches include:

- Self-attestation (trust-based)
- Integration with land registries
- Physical verification processes
- Reputation systems

Interoperability does not require agreement on verification methods.

### 7.5 Email Whitelisting

Servers MAY restrict account registration to pre-approved email addresses. When enabled, registration attempts with non-whitelisted emails are rejected with `403 Forbidden`.

---

## 8. Administration

MRS defines optional administrative endpoints for server operators. These endpoints MUST be restricted to localhost access only (connections from `127.0.0.1` or `::1`).

### 8.1 Export

**Request:** `GET /admin/export`

Returns the complete server state as JSON: all registrations, tombstones, and known peers.

### 8.2 Import

**Request:** `POST /admin/import`

Accepts the same format as export. Uses upsert semantics—safe to run repeatedly. Useful for backup/restore, migration, and bulk federation seeding.

### 8.3 Email Whitelist Management

- `GET /admin/whitelist` — List all whitelisted emails
- `POST /admin/whitelist` — Add email(s) to the whitelist
- `DELETE /admin/whitelist/{email}` — Remove an email from the whitelist

---

## 9. Future Work

### 9.1 MRSE: Service Enumeration

A future specification will define MRSE (Mixed Reality Service Enumeration)—a standard for what service points return. This may include:

- Permission schemas (overflight allowed, photography prohibited, etc.)
- Metadata formats (hours of operation, contact information, hazard warnings)
- Capability negotiation

### 9.2 Dynamic Spaces

The current specification addresses static spaces (land, buildings). A companion protocol for dynamic spaces (vehicles, temporary zones) may be developed.

### 9.3 Verification Protocols

Community protocols for ownership verification may emerge. These will be documented separately as best practices rather than specification requirements.

---

## 10. IANA Considerations

This specification requests registration of:

- `/.well-known/mrs` — MRS server metadata endpoint
- `/.well-known/mrs/keys/{identity}` — Public key endpoint for MRS identities
- `MRS-Identity` — HTTP header for MRS identity in signed requests

---

## 11. References

- RFC 3986: Uniform Resource Identifier (URI): Generic Syntax
- RFC 9421: HTTP Message Signatures
- WGS 84: World Geodetic System 1984

---

## Appendix A: Example Client Session

```python
# Pseudocode for MRS client library

def search(location, range=100, max_depth=3):
    visited = set()
    results = []
    queue = [initial_server]

    while queue and len(visited) < max_depth:
        server = queue.pop(0)
        if server in visited:
            continue
        visited.add(server)

        response = query_server(server, location, range)
        results.extend(response.results)
        queue.extend(r.server for r in response.referrals)

    # Deduplicate by registration ID
    unique = {r.id: r for r in results}

    # Sort by volume (smallest first), then distance
    return sorted(unique.values(), key=lambda r: (r.space.volume, r.distance))
```

---

## Appendix B: Endpoint Summary

| Action | Method | Path | Auth |
|--------|--------|------|------|
| Search nearby | POST | `/search` | No |
| Register space | POST | `/register` | Yes |
| Update space | PUT | `/register/{id}` | Yes |
| Release space | POST | `/release` | Yes |
| Create account | POST | `/auth/register` | No |
| Login | POST | `/auth/login` | No |
| Current identity | GET | `/auth/me` | Yes |
| Own registrations | GET | `/auth/me/registrations` | Yes |
| Server metadata | GET | `/.well-known/mrs` | No |
| Public keys | GET | `/.well-known/mrs/keys/{identity}` | No |
| Sync snapshot | GET | `/sync/snapshot` | No |
| Sync changes | GET | `/sync/changes` | No |
| Export (admin) | GET | `/admin/export` | Localhost |
| Import (admin) | POST | `/admin/import` | Localhost |

---

## Appendix C: Revision History

| Version | Date | Changes |
|---------|------|---------|
| 0.5.0-draft | 2026-01 | Initial working draft |
| 0.5.0-draft | 2026-03 | Added federation fields (origin_server, origin_id, version) to Registration data model. Added Tombstone data model. Documented Update endpoint (PUT /register/{id}). Documented Sync protocol (snapshot and changes). Documented Authentication endpoints (/auth/*). Documented Admin endpoints. Added duplicate registration rejection. Fixed FOAD definition and search behavior. Standardized error format. Added service_point validation rules. |

---

## Acknowledgements

The author thanks Tony Parisi, Owen Rowley, Peter Kennard, and Sir Tim Berners-Lee for their contributions to the ideas underlying this specification over three decades of development.
