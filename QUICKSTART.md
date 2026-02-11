# MRS Server Quickstart

From a fresh clone:

```bash
git clone https://github.com/mpesce/mrs-server.git
cd mrs-server

./scripts/bootstrap.sh
./scripts/verify.sh
```

Run server locally:

```bash
source .venv/bin/activate
python -m mrs_server.main --host 127.0.0.1 --port 8000
```

Check endpoints:
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/.well-known/mrs`

For production TLS deployments behind a reverse proxy, verify with:

```bash
./scripts/verify-tls.sh mrs.example.com https://mrs.example.com
```

Create a user/token:

```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"password123"}'
```
