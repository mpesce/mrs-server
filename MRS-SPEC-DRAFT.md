# Mixed Reality Service (MRS) Protocol Specification

**Version:** 0.5.0-draft
**Date:** January 2026
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

**Authoritative Server:** A server that holds the canonical registration for a given Space.

**Referral:** A hint from one server pointing to another server that may have relevant registrations.

**Client:** Any system that queries MRS—typically an AI agent or autonomous device.

**FOAD Flag:** "Forbidden/Off-limits And Declared" — a privacy marker indicating a Space is registered but explicitly provides no services.

---

## 3. Data Model

### 3.1 Coordinates

MRS uses the WGS 84 coordinate system (the standard for GPS).

| Field | Type | Description |
|-------|------|-------------|
| `lat` | float | Latitude in degrees. Range: -90.0 to 90.0 |
| `lon` | float | Longitude in degrees. Range: -180.0 to 180.0 |
| `ele` | float | Elevation in meters above sea level. Negative values for below sea level. |

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
  "created": "2026-01-15T10:30:00Z",
  "updated": "2026-01-15T10:30:00Z"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier for this registration |
| `space` | object | Yes | Geometry defining the bounded volume |
| `service_point` | URI | No* | URI for services/metadata at this space |
| `foad` | boolean | Yes | If true, space is registered but provides no services |
| `owner` | string | Yes | Domain-based identity of the registrant |
| `created` | ISO 8601 | Yes | Timestamp of initial registration |
| `updated` | ISO 8601 | Yes | Timestamp of last modification |

*`service_point` is REQUIRED if `foad` is false. If `foad` is true, `service_point` SHOULD be omitted.

---

## 4. Protocol Operations

All operations use HTTPS. Request and response bodies are JSON with Content-Type `application/json`.

### 4.1 Register

Creates or updates a Registration.

**Request:** `POST /register`

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
    "space": { ... },
    "service_point": "https://example.com/spaces/my-space",
    "foad": false,
    "owner": "user@example.com",
    "created": "2026-01-26T08:30:00Z",
    "updated": "2026-01-26T08:30:00Z"
  }
}
```

**Response (error):** `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`

```json
{
  "status": "error",
  "error": "invalid_geometry",
  "message": "Radius must be positive and less than 1,000,000 meters"
}
```

**Authentication:** Required. See Section 6.

### 4.2 Release

Removes a Registration.

**Request:** `POST /release`

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

**Response (error):** `401 Unauthorized`, `403 Forbidden`, `404 Not Found`

**Authentication:** Required. Only the owner of a registration may release it.

### 4.3 Search

Queries for Registrations intersecting a location or volume.

**Request:** `POST /search`

```json
{
  "location": { "lat": -33.85939, "lon": 151.20458, "ele": 10.0 },
  "range": 100.0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `location` | object | Yes | Center point for search |
| `range` | float | No | Search radius in meters. Default: 0 (exact point) |

**Response:** `200 OK`

```json
{
  "status": "ok",
  "results": [
    {
      "id": "reg_a1b2c3d4e5f6",
      "space": { ... },
      "service_point": "https://example.com/spaces/my-space",
      "foad": false,
      "distance": 12.5
    },
    {
      "id": "reg_x9y8z7w6v5u4",
      "space": { ... },
      "foad": true,
      "distance": 45.0
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

**Result Ordering:** Results are ordered by specificity: smallest bounding volume first (inside-out). For equal volumes, order by distance from query location (nearest first).

**Referrals:** If the server is not authoritative for the queried location, or knows of other servers that may have additional registrations, it SHOULD include referrals. See Section 5.

**Authentication:** Not required for search.

### 4.4 Server Metadata

Returns information about the server and its authoritative regions.

**Request:** `GET /.well-known/mrs`

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
    },
    {
      "server": "https://global.mrs.example.net",
      "hint": "Global fallback server"
    }
  ],
  "capabilities": {
    "geometry_types": ["sphere", "polygon"],
    "max_radius": 1000000
  }
}
```

---

## 5. Federation Model

MRS operates as a federated network of servers. There is no central authority or root server.

### 5.1 Authority

A server is **authoritative** for a Space if it holds the canonical Registration for that Space. A server declares its authoritative regions in its metadata (see 4.4).

Multiple servers may hold registrations for overlapping spaces. This is expected and valid—a city government's server might register municipal boundaries while individual property owners register their buildings.

### 5.2 Discovery via Referral

When a server receives a search query:

1. It returns all matching Registrations it holds authoritatively.
2. It includes referrals to other servers that may have relevant registrations.

Referrals are hints, not guarantees. A referred server may or may not have additional results.

### 5.3 Client-Side Resolution

The MRS client library is responsible for:

1. Issuing the initial search query
2. Following referrals (up to a configured depth limit)
3. Deduplicating results (by registration ID)
4. Detecting cycles (do not re-query servers already visited)
5. Aggregating and sorting final results

This keeps servers simple and stateless while enabling comprehensive discovery.

### 5.4 Peer Discovery

Servers discover peers through:

- **Manual configuration:** Operators configure known peers
- **Referral accumulation:** Servers learn about peers from referrals received during queries
- **Well-known registries:** Community-maintained lists of public MRS servers (out of scope for this specification)

### 5.5 Consistency Model

MRS uses eventual consistency. When a Registration is created or modified:

1. The authoritative server updates immediately
2. Other servers learn of the change when they next query or receive a referral

There is no global synchronization. Clients should treat results as best-effort snapshots.

---

## 6. Identity and Authentication

### 6.1 Domain-Based Identity

MRS uses domain-based identity, similar to email addresses:

```
username@domain.example
```

The domain portion identifies a server or organization. The username identifies an account within that domain.

Every MRS identity has an associated public key, published at a well-known location:

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

MRS supports two authentication methods. Servers MUST implement both.

#### 6.2.1 Bearer Token (Local Authentication)

For clients authenticating to their home server, Bearer tokens provide a simple mechanism:

```
Authorization: Bearer <token>
```

Token issuance, format, and validation are server-specific. Servers MAY use JWTs, opaque tokens, OAuth integration, or any other mechanism.

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

### 6.3 Server-to-Server Authentication

When servers communicate (e.g., during peer discovery or future synchronization), they MUST use HTTP Signatures.

A server's identity is its domain with no username portion:

```
@mrs.example.com
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

### 7.2 Privacy

Search queries reveal the querying client's location of interest. Servers:

- MUST NOT log query locations beyond what is necessary for operation
- SHOULD NOT share query patterns with third parties
- MAY implement rate limiting to prevent location tracking attacks

### 7.3 Abuse Prevention

The FOAD flag allows space owners to register without providing services—useful for declaring "do not enter" or "do not photograph" zones. However, MRS cannot enforce these declarations. Enforcement is the responsibility of consuming applications.

### 7.4 Verification of Ownership

This specification does not define how ownership of physical space is verified. This is intentionally left as a social and legal problem, not a technical one.

Servers MAY implement their own verification requirements. Possible approaches include:

- Self-attestation (trust-based)
- Integration with land registries
- Physical verification processes
- Reputation systems

Interoperability does not require agreement on verification methods.

---

## 8. Future Work

### 8.1 MRSE: Service Enumeration

A future specification will define MRSE (Mixed Reality Service Enumeration)—a standard for what service points return. This may include:

- Permission schemas (overflight allowed, photography prohibited, etc.)
- Metadata formats (hours of operation, contact information, hazard warnings)
- Capability negotiation

### 8.2 Dynamic Spaces

The current specification addresses static spaces (land, buildings). A companion protocol for dynamic spaces (vehicles, temporary zones) may be developed.

### 8.3 Verification Protocols

Community protocols for ownership verification may emerge. These will be documented separately as best practices rather than specification requirements.

---

## 9. IANA Considerations

This specification requests registration of:

- `/.well-known/mrs` — MRS server metadata endpoint
- `/.well-known/mrs/keys/{identity}` — Public key endpoint for MRS identities
- `MRS-Identity` — HTTP header for MRS identity in signed requests

---

## 10. References

- RFC 3986: Uniform Resource Identifier (URI): Generic Syntax
- RFC 9421: HTTP Message Signatures
- WGS 84: World Geodetic System 1984

---

## Appendix A: Example Client Session

```python
# Pseudocode for MRS client library

def search(location, range=0, max_depth=3):
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
        queue.extend(response.referrals)

    # Deduplicate by registration ID
    unique = {r.id: r for r in results}

    # Sort by volume (smallest first), then distance
    return sorted(unique.values(), key=lambda r: (r.space.volume, r.distance))
```

---

## Appendix B: Revision History

| Version | Date | Changes |
|---------|------|---------|
| 0.5.0-draft | 2026-01 | Initial working draft |

---

## Acknowledgements

The author thanks Tony Parisi, Owen Rowley, Peter Kennard, and Sir Tim Berners-Lee for their contributions to the ideas underlying this specification over three decades of development.
