# User Authentication & Authorisation

This document covers how user accounts work in MRS Server, including registration, login, token-based authentication, and the email whitelist system for controlling who can create accounts.

## Overview

MRS Server uses a simple bearer-token authentication model:

1. A user **registers** with a username, password, and email address
2. The server returns a **bearer token** (valid for 1 week by default)
3. The token is included in the `Authorization` header for protected requests
4. Users can **log in** again to get a fresh token at any time

User identities follow the format `username@server_domain` (e.g. `alice@mrs.example.com`).

## Registration

### Creating an Account

```bash
curl -X POST https://mrs.example.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "secretpassword",
    "email": "alice@example.com"
  }'
```

**Response (201 Created):**
```json
{
  "token": "abc123...",
  "expires_at": "2026-03-15T12:00:00+00:00"
}
```

### Field Requirements

| Field | Rules |
|-------|-------|
| `username` | 1-64 characters, alphanumeric plus `-` and `_` |
| `password` | 8-128 characters |
| `email` | Valid email address (normalised to lowercase) |

### What Can Go Wrong

| Status | Meaning |
|--------|---------|
| 201 | Account created, token returned |
| 400 | Username already taken |
| 403 | Email not in whitelist (when whitelist is enabled) |
| 422 | Validation error (bad email format, password too short, etc.) |

## Login

```bash
curl -X POST https://mrs.example.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secretpassword"}'
```

Returns a new bearer token. Login does not require an email — just the username and password used at registration.

## Using Your Token

Include the token in the `Authorization` header for any protected endpoint:

```bash
curl -X POST https://mrs.example.com/register \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{ ... }'
```

Tokens expire after 1 week by default (configurable via `MRS_TOKEN_EXPIRY_HOURS`). After expiry, log in again to get a new one.

## Current User Info

```bash
curl https://mrs.example.com/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "id": "alice@mrs.example.com",
  "created_at": "2026-03-08T10:00:00+00:00",
  "is_local": true
}
```

## Email Whitelist

The whitelist system lets server operators restrict who can register. When enabled, only email addresses that have been pre-approved can create accounts. Everyone else gets a `403 Forbidden`.

### Enabling the Whitelist

Set the environment variable before starting the server:

```bash
export MRS_REGISTRATION_REQUIRES_WHITELIST="true"
```

Or add it to your `.env` file:

```
MRS_REGISTRATION_REQUIRES_WHITELIST=true
```

When this is `false` (the default), anyone with a valid email can register. The email is still collected and stored, but no whitelist check is performed.

### Managing the Whitelist

Whitelist management is done via localhost-only admin endpoints. These endpoints **only accept connections from `127.0.0.1` or `::1`** — they cannot be reached from the network.

#### List All Whitelisted Emails

```bash
curl http://127.0.0.1:8000/admin/whitelist
```

**Response:**
```json
{
  "emails": [
    {"email": "alice@example.com", "added_at": "2026-03-08T10:00:00+00:00"},
    {"email": "bob@example.com", "added_at": "2026-03-08T10:05:00+00:00"}
  ]
}
```

#### Add a Single Email

```bash
curl -X POST http://127.0.0.1:8000/admin/whitelist \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com"}'
```

#### Add Multiple Emails at Once

```bash
curl -X POST http://127.0.0.1:8000/admin/whitelist \
  -H "Content-Type: application/json" \
  -d '{"emails": ["alice@example.com", "bob@example.com", "carol@example.com"]}'
```

**Response (201 Created):**
```json
{"status": "added", "added": 3}
```

Adding an email that's already in the whitelist is a no-op (no error, `added` count won't include it).

#### Remove an Email

```bash
curl -X DELETE http://127.0.0.1:8000/admin/whitelist/alice@example.com
```

**Response:**
```json
{"status": "removed", "email": "alice@example.com"}
```

Returns `404` if the email isn't in the whitelist. Removing a whitelisted email does **not** affect existing accounts — it only prevents new registrations with that email.

### How the Whitelist Check Works

1. User submits `POST /auth/register` with username, password, and email
2. The email is normalised to lowercase
3. If `MRS_REGISTRATION_REQUIRES_WHITELIST` is `true`, the server checks the `registration_whitelist` table
4. If the email is found, registration proceeds normally
5. If not found, the server returns `403` with `"Email address is not authorised to register"`

The check is case-insensitive — `Alice@Example.COM` matches a whitelist entry for `alice@example.com`.

### Typical Deployment Workflow

```bash
# 1. Enable whitelist enforcement
export MRS_REGISTRATION_REQUIRES_WHITELIST="true"

# 2. Start the server
python -m mrs_server.main &

# 3. Pre-approve your users (from the same machine)
curl -X POST http://127.0.0.1:8000/admin/whitelist \
  -H "Content-Type: application/json" \
  -d '{"emails": ["alice@example.com", "bob@example.com"]}'

# 4. Now alice and bob can register from anywhere
curl -X POST https://mrs.example.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secretpassword", "email": "alice@example.com"}'
# → 201 Created

# 5. Unapproved users cannot
curl -X POST https://mrs.example.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "mallory", "password": "secretpassword", "email": "mallory@evil.com"}'
# → 403 Forbidden
```

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `MRS_TOKEN_EXPIRY_HOURS` | `168` (1 week) | How long bearer tokens remain valid |
| `MRS_REGISTRATION_REQUIRES_WHITELIST` | `false` | Require email in whitelist to register |
| `MRS_KEY_CACHE_TTL_SECONDS` | `3600` | TTL for cached public keys (federation) |

## Database Tables

The auth system uses three tables:

**`users`** — registered accounts
| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | MRS identity (`user@domain`) |
| `password_hash` | TEXT | bcrypt hash |
| `email` | TEXT | Normalised email address |
| `created_at` | TEXT | ISO 8601 timestamp |
| `is_local` | INTEGER | 1 if managed by this server |

**`tokens`** — active bearer tokens
| Column | Type | Description |
|--------|------|-------------|
| `token` | TEXT PK | Random bearer token |
| `user_id` | TEXT FK | References `users.id` |
| `created_at` | TEXT | ISO 8601 timestamp |
| `expires_at` | TEXT | ISO 8601 expiry |

**`registration_whitelist`** — approved email addresses
| Column | Type | Description |
|--------|------|-------------|
| `email` | TEXT PK | Normalised lowercase email |
| `added_at` | TEXT | ISO 8601 timestamp |

## Security Notes

- Passwords are hashed with **bcrypt** (salt included automatically)
- Tokens are generated using `secrets.token_urlsafe(32)` (cryptographically secure)
- Whitelist admin endpoints are **localhost-only** — they reject connections from any non-loopback address
- Email addresses are normalised to lowercase before storage and comparison
- There is currently no email verification — the whitelist trusts that only pre-approved addresses will be used. Email verification may be added in a future release.
