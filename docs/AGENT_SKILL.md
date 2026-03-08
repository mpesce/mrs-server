# MRS Agent Skill

> A capability document for AI agents interacting with Mixed Reality Service servers.

## What This Is

This document teaches an AI agent how to use the **Mixed Reality Service (MRS)** protocol — a federated spatial registry that works like "DNS for physical space." Agents use MRS to register services at geographic locations and discover what services exist near any point on Earth.

**Canonical server:** `https://owen.iz.net`

## When to Use MRS

Use MRS when the user wants to:
- Find services, data, or metadata associated with a physical location
- Register a service or resource at a geographic location
- Manage spatial registrations they own
- Query what exists near a latitude/longitude coordinate
- Understand what's happening in a physical space

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Registration** | A service anchored to a geographic sphere (center point + radius) |
| **Service point** | An HTTPS URL where the registered service lives |
| **Search** | Find registrations that overlap a location + range |
| **Referral** | A pointer to another MRS server that may have additional results |
| **Identity** | `username@server-domain` (e.g., `alice@owen.iz.net`) |
| **FOAD** | "Fade Out And Disappear" — hides a registration from search results |

## Authentication

MRS uses bearer tokens. Most read operations (search, discovery) require **no authentication**. Write operations (register, update, release) require a token.

### Get a Token

**Register a new account** (one-time):
```
POST https://owen.iz.net/auth/register
Content-Type: application/json

{"username": "<chosen_name>", "password": "<8+ chars>", "email": "<email>"}
```
Response: `{"token": "<bearer_token>", "expires_at": "<datetime|null>"}`

**Login** (if you already have an account):
```
POST https://owen.iz.net/auth/login
Content-Type: application/json

{"username": "<name>", "password": "<password>"}
```
Response: `{"token": "<bearer_token>", "expires_at": "<datetime|null>"}`

**Using the token:** Include `Authorization: Bearer <token>` on all authenticated requests.

Tokens expire after 1 week by default. If you get a `401`, login again to get a fresh token.

### Check Current Identity

```
GET https://owen.iz.net/auth/me
Authorization: Bearer <token>
```
Response: `{"id": "username@owen.iz.net", "created_at": "...", "is_local": true}`

---

## API Reference

### Search for Nearby Services

**No authentication required.**

```
POST https://owen.iz.net/search
Content-Type: application/json

{
  "location": {"lat": <float>, "lon": <float>, "ele": <float>},
  "range": <meters>
}
```

| Parameter | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `location.lat` | float | -90 to 90 | Latitude in decimal degrees |
| `location.lon` | float | -180 to 180 | Longitude in decimal degrees |
| `location.ele` | float | any (default 0) | Elevation in meters above sea level |
| `range` | float | >0, ≤1,000,000 | Search radius in meters |

**Response:**
```json
{
  "status": "ok",
  "results": [
    {
      "id": "reg_abc123def456",
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
      "origin_id": "reg_abc123def456",
      "version": 1,
      "created": "2025-01-15T10:30:00Z",
      "updated": "2025-01-15T10:30:00Z"
    }
  ],
  "referrals": [
    {"server": "https://other-mrs.example.com", "hint": "Asia-Pacific region"}
  ]
}
```

**Agent guidance:**
- Results are sorted smallest-sphere-first, then by distance. The first result is usually the most specific/relevant.
- `distance` is in meters from the query point to the registration's center.
- `referrals` point to other MRS servers that may have additional results for the searched area. Follow referrals if the user needs comprehensive coverage.
- `service_point` is the URL to visit to actually use the registered service.
- Registrations with `foad: true` are never returned in search results.

---

### Register a Service at a Location

**Authentication required.**

```
POST https://owen.iz.net/register
Content-Type: application/json
Authorization: Bearer <token>

{
  "space": {
    "type": "sphere",
    "center": {"lat": <float>, "lon": <float>, "ele": <float>},
    "radius": <meters>
  },
  "service_point": "<https_url>",
  "foad": false
}
```

| Parameter | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `space.type` | string | Must be `"sphere"` | Geometry type (only spheres supported currently) |
| `space.center.lat` | float | -90 to 90 | Latitude |
| `space.center.lon` | float | -180 to 180 | Longitude |
| `space.center.ele` | float | any (default 0) | Elevation in meters |
| `space.radius` | float | >0, ≤1,000,000 | Radius in meters |
| `service_point` | string | Valid HTTPS URL | Where the service lives (required unless foad=true) |
| `foad` | boolean | default false | If true, registration is hidden from searches |

**Response (201):**
```json
{
  "status": "registered",
  "registration": {
    "id": "reg_abc123def456",
    "space": { ... },
    "service_point": "https://...",
    "owner": "you@owen.iz.net",
    "version": 1,
    "created": "...",
    "updated": "..."
  }
}
```

**Agent guidance:**
- `service_point` must be `https://` — HTTP is rejected. It must not contain fragments (`#`), credentials, or whitespace.
- Choose `radius` to match the real-world footprint: ~50m for a building, ~500m for a city block, ~5000m for a neighborhood.
- Save the returned `id` — you'll need it to update or release the registration later.
- Set `foad: true` only when the user wants to claim a space without being discoverable.

---

### Update a Registration

**Authentication required. You must own the registration.**

```
PUT https://owen.iz.net/register/<registration_id>
Content-Type: application/json
Authorization: Bearer <token>

{
  "space": {
    "type": "sphere",
    "center": {"lat": <float>, "lon": <float>, "ele": <float>},
    "radius": <meters>
  },
  "service_point": "<https_url>",
  "foad": false
}
```

Response (200): Same shape as register, with incremented `version`.

**Errors:** 403 if you don't own it, 404 if not found, 409 if the registration originated on another server (federated).

---

### Release (Delete) a Registration

**Authentication required. You must own the registration.**

```
POST https://owen.iz.net/release
Content-Type: application/json
Authorization: Bearer <token>

{"id": "<registration_id>"}
```

Response (200): `{"status": "released", "id": "reg_..."}`

---

### List Your Registrations

**Authentication required.**

```
GET https://owen.iz.net/auth/me/registrations
Authorization: Bearer <token>
```

Response: `{"registrations": [...]}`

---

### Server Discovery

**No authentication required.**

```
GET https://owen.iz.net/.well-known/mrs
```

Response:
```json
{
  "mrs_version": "0.2.0",
  "server": "https://owen.iz.net",
  "operator": "admin@owen.iz.net",
  "authoritative_regions": [],
  "known_peers": [{"server": "https://...", "hint": "..."}],
  "capabilities": {"geometry_types": ["sphere"], "max_radius": 1000000}
}
```

**Agent guidance:** Call this endpoint first to verify the server is reachable and to learn its capabilities and known peers.

---

### Public Key Retrieval

**No authentication required.**

```
GET https://owen.iz.net/.well-known/mrs/keys/<identity>
```

Where `<identity>` is a username (local user), `_server` (the server's own key), or a full `user@domain` identity.

Response: `{"id": "...", "public_key": {"type": "Ed25519", "key": "<base64>"}, "created": "..."}`

---

## Error Handling

All errors return JSON with a `detail` field:

| Status | Meaning | What to Do |
|--------|---------|------------|
| 400 | Bad request (invalid data, limits exceeded) | Check field values and constraints |
| 401 | Missing or expired token | Login again to get a fresh token |
| 403 | Not the owner / email not whitelisted | You can only modify your own registrations |
| 404 | Registration not found | Verify the ID |
| 409 | Conflict (federated registration) | Can only modify registrations on their origin server |
| 422 | Validation error | Check required fields and formats |

---

## Common Agent Workflows

### Workflow 1: "What's near me?"

```
1. POST /search with the user's location and a reasonable range (start with 1000m)
2. Present the results — service_point URLs, distances, owner info
3. If referrals are returned and the user wants more results, search those servers too
4. If no results, widen the range (try 5000m, then 10000m)
```

### Workflow 2: "Register my service at this location"

```
1. If you don't have a token: POST /auth/register or POST /auth/login
2. POST /register with the location, radius, and service_point URL
3. Save the returned registration ID for future updates/deletion
4. Confirm to the user: "Registered at [lat, lon] with radius [X]m, ID: [id]"
```

### Workflow 3: "Update my registration"

```
1. GET /auth/me/registrations to find the registration ID
2. PUT /register/<id> with the updated fields
3. Confirm the update and new version number
```

### Workflow 4: "Remove my registration"

```
1. GET /auth/me/registrations to find the registration ID
2. POST /release with the ID
3. Confirm deletion
```

### Workflow 5: "Explore the MRS network"

```
1. GET /.well-known/mrs to see server info and peers
2. Search known_peers to discover the federation topology
3. POST /search at each peer to find registrations across the network
```

---

## Practical Notes for Agents

- **Coordinate format:** Decimal degrees. Sydney Opera House is `lat: -33.8568, lon: 151.2153`. Negative lat = south, negative lon = west.
- **Radius intuition:** 10m ≈ a room, 50m ≈ a building, 500m ≈ a few city blocks, 5000m ≈ a suburb, 50000m ≈ a metro area.
- **Elevation:** Usually 0 unless the user specifies altitude. Elevation is in meters above sea level.
- **Tokens are long-lived:** Default expiry is 1 week. Cache and reuse them rather than logging in repeatedly.
- **The server speaks only JSON.** All requests and responses use `Content-Type: application/json`.
- **CORS is open:** The API can be called from any origin, including browser-based agents.
- **No rate limiting is enforced by the server itself,** but be respectful — avoid tight polling loops.
- **Registration ownership is permanent:** Only the creating user can update or delete a registration.
- **Federated registrations are read-only:** If a registration's `origin_server` differs from the server you're querying, you can view it but not modify it. Go to the origin server to make changes.

---

## Quick Reference Card

| Action | Method | Path | Auth |
|--------|--------|------|------|
| Search nearby | POST | `/search` | No |
| Register space | POST | `/register` | Yes |
| Update space | PUT | `/register/{id}` | Yes |
| Release space | POST | `/release` | Yes |
| Create account | POST | `/auth/register` | No |
| Login | POST | `/auth/login` | No |
| Who am I? | GET | `/auth/me` | Yes |
| My registrations | GET | `/auth/me/registrations` | Yes |
| Server info | GET | `/.well-known/mrs` | No |
| Public keys | GET | `/.well-known/mrs/keys/{id}` | No |
