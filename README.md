# MRS Server

**Mixed Reality Service** - A federated spatial registry protocol

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Overview

MRS (Mixed Reality Service) is a federated protocol for registering and discovering services associated with physical locations. Think of it as "DNS for physical space" - it allows agents, applications, and devices to query what services or metadata are associated with any geographic location.

Key features:
- **Spatial Registration**: Register services at specific geographic locations (spheres)
- **Federated Architecture**: Servers can peer with each other and refer queries
- **Identity Federation**: Users can authenticate across servers using cryptographic signatures
- **Privacy Controls**: The `foad` (Fade Out And Disappear) flag hides registrations from searches

## Quick Start

### 90-Second Setup

```bash
git clone https://github.com/mpesce/mrs-server.git
cd mrs-server
./scripts/bootstrap.sh
./scripts/verify.sh
```

For a short walkthrough, see [QUICKSTART.md](QUICKSTART.md).

### Installation (manual)

```bash
# Clone the repository
git clone https://github.com/mpesce/mrs-server.git
cd mrs-server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Initialize database
python scripts/init_db.py

# Run the server
python -m mrs_server.main
```

The server will start at `http://localhost:8000`. Visit `http://localhost:8000/docs` for interactive API documentation.

### Command Line Options

```bash
# Run on a specific port
python -m mrs_server.main --port 9000

# Run on a specific host and port
python -m mrs_server.main --host 127.0.0.1 --port 9000

# Enable auto-reload for development
python -m mrs_server.main --reload
```

### Configuration

Configure via environment variables (prefix `MRS_`):

> Production note: terminate TLS at a reverse proxy (Apache/Caddy/Nginx) and keep `mrs-server` on `127.0.0.1:8000`. See [`docs/TLS_DEPLOYMENT.md`](docs/TLS_DEPLOYMENT.md).

```bash
# Server identity
export MRS_SERVER_URL="https://your-domain.com"
export MRS_SERVER_DOMAIN="your-domain.com"
export MRS_ADMIN_EMAIL="admin@your-domain.com"

# Network
export MRS_HOST="0.0.0.0"
export MRS_PORT="8000"

# Database
export MRS_DATABASE_PATH="./mrs.db"

# Optional: Federation peers
export MRS_BOOTSTRAP_PEERS='["https://peer1.example.com", "https://peer2.example.com"]'
```

Or create a `.env` file in the project root. Command line arguments override environment variables.

## API Usage

### Authentication

First, create an account and get a token:

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secretpassword"}'

# Login (returns bearer token)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secretpassword"}'
```

### Register a Space

`service_point` is strictly validated for safety. It must be a well-formed `https://` URI and must not include credentials, fragments, control characters, or whitespace.


```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "space": {
      "type": "sphere",
      "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
      "radius": 50
    },
    "service_point": "https://example.com/sydney-opera-house"
  }'
```

### Search for Nearby Services

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "location": {"lat": -33.8570, "lon": 151.2155, "ele": 0},
    "range": 100
  }'
```

### Release a Registration

```bash
curl -X POST http://localhost:8000/release \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"id": "reg_abc123..."}'
```

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/register` | Required | Register a new space |
| POST | `/release` | Required | Release a registration |
| POST | `/search` | None | Search for nearby registrations |
| GET | `/.well-known/mrs` | None | Server metadata |
| GET | `/.well-known/mrs/keys/{identity}` | None | Public key for identity |
| POST | `/auth/register` | None | Create user account |
| POST | `/auth/login` | None | Get bearer token |
| GET | `/auth/me` | Required | Current user info |

## Project Structure

```
mrs-server/
├── mrs_server/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── database.py          # SQLite setup
│   ├── models.py            # Pydantic models
│   ├── api/                  # API endpoints
│   │   ├── register.py
│   │   ├── release.py
│   │   ├── search.py
│   │   ├── wellknown.py
│   │   └── auth.py
│   ├── auth/                 # Authentication
│   │   ├── bearer.py
│   │   ├── keys.py
│   │   └── dependencies.py
│   ├── federation/           # Federation
│   │   ├── peers.py
│   │   └── referrals.py
│   └── geo/                  # Geometry utilities
│       ├── distance.py
│       ├── bbox.py
│       └── intersect.py
├── tests/
├── scripts/
└── docs/
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mrs_server

# Run specific test file
pytest tests/test_api.py -v
```

### Code Style

```bash
# Format code
ruff format .

# Lint
ruff check .
```

## Federation

MRS servers can federate with each other:

1. **Bootstrap Peers**: Configure trusted peers in `MRS_BOOTSTRAP_PEERS`
2. **Referrals**: Search responses include referrals to other servers that may have relevant data
3. **Identity Federation**: Users from federated servers can authenticate using HTTP signatures (planned)

### Adding a Federation Peer

```python
# Via the API (admin)
POST /admin/peers
{"server_url": "https://sydney.mrs.example", "hint": "Sydney region"}

# Or via configuration
MRS_BOOTSTRAP_PEERS='["https://sydney.mrs.example"]'
```

## Roadmap

- [ ] HTTP Signature authentication (RFC 9421)
- [ ] Polygon geometry support
- [ ] Real-time updates via WebSocket
- [ ] PostgreSQL/PostGIS backend option
- [ ] Admin dashboard

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits

Developed by Mark Pesce. Inspired by the need for agents to understand and interact with physical space.
