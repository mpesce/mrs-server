"""
Database module for MRS server.

Provides SQLite database initialization, connection management, and schema setup.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

# Module-level connection for the application
_db_path: Path | None = None
_connection: sqlite3.Connection | None = None


SCHEMA = """
-- Registrations: spatial claims in MRS
CREATE TABLE IF NOT EXISTS registrations (
    id TEXT PRIMARY KEY,                    -- "reg_" + 12 random alphanumeric
    owner TEXT NOT NULL,                    -- MRS identity (user@domain)

    -- Geometry (sphere only for now)
    geo_type TEXT NOT NULL DEFAULT 'sphere',
    center_lat REAL NOT NULL,
    center_lon REAL NOT NULL,
    center_ele REAL NOT NULL DEFAULT 0,
    radius REAL NOT NULL,                   -- meters

    -- Service
    service_point TEXT,                     -- URI, null if foad=true
    foad INTEGER NOT NULL DEFAULT 0,        -- boolean: 1=true, 0=false

    -- Canonical federation metadata
    origin_server TEXT NOT NULL,
    origin_id TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,

    -- Metadata
    created_at TEXT NOT NULL,               -- ISO 8601
    updated_at TEXT NOT NULL,               -- ISO 8601

    -- Spatial index helpers (precomputed bounding box)
    bbox_min_lat REAL NOT NULL,
    bbox_max_lat REAL NOT NULL,
    bbox_min_lon REAL NOT NULL,
    bbox_max_lon REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_registrations_bbox ON registrations(
    bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon
);
CREATE INDEX IF NOT EXISTS idx_registrations_owner ON registrations(owner);
CREATE INDEX IF NOT EXISTS idx_registrations_updated ON registrations(updated_at);

-- Tombstones: propagated deletes for sync consistency
CREATE TABLE IF NOT EXISTS tombstones (
    origin_server TEXT NOT NULL,
    origin_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    deleted_at TEXT NOT NULL,
    PRIMARY KEY (origin_server, origin_id)
);

CREATE INDEX IF NOT EXISTS idx_tombstones_deleted_at ON tombstones(deleted_at);

-- Users: local and federated identities
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,                    -- MRS identity (user@domain)
    password_hash TEXT,                     -- bcrypt hash, for local users
    created_at TEXT NOT NULL,
    is_local INTEGER NOT NULL DEFAULT 0     -- 1 if this server manages this identity
);

CREATE INDEX IF NOT EXISTS idx_users_local ON users(is_local);

-- Keys: cryptographic keys for identities
-- Note: No foreign key on owner because keys can belong to "_server" or federated identities
CREATE TABLE IF NOT EXISTS keys (
    id TEXT PRIMARY KEY,                    -- "key_" + random id
    owner TEXT NOT NULL,                    -- MRS identity or "_server" for server key
    key_id TEXT NOT NULL,                   -- human-readable key identifier
    algorithm TEXT NOT NULL DEFAULT 'Ed25519',
    public_key TEXT NOT NULL,               -- base64-encoded
    private_key TEXT,                       -- base64-encoded, only for local identities
    created_at TEXT NOT NULL,
    expires_at TEXT,
    deprecated INTEGER NOT NULL DEFAULT 0,

    UNIQUE(owner, key_id)
);

CREATE INDEX IF NOT EXISTS idx_keys_owner ON keys(owner);

-- Tokens: bearer tokens for authentication
CREATE TABLE IF NOT EXISTS tokens (
    token TEXT PRIMARY KEY,                 -- random bearer token
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT,

    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_tokens_user ON tokens(user_id);

-- Peers: known MRS federation peers
CREATE TABLE IF NOT EXISTS peers (
    server_url TEXT PRIMARY KEY,            -- e.g., "https://sydney.mrs.example"
    hint TEXT,                              -- human-readable description
    last_seen TEXT,                         -- ISO 8601
    is_configured INTEGER NOT NULL DEFAULT 0,
    authoritative_regions TEXT              -- JSON array of geometry objects
);

-- Server configuration
CREATE TABLE IF NOT EXISTS server_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _ensure_registration_columns(conn: sqlite3.Connection) -> None:
    """Ensure backward-compatible presence of newer registrations columns."""
    cur = conn.execute("PRAGMA table_info(registrations)")
    cols = {row[1] for row in cur.fetchall()}

    if "origin_server" not in cols:
        conn.execute(
            "ALTER TABLE registrations ADD COLUMN origin_server TEXT NOT NULL DEFAULT ''"
        )
    if "origin_id" not in cols:
        conn.execute(
            "ALTER TABLE registrations ADD COLUMN origin_id TEXT NOT NULL DEFAULT ''"
        )
    if "version" not in cols:
        conn.execute(
            "ALTER TABLE registrations ADD COLUMN version INTEGER NOT NULL DEFAULT 1"
        )

    # Backfill defaults for legacy rows
    conn.execute(
        "UPDATE registrations SET origin_server = '' WHERE origin_server IS NULL"
    )
    conn.execute("UPDATE registrations SET origin_id = id WHERE origin_id IS NULL OR origin_id = ''")
    conn.execute("UPDATE registrations SET version = 1 WHERE version IS NULL OR version < 1")


def init_database(db_path: str | Path) -> None:
    """Initialize the database with the MRS schema."""
    global _db_path, _connection

    _db_path = Path(db_path)
    _connection = sqlite3.connect(str(_db_path), check_same_thread=False)
    _connection.row_factory = sqlite3.Row

    # Enable foreign keys
    _connection.execute("PRAGMA foreign_keys = ON")

    # Create schema
    _connection.executescript(SCHEMA)
    _ensure_registration_columns(_connection)
    _connection.commit()


def get_connection() -> sqlite3.Connection:
    """Get the current database connection."""
    if _connection is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _connection


@contextmanager
def get_cursor() -> Generator[sqlite3.Cursor, None, None]:
    """Get a database cursor with automatic commit/rollback."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def close_database() -> None:
    """Close the database connection."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None


def get_config(key: str) -> str | None:
    """Get a configuration value from the database."""
    with get_cursor() as cursor:
        cursor.execute("SELECT value FROM server_config WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else None


def set_config(key: str, value: str) -> None:
    """Set a configuration value in the database."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO server_config (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
