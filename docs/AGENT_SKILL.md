---
name: mrs-spatial-registry
description: >
  Interacts with Mixed Reality Service (MRS) servers to register, discover,
  update, and remove services anchored to geographic locations. Use when the
  user asks about services at a physical location, wants to find what exists
  near a coordinate, or needs to register a service at a place. The canonical
  MRS server is https://owen.iz.net.
---

# MRS Agent Skill

MRS is a federated spatial registry — "DNS for physical space." Agents use it
to associate HTTPS service endpoints with geographic spheres and to search for
services near any point on Earth.

**Canonical server:** `https://owen.iz.net`

## Quick Start

The most common operation is searching for services near a location. This
requires no authentication:

```http
POST https://owen.iz.net/search
Content-Type: application/json

{
  "location": {"lat": -33.8568, "lon": 151.2153},
  "range": 1000
}
```

This returns all services registered within 1 km of the Sydney Opera House,
sorted most-specific first, along with referrals to other MRS servers that may
hold additional results.

---

## Authentication

Read operations (search, discovery) require **no auth**. Write operations
(register, update, release) require a bearer token.

### Register an Account (one-time)

```http
POST https://owen.iz.net/auth/register
Content-Type: application/json

{"username": "alice", "password": "s3cure-pass!", "email": "alice@example.com"}
```

Returns: `{"token": "<bearer_token>", "expires_at": "..."}`

### Login (returning user)

```http
POST https://owen.iz.net/auth/login
Content-Type: application/json

{"username": "alice", "password": "s3cure-pass!"}
```

Returns: `{"token": "<bearer_token>", "expires_at": "..."}`

### Using the Token

Add this header to all authenticated requests:

```
Authorization: Bearer <token>
```

Tokens expire after **1 week** by default. On `401`, call `/auth/login` again.

### Verify Identity

```http
GET https://owen.iz.net/auth/me
Authorization: Bearer <token>
```

Returns: `{"id": "alice@owen.iz.net", "created_at": "...", "is_local": true}`

**Credential requirements:**
- Username: 1–64 characters, alphanumeric plus `-` and `_`
- Password: 8–128 characters
- Email: must contain `@` and `.` — may need to be pre-whitelisted by the server operator

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Registration** | A service anchored to a geographic sphere (center + radius) |
| **Service point** | The HTTPS URL where the registered service lives |
| **Search** | Find registrations whose spheres overlap a query point + range |
| **Referral** | A pointer to another MRS server that may have additional results |
| **Identity** | `username@server-domain` (e.g. `alice@owen.iz.net`) |
| **FOAD** | "Fade Out And Disappear" — hides a registration from search |
| **Tombstone** | A deletion marker that propagates across federated servers |

---

## API Reference

### POST /search — Find Services Near a Location

No authentication required.

```http
POST https://owen.iz.net/search
Content-Type: application/json

{
  "location": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
  "range": 1000
}
```

**Parameters:**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `location.lat` | float | yes | −90 to 90 | Decimal degrees latitude |
| `location.lon` | float | yes | −180 to 180 | Decimal degrees longitude |
| `location.ele` | float | no | default 0 | Meters above sea level |
| `range` | float | yes | >0, ≤1 000 000 | Search radius in meters |

**Response (200):**

```json
{
  "status": "ok",
  "results": [
    {
      "id": "reg_Xk9mQ2vLp4Tz",
      "space": {
        "type": "sphere",
        "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
        "radius": 50
      },
      "service_point": "https://example.com/opera-house",
      "foad": false,
      "distance": 12.5,
      "owner": "alice@owen.iz.net",
      "origin_server": "https://owen.iz.net",
      "origin_id": "reg_Xk9mQ2vLp4Tz",
      "version": 1,
      "created": "2025-06-15T10:30:00Z",
      "updated": "2025-06-15T10:30:00Z"
    }
  ],
  "referrals": [
    {"server": "https://other-mrs.example.com", "hint": "Asia-Pacific"}
  ]
}
```

**Behavior:**
- Results are sorted smallest-sphere-first, then by distance — the first
  result is typically the most specific match.
- `distance` is in meters from the query point to the sphere center.
- FOAD registrations are never returned.
- Up to 100 results are returned per query.
- `referrals` list other MRS servers whose authoritative regions overlap the
  search area. Follow them for comprehensive coverage.

---

### POST /register — Register a Service at a Location

Authentication required.

```http
POST https://owen.iz.net/register
Content-Type: application/json
Authorization: Bearer <token>

{
  "space": {
    "type": "sphere",
    "center": {"lat": 40.7484, "lon": -73.9857, "ele": 0},
    "radius": 100
  },
  "service_point": "https://example.com/empire-state",
  "foad": false
}
```

**Parameters:**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `space.type` | string | yes | `"sphere"` | Only spheres are supported |
| `space.center.lat` | float | yes | −90 to 90 | Latitude |
| `space.center.lon` | float | yes | −180 to 180 | Longitude |
| `space.center.ele` | float | no | default 0 | Elevation in meters |
| `space.radius` | float | yes | >0, ≤1 000 000 | Radius in meters |
| `service_point` | string | yes* | Valid `https://` URL | The service endpoint. *Not required if `foad: true` |
| `foad` | bool | no | default false | Hide from search results |

**Response (201):**

```json
{
  "status": "registered",
  "registration": {
    "id": "reg_Xk9mQ2vLp4Tz",
    "space": {"type": "sphere", "center": {"lat": 40.7484, "lon": -73.9857, "ele": 0}, "radius": 100},
    "service_point": "https://example.com/empire-state",
    "foad": false,
    "owner": "alice@owen.iz.net",
    "origin_server": "https://owen.iz.net",
    "origin_id": "reg_Xk9mQ2vLp4Tz",
    "version": 1,
    "created": "2025-06-20T14:00:00Z",
    "updated": "2025-06-20T14:00:00Z"
  }
}
```

**Important:**
- `service_point` must be `https://` — plain HTTP is rejected. No fragments
  (`#`), credentials, control characters, or whitespace.
- Save the returned `id` — it is needed for update and release operations.
- Choose `radius` to match the real-world footprint of the service (see
  Radius Guide below).

---

### PUT /register/{id} — Update a Registration

Authentication required. Must be the owner.

```http
PUT https://owen.iz.net/register/reg_Xk9mQ2vLp4Tz
Content-Type: application/json
Authorization: Bearer <token>

{
  "space": {
    "type": "sphere",
    "center": {"lat": 40.7484, "lon": -73.9857, "ele": 0},
    "radius": 200
  },
  "service_point": "https://example.com/empire-state-v2",
  "foad": false
}
```

Response (200): Same shape as POST /register, with incremented `version`.

Errors: `403` not the owner, `404` not found, `409` originated on another server.

---

### POST /release — Delete a Registration

Authentication required. Must be the owner.

```http
POST https://owen.iz.net/release
Content-Type: application/json
Authorization: Bearer <token>

{"id": "reg_Xk9mQ2vLp4Tz"}
```

Response (200): `{"status": "released", "id": "reg_Xk9mQ2vLp4Tz"}`

Errors: `403` not the owner, `404` not found, `409` originated on another server.

---

### GET /auth/me/registrations — List Your Registrations

Authentication required.

```http
GET https://owen.iz.net/auth/me/registrations
Authorization: Bearer <token>
```

Response (200): `{"registrations": [<Registration>, ...]}`

---

### GET /.well-known/mrs — Server Discovery

No authentication required.

```http
GET https://owen.iz.net/.well-known/mrs
```

Response (200):

```json
{
  "mrs_version": "0.2.0",
  "server": "https://owen.iz.net",
  "operator": "admin@owen.iz.net",
  "authoritative_regions": [],
  "known_peers": [{"server": "https://peer.example.com", "hint": "EU region"}],
  "capabilities": {"geometry_types": ["sphere"], "max_radius": 1000000}
}
```

Call this first to verify the server is reachable and to learn its
capabilities, version, and known peers.

---

### GET /.well-known/mrs/keys/{identity} — Public Key Retrieval

No authentication required.

```http
GET https://owen.iz.net/.well-known/mrs/keys/alice
```

Accepts a local username (`alice`), a full identity (`alice@owen.iz.net`), or
`_server` for the server's own Ed25519 key.

Response (200): `{"id": "alice@owen.iz.net", "public_key": {"type": "Ed25519", "key": "<base64>"}, "created": "..."}`

---

## Error Handling

All errors return JSON with a `detail` field describing the problem.

| Status | Meaning | Recovery |
|--------|---------|----------|
| 400 | Invalid data or limits exceeded | Check field values against constraints above |
| 401 | Token missing, invalid, or expired | Call `/auth/login` to get a fresh token, then retry |
| 403 | Ownership violation or email not whitelisted | Only the registration owner can modify it |
| 404 | Resource not found | Verify the ID or identity string |
| 409 | Cannot modify a federated registration | Modify it on its `origin_server` instead |
| 422 | Validation failure | Check required fields and data types |

---

## Common Workflows

### 1. Find services near a location

```
POST /search  { location: {lat, lon}, range: 1000 }
→ If no results, widen range to 5000, then 10000
→ If referrals returned and user wants comprehensive results, repeat search at each referral server
→ Present results: service_point URLs, distances, owners
```

### 2. Register a service

```
POST /auth/login (or /auth/register if new)  → save token
POST /register  { space: {type: "sphere", center: {lat, lon}, radius}, service_point }  → save id
→ Confirm: "Registered at [lat, lon], radius [X]m, ID: [id]"
```

### 3. Update a registration

```
GET /auth/me/registrations  → find the registration id
PUT /register/{id}  { updated fields }
→ Confirm new version number
```

### 4. Remove a registration

```
GET /auth/me/registrations  → find the registration id
POST /release  { id }
→ Confirm deletion
```

### 5. Explore the MRS federation

```
GET /.well-known/mrs  → note known_peers
→ For each peer: GET <peer>/.well-known/mrs
→ Build a map of the federation topology
```

---

## Practical Reference

### Radius Guide

| Scale | Radius | Example |
|-------|--------|---------|
| A room | 10 m | Conference room, exhibit |
| A building | 50 m | Museum, restaurant, shop |
| A city block | 500 m | Plaza, park, campus |
| A neighborhood | 5 000 m | District, suburb |
| A metro area | 50 000 m | City-wide service |
| A region | 500 000 m | State or province |

### Coordinate Reference

| Location | Latitude | Longitude |
|----------|----------|-----------|
| Sydney Opera House | −33.8568 | 151.2153 |
| Empire State Building | 40.7484 | −73.9857 |
| Eiffel Tower | 48.8584 | 2.2945 |
| Tokyo Tower | 35.6586 | 139.7454 |

Negative latitude = south. Negative longitude = west.

### Key Behaviors

- All requests and responses are `application/json`.
- CORS is fully open — browser-based agents work without proxies.
- Tokens last 1 week by default. Cache them; do not login on every request.
- Registration ownership is permanent — only the creator can modify or delete.
- Federated registrations (where `origin_server` differs from the queried
  server) are read-only on non-origin servers.
- No server-side rate limiting, but agents should avoid tight polling loops.

---

## Quick Reference

| Action | Method | Path | Auth? |
|--------|--------|------|-------|
| Search nearby | POST | `/search` | No |
| Register space | POST | `/register` | Yes |
| Update space | PUT | `/register/{id}` | Yes |
| Release space | POST | `/release` | Yes |
| Create account | POST | `/auth/register` | No |
| Login | POST | `/auth/login` | No |
| Who am I | GET | `/auth/me` | Yes |
| My registrations | GET | `/auth/me/registrations` | Yes |
| Server info | GET | `/.well-known/mrs` | No |
| Public keys | GET | `/.well-known/mrs/keys/{id}` | No |
