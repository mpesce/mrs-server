# MRS Server Implementation Specification

**Version:** 0.5.0-draft
**Date:** January 2026
**Purpose:** Implementation guide for MRS server developers

---

## 1. Overview

This document specifies how to implement an MRS server. The reference implementation is in Python using FastAPI and SQLite, designed for clarity and ease of modification. Production deployments may port to other languages/databases while maintaining protocol compatibility.

The canonical server will run at `owen.iz.net` and serves as the default bootstrap node for the MRS federation.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      MRS Server                         │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   HTTP API  │  │   Auth      │  │   Federation    │  │
│  │   (FastAPI) │  │   Module    │  │   Module        │  │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │
│         │                │                   │          │
│         └────────────────┼───────────────────┘          │
│                          │                              │
│                   ┌──────┴──────┐                       │
│                   │   Storage   │                       │
│                   │   (SQLite)  │                       │
│                   └─────────────┘                       │
└─────────────────────────────────────────────────────────┘
```

### 2.1 Components

| Component | Responsibility |
|-----------|----------------|
| HTTP API | Request routing, JSON serialization, error handling |
| Auth Module | Bearer token validation, HTTP signature verification, key management |
| Federation Module | Peer tracking, referral generation, peer discovery |
| Storage | Registrations, users, keys, known peers |

---

## 3. Database Schema

SQLite database with the following tables:

### 3.1 registrations

```sql
CREATE TABLE registrations (
    id TEXT PRIMARY KEY,                    -- "reg_" + 12 random alphanumeric
    owner TEXT NOT NULL,                    -- MRS identity (user@domain)

    -- Geometry (sphere)
    geo_type TEXT NOT NULL DEFAULT 'sphere', -- 'sphere' or 'polygon'
    center_lat REAL NOT NULL,
    center_lon REAL NOT NULL,
    center_ele REAL NOT NULL DEFAULT 0,
    radius REAL,                            -- meters, for sphere type

    -- Geometry (polygon) - stored as JSON if geo_type='polygon'
    polygon_data TEXT,                      -- JSON: {"vertices": [...], "height": ...}

    -- Service
    service_point TEXT,                     -- URI, null if foad=true
    foad INTEGER NOT NULL DEFAULT 0,        -- boolean: 1=true, 0=false

    -- Metadata
    created_at TEXT NOT NULL,               -- ISO 8601
    updated_at TEXT NOT NULL,               -- ISO 8601

    -- Spatial index helpers (precomputed bounding box)
    bbox_min_lat REAL NOT NULL,
    bbox_max_lat REAL NOT NULL,
    bbox_min_lon REAL NOT NULL,
    bbox_max_lon REAL NOT NULL
);

CREATE INDEX idx_registrations_bbox ON registrations(
    bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon
);
CREATE INDEX idx_registrations_owner ON registrations(owner);
```

### 3.2 users

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,                    -- MRS identity (user@domain)
    password_hash TEXT,                     -- bcrypt hash, for local users
    created_at TEXT NOT NULL,

    -- For local users only
    is_local INTEGER NOT NULL DEFAULT 0     -- 1 if this server manages this identity
);

CREATE INDEX idx_users_local ON users(is_local);
```

### 3.3 keys

```sql
CREATE TABLE keys (
    id TEXT PRIMARY KEY,                    -- "key_" + random id
    owner TEXT NOT NULL,                    -- MRS identity or "_server" for server key
    key_id TEXT NOT NULL,                   -- human-readable key identifier
    algorithm TEXT NOT NULL DEFAULT 'Ed25519',
    public_key TEXT NOT NULL,               -- base64-encoded
    private_key TEXT,                       -- base64-encoded, only for local identities
    created_at TEXT NOT NULL,
    expires_at TEXT,
    deprecated INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (owner) REFERENCES users(id),
    UNIQUE(owner, key_id)
);

CREATE INDEX idx_keys_owner ON keys(owner);
```

### 3.4 tokens

```sql
CREATE TABLE tokens (
    token TEXT PRIMARY KEY,                 -- random bearer token
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT,

    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_tokens_user ON tokens(user_id);
```

### 3.5 peers

```sql
CREATE TABLE peers (
    server_url TEXT PRIMARY KEY,            -- e.g., "https://sydney.mrs.example"
    hint TEXT,                              -- human-readable description
    last_seen TEXT,                         -- ISO 8601, when we last got a referral
    is_configured INTEGER NOT NULL DEFAULT 0, -- 1 if manually configured

    -- Optional: regions this peer claims authority over (JSON)
    authoritative_regions TEXT              -- JSON array of geometry objects
);
```

### 3.6 server_config

```sql
CREATE TABLE server_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Required entries:
-- 'server_url': "https://owen.iz.net"
-- 'server_domain': "owen.iz.net"
-- 'admin_email': "admin@owen.iz.net"
```

---

## 4. API Endpoints

Base URL: `https://{server_domain}`

### 4.1 Protocol Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/register` | Required | Create/update registration |
| POST | `/release` | Required | Delete registration |
| POST | `/search` | None | Query registrations |
| GET | `/.well-known/mrs` | None | Server metadata |
| GET | `/.well-known/mrs/keys/{identity}` | None | Public key for identity |

### 4.2 Management Endpoints (Optional)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | None | Create local user account |
| POST | `/auth/login` | None | Get bearer token |
| GET | `/auth/me` | Required | Get current user info |
| GET | `/registrations` | Required | List user's registrations |
| POST | `/admin/peers` | Admin | Add/remove configured peers |

---

## 5. Endpoint Specifications

### 5.1 POST /register

**Request:**

```json
{
  "space": {
    "type": "sphere",
    "center": { "lat": -33.85939, "lon": 151.20458, "ele": 10.0 },
    "radius": 50.0
  },
  "service_point": "https://example.com/my-space",
  "foad": false
}
```

**Processing:**

1. Authenticate request (Bearer or HTTP Signature)
2. Validate geometry:
   - `lat` in range [-90, 90]
   - `lon` in range [-180, 180]
   - `radius` > 0 and <= 1,000,000
   - If polygon: minimum 3 vertices, valid coordinates
3. Validate `service_point` is well-formed URI (if `foad` is false)
4. Compute bounding box for spatial indexing
5. Generate registration ID: `"reg_" + secrets.token_urlsafe(9)`
6. Insert into database
7. Return registration object

**Response (201 Created):**

```json
{
  "status": "registered",
  "registration": {
    "id": "reg_a1b2c3d4e5f6",
    "space": { ... },
    "service_point": "https://example.com/my-space",
    "foad": false,
    "owner": "user@example.com",
    "created": "2026-01-26T08:30:00Z",
    "updated": "2026-01-26T08:30:00Z"
  }
}
```

**Errors:**

| Code | Condition |
|------|-----------|
| 400 | Invalid geometry, missing required fields |
| 401 | Missing or invalid authentication |
| 403 | Not authorized (e.g., updating someone else's registration) |

### 5.2 POST /release

**Request:**

```json
{
  "id": "reg_a1b2c3d4e5f6"
}
```

**Processing:**

1. Authenticate request
2. Look up registration by ID
3. Verify requester is owner
4. Delete from database

**Response (200 OK):**

```json
{
  "status": "released",
  "id": "reg_a1b2c3d4e5f6"
}
```

**Errors:**

| Code | Condition |
|------|-----------|
| 401 | Missing or invalid authentication |
| 403 | Requester is not owner |
| 404 | Registration not found |

### 5.3 POST /search

**Request:**

```json
{
  "location": { "lat": -33.85939, "lon": 151.20458, "ele": 10.0 },
  "range": 100.0
}
```

**Processing:**

1. Validate coordinates
2. Compute search bounding box from location + range
3. Query registrations with overlapping bounding boxes
4. Filter by actual geometry intersection (sphere or polygon)
5. Compute distance from query point to each result
6. Sort by volume (smallest first), then distance
7. Generate referrals from known peers
8. Return results and referrals

**Spatial Query (SQL):**

```sql
SELECT * FROM registrations
WHERE bbox_max_lat >= :search_min_lat
  AND bbox_min_lat <= :search_max_lat
  AND bbox_max_lon >= :search_min_lon
  AND bbox_min_lon <= :search_max_lon
```

Then filter in application code for precise intersection.

**Referral Generation:**

```python
def generate_referrals(location, range, results):
    referrals = []
    for peer in get_known_peers():
        # Include peer if:
        # 1. Peer claims authority over a region that intersects the search
        # 2. OR peer is a configured bootstrap peer
        # 3. AND peer hasn't been seen returning results for this area
        if should_refer(peer, location, range):
            referrals.append({
                "server": peer.server_url,
                "hint": peer.hint
            })
    return referrals
```

**Response (200 OK):**

```json
{
  "status": "ok",
  "results": [
    {
      "id": "reg_a1b2c3d4e5f6",
      "space": { ... },
      "service_point": "https://example.com/my-space",
      "foad": false,
      "distance": 12.5
    }
  ],
  "referrals": [
    {
      "server": "https://sydney.mrs.example",
      "hint": "Authoritative for Sydney metropolitan area"
    }
  ]
}
```

### 5.4 GET /.well-known/mrs

**Response:**

```json
{
  "mrs_version": "0.5.0",
  "server": "https://owen.iz.net",
  "operator": "admin@owen.iz.net",
  "authoritative_regions": [],
  "known_peers": [
    {
      "server": "https://sydney.mrs.example",
      "hint": "Sydney metropolitan area"
    }
  ],
  "capabilities": {
    "geometry_types": ["sphere"],
    "max_radius": 1000000
  }
}
```

### 5.5 GET /.well-known/mrs/keys/{identity}

**Path Parameters:**

- `identity`: Either a username (for `user@this-server`) or `_server` for server key

**Response (single key):**

```json
{
  "id": "mark@owen.iz.net",
  "public_key": {
    "type": "Ed25519",
    "key": "base64-encoded-public-key"
  },
  "created": "2026-01-15T10:30:00Z"
}
```

**Response (multiple keys):**

```json
{
  "id": "mark@owen.iz.net",
  "keys": [
    {
      "key_id": "key-2026-01",
      "type": "Ed25519",
      "key": "base64-encoded-public-key",
      "created": "2026-01-01T00:00:00Z",
      "expires": "2027-01-01T00:00:00Z"
    }
  ]
}
```

---

## 6. Authentication Implementation

### 6.1 Bearer Token Validation

```python
async def validate_bearer_token(token: str) -> User:
    row = db.execute(
        "SELECT user_id, expires_at FROM tokens WHERE token = ?",
        [token]
    ).fetchone()

    if not row:
        raise AuthError("Invalid token")

    if row['expires_at'] and datetime.fromisoformat(row['expires_at']) < datetime.utcnow():
        raise AuthError("Token expired")

    return get_user(row['user_id'])
```

### 6.2 HTTP Signature Verification

```python
async def verify_http_signature(request: Request) -> User:
    # 1. Extract headers
    sig_input = request.headers.get('Signature-Input')
    signature = request.headers.get('Signature')
    mrs_identity = request.headers.get('MRS-Identity')
    content_digest = request.headers.get('Content-Digest')

    if not all([sig_input, signature, mrs_identity]):
        raise AuthError("Missing signature headers")

    # 2. Parse Signature-Input to get keyid and algorithm
    params = parse_signature_input(sig_input)
    key_url = params['keyid']
    algorithm = params['alg']

    # 3. Verify key URL domain matches identity domain
    identity_domain = mrs_identity.split('@')[1]
    key_domain = urlparse(key_url).netloc
    if identity_domain != key_domain:
        raise AuthError("Key domain mismatch")

    # 4. Fetch public key (with caching)
    public_key = await fetch_public_key(key_url)

    # 5. Reconstruct signed data
    signed_components = extract_signed_components(request, params)

    # 6. Verify signature
    if not verify_signature(signed_components, signature, public_key, algorithm):
        raise AuthError("Invalid signature")

    # 7. Verify content digest if present
    if content_digest:
        body = await request.body()
        if not verify_content_digest(body, content_digest):
            raise AuthError("Content digest mismatch")

    return User(id=mrs_identity, is_local=False)
```

### 6.3 Key Caching

```python
class KeyCache:
    def __init__(self, ttl_seconds=3600):
        self.cache = {}  # key_url -> (public_key, expires_at)
        self.ttl = ttl_seconds

    async def get(self, key_url: str) -> bytes:
        if key_url in self.cache:
            key, expires = self.cache[key_url]
            if datetime.utcnow() < expires:
                return key

        # Fetch fresh
        key = await self._fetch_key(key_url)
        self.cache[key_url] = (key, datetime.utcnow() + timedelta(seconds=self.ttl))
        return key

    async def _fetch_key(self, key_url: str) -> bytes:
        async with httpx.AsyncClient() as client:
            resp = await client.get(key_url)
            resp.raise_for_status()
            data = resp.json()

            # Handle single key or multiple keys format
            if 'public_key' in data:
                return base64.b64decode(data['public_key']['key'])
            elif 'keys' in data:
                # Find non-deprecated, non-expired key
                for k in data['keys']:
                    if k.get('deprecated'):
                        continue
                    if k.get('expires') and datetime.fromisoformat(k['expires']) < datetime.utcnow():
                        continue
                    return base64.b64decode(k['key'])

            raise AuthError("No valid key found")
```

---

## 7. Federation Implementation

### 7.1 Peer Management

```python
def add_peer(server_url: str, hint: str = None, is_configured: bool = False):
    """Add or update a known peer."""
    db.execute("""
        INSERT INTO peers (server_url, hint, last_seen, is_configured)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(server_url) DO UPDATE SET
            hint = COALESCE(excluded.hint, hint),
            last_seen = excluded.last_seen,
            is_configured = MAX(is_configured, excluded.is_configured)
    """, [server_url, hint, datetime.utcnow().isoformat(), int(is_configured)])

def get_known_peers() -> List[Peer]:
    """Get all known peers, configured first."""
    rows = db.execute("""
        SELECT * FROM peers
        ORDER BY is_configured DESC, last_seen DESC
    """).fetchall()
    return [Peer(**row) for row in rows]

def learn_peer_from_referral(server_url: str, hint: str = None):
    """Called when we receive a referral pointing to a peer we didn't know."""
    add_peer(server_url, hint, is_configured=False)
```

### 7.2 Referral Logic

```python
def generate_referrals(location: Location, range: float) -> List[Referral]:
    """Generate referrals for a search query."""
    referrals = []
    peers = get_known_peers()

    for peer in peers:
        # Always include configured peers (they're explicitly trusted)
        if peer.is_configured:
            referrals.append(Referral(server=peer.server_url, hint=peer.hint))
            continue

        # Include learned peers if they claim authority over relevant region
        if peer.authoritative_regions:
            regions = json.loads(peer.authoritative_regions)
            for region in regions:
                if intersects(region, location, range):
                    referrals.append(Referral(server=peer.server_url, hint=peer.hint))
                    break

    return referrals
```

### 7.3 Learning from Peer Metadata

```python
async def refresh_peer_metadata(peer_url: str):
    """Fetch and store peer's authoritative regions."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{peer_url}/.well-known/mrs")
            resp.raise_for_status()
            data = resp.json()

            db.execute("""
                UPDATE peers
                SET authoritative_regions = ?,
                    hint = COALESCE(?, hint),
                    last_seen = ?
                WHERE server_url = ?
            """, [
                json.dumps(data.get('authoritative_regions', [])),
                data.get('operator'),
                datetime.utcnow().isoformat(),
                peer_url
            ])
    except Exception as e:
        logger.warning(f"Failed to refresh peer metadata for {peer_url}: {e}")
```

---

## 8. Geometry Utilities

### 8.1 Bounding Box Computation

```python
import math

EARTH_RADIUS_M = 6371000  # meters

def compute_bounding_box(geo_type: str, center: Location, radius: float = None,
                          vertices: List[Location] = None) -> BoundingBox:
    """Compute lat/lon bounding box for a geometry."""

    if geo_type == 'sphere':
        # Convert radius in meters to degrees (approximate)
        lat_delta = radius / EARTH_RADIUS_M * (180 / math.pi)
        lon_delta = lat_delta / math.cos(math.radians(center.lat))

        return BoundingBox(
            min_lat=center.lat - lat_delta,
            max_lat=center.lat + lat_delta,
            min_lon=center.lon - lon_delta,
            max_lon=center.lon + lon_delta
        )

    elif geo_type == 'polygon':
        lats = [v.lat for v in vertices]
        lons = [v.lon for v in vertices]
        return BoundingBox(
            min_lat=min(lats),
            max_lat=max(lats),
            min_lon=min(lons),
            max_lon=max(lons)
        )
```

### 8.2 Distance Calculation

```python
def haversine_distance(loc1: Location, loc2: Location) -> float:
    """Calculate distance in meters between two points."""
    lat1, lon1 = math.radians(loc1.lat), math.radians(loc1.lon)
    lat2, lon2 = math.radians(loc2.lat), math.radians(loc2.lon)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    return EARTH_RADIUS_M * c
```

### 8.3 Intersection Testing

```python
def sphere_contains_point(center: Location, radius: float, point: Location) -> bool:
    """Test if a point is inside a sphere."""
    distance = haversine_distance(center, point)
    return distance <= radius

def spheres_intersect(c1: Location, r1: float, c2: Location, r2: float) -> bool:
    """Test if two spheres intersect."""
    distance = haversine_distance(c1, c2)
    return distance <= (r1 + r2)
```

---

## 9. Project Structure

```
mrs-server/
├── README.md
├── requirements.txt
├── pyproject.toml
├── mrs_server/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, startup
│   ├── config.py            # Configuration management
│   ├── database.py          # SQLite setup, migrations
│   ├── models.py            # Pydantic models
│   ├── api/
│   │   ├── __init__.py
│   │   ├── register.py      # POST /register
│   │   ├── release.py       # POST /release
│   │   ├── search.py        # POST /search
│   │   ├── wellknown.py     # /.well-known/* endpoints
│   │   └── auth.py          # /auth/* endpoints
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── bearer.py        # Bearer token handling
│   │   ├── signatures.py    # HTTP signature verification
│   │   └── keys.py          # Key management, caching
│   ├── federation/
│   │   ├── __init__.py
│   │   ├── peers.py         # Peer management
│   │   └── referrals.py     # Referral generation
│   └── geo/
│       ├── __init__.py
│       ├── bbox.py          # Bounding box computation
│       ├── distance.py      # Haversine distance
│       └── intersect.py     # Geometry intersection
├── tests/
│   ├── test_api.py
│   ├── test_auth.py
│   ├── test_federation.py
│   └── test_geo.py
└── scripts/
    ├── init_db.py           # Initialize database
    └── add_peer.py          # Add configured peer
```

---

## 10. Configuration

Environment variables or config file:

```python
# config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Server identity
    server_url: str = "https://owen.iz.net"
    server_domain: str = "owen.iz.net"
    admin_email: str = "admin@owen.iz.net"

    # Database
    database_path: str = "./mrs.db"

    # Server options
    max_radius: float = 1_000_000  # meters
    max_results: int = 100

    # Federation
    bootstrap_peers: list[str] = []  # Manually configured peers

    # Auth
    token_expiry_hours: int = 24 * 7  # 1 week
    key_cache_ttl_seconds: int = 3600  # 1 hour

    class Config:
        env_prefix = "MRS_"
```

---

## 11. Startup Sequence

```python
# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_database()
    generate_server_key_if_missing()
    load_configured_peers()

    yield

    # Shutdown
    close_database()

app = FastAPI(lifespan=lifespan)

def init_database():
    """Create tables if they don't exist."""
    # Run schema creation SQL

def generate_server_key_if_missing():
    """Generate Ed25519 keypair for server identity."""
    if not get_server_key():
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        store_server_key(private_key, public_key)

def load_configured_peers():
    """Add bootstrap peers from configuration."""
    for peer_url in settings.bootstrap_peers:
        add_peer(peer_url, is_configured=True)
```

---

## 12. Dependencies

```
# requirements.txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
httpx>=0.26.0
pydantic>=2.5.0
cryptography>=41.0.0
python-multipart>=0.0.6
```

---

## 13. Testing Strategy

### 13.1 Unit Tests

- Geometry calculations (bounding box, distance, intersection)
- Authentication (token validation, signature verification)
- Referral generation logic

### 13.2 Integration Tests

- Full API flows (register → search → release)
- Federation scenarios (referrals returned, peers learned)
- Authentication flows (local login, federated identity)

### 13.3 Test Fixtures

```python
# Predefined test registrations
TEST_SYDNEY_OPERA_HOUSE = {
    "space": {
        "type": "sphere",
        "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
        "radius": 100
    },
    "service_point": "https://example.com/sydney-opera-house"
}
```

---

## 14. Deployment Notes

### 14.1 Initial Deployment (owen.iz.net)

1. Set up HTTPS (Let's Encrypt or similar)
2. Configure environment variables
3. Initialize database: `python scripts/init_db.py`
4. Create admin user: `python scripts/create_user.py admin`
5. Start server: `uvicorn mrs_server.main:app --host 0.0.0.0 --port 443`

### 14.2 Adding a Federated Server

1. Deploy server with unique domain
2. Add `owen.iz.net` as bootstrap peer in config
3. Register with owen.iz.net (manual for now)
4. Begin accepting registrations

### 14.3 Future: Node.js Port

The Python implementation prioritizes clarity. For production scale:

- Port to Node.js/TypeScript with similar structure
- Replace SQLite with PostgreSQL + PostGIS for native spatial queries
- Add connection pooling, caching layer (Redis)
- Containerize with Docker

---

## Appendix A: Example Session

```bash
# Start server
$ uvicorn mrs_server.main:app --reload

# Create user and get token
$ curl -X POST http://localhost:8000/auth/register \
    -H "Content-Type: application/json" \
    -d '{"username": "mark", "password": "secret"}'

$ curl -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username": "mark", "password": "secret"}'
# Returns: {"token": "abc123..."}

# Register a space
$ curl -X POST http://localhost:8000/register \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer abc123..." \
    -d '{
      "space": {
        "type": "sphere",
        "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
        "radius": 50
      },
      "service_point": "https://example.com/my-place",
      "foad": false
    }'

# Search
$ curl -X POST http://localhost:8000/search \
    -H "Content-Type: application/json" \
    -d '{
      "location": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
      "range": 100
    }'
```
