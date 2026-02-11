# MRS Server Installation

This guide installs and runs `mrs-server` locally for development and early testing.

## Requirements
- Python 3.11+
- `pip`
- Linux/macOS/WSL (Windows works via PowerShell with equivalent commands)

## Quick install (recommended)

```bash
git clone https://github.com/mpesce/mrs-server.git
cd mrs-server

python3 -m venv .venv
source .venv/bin/activate

pip install -U pip
pip install -e ".[dev]"

python scripts/init_db.py
python -m mrs_server.main --host 127.0.0.1 --port 8000
```

Open:
- API docs: `http://127.0.0.1:8000/docs`
- Well-known metadata: `http://127.0.0.1:8000/.well-known/mrs`

## Configuration
Set env vars (optional):

```bash
export MRS_SERVER_URL="https://your-domain.example"
export MRS_SERVER_DOMAIN="your-domain.example"
export MRS_ADMIN_EMAIL="admin@your-domain.example"
export MRS_DATABASE_PATH="./mrs.db"
export MRS_HOST="127.0.0.1"
export MRS_PORT="8000"
```

## Test suite

```bash
source .venv/bin/activate
pytest -q
```

## Notes
- `service_point` URI validation is strict (HTTPS-only, no fragments/credentials/control chars).
- For local development, bind to `127.0.0.1` unless you intentionally want LAN exposure.
