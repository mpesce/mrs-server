"""
Cryptographic key management.

This module handles Ed25519 key generation and storage for server identity
and user keys. HTTP signature verification will be added in a future version.
"""

import base64
import secrets
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from mrs_server.database import get_cursor


def generate_key_id() -> str:
    """Generate a unique key ID."""
    return f"key_{secrets.token_urlsafe(9)}"


def generate_ed25519_keypair() -> tuple[bytes, bytes]:
    """
    Generate a new Ed25519 keypair.

    Returns:
        Tuple of (private_key_bytes, public_key_bytes)
    """
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    return private_bytes, public_bytes


def store_key(
    owner: str,
    key_id: str,
    public_key: bytes,
    private_key: bytes | None = None,
    expires_at: datetime | None = None,
) -> str:
    """
    Store a key in the database.

    Args:
        owner: MRS identity or "_server" for server key
        key_id: Human-readable key identifier
        public_key: Raw public key bytes
        private_key: Raw private key bytes (only for local identities)
        expires_at: Optional expiration time

    Returns:
        The database ID for the key
    """
    db_id = generate_key_id()
    now = datetime.now(timezone.utc).isoformat()

    public_b64 = base64.b64encode(public_key).decode()
    private_b64 = base64.b64encode(private_key).decode() if private_key else None
    expires_str = expires_at.isoformat() if expires_at else None

    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO keys (id, owner, key_id, algorithm, public_key, private_key,
                              created_at, expires_at, deprecated)
            VALUES (?, ?, ?, 'Ed25519', ?, ?, ?, ?, 0)
            """,
            (db_id, owner, key_id, public_b64, private_b64, now, expires_str),
        )

    return db_id


def get_server_key() -> dict | None:
    """
    Get the server's signing key.

    Returns:
        Dict with key info or None if no server key exists
    """
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, key_id, public_key, private_key, created_at
            FROM keys
            WHERE owner = '_server' AND deprecated = 0
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": row["id"],
            "key_id": row["key_id"],
            "public_key": base64.b64decode(row["public_key"]),
            "private_key": base64.b64decode(row["private_key"]) if row["private_key"] else None,
            "created_at": datetime.fromisoformat(row["created_at"]),
        }


def get_public_key(owner: str) -> dict | None:
    """
    Get the public key for an identity.

    Args:
        owner: MRS identity or "_server"

    Returns:
        Dict with key info or None if not found
    """
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT key_id, public_key, created_at, expires_at
            FROM keys
            WHERE owner = ? AND deprecated = 0
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (owner,),
        )
        row = cursor.fetchone()

        if not row:
            return None

        return {
            "key_id": row["key_id"],
            "public_key": base64.b64decode(row["public_key"]),
            "public_key_b64": row["public_key"],
            "created_at": datetime.fromisoformat(row["created_at"]),
            "expires_at": (
                datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None
            ),
        }


def ensure_server_key() -> dict:
    """
    Ensure the server has a signing key, generating one if needed.

    Returns:
        Dict with server key info
    """
    existing = get_server_key()
    if existing:
        return existing

    # Generate new server key
    private_bytes, public_bytes = generate_ed25519_keypair()

    # Use a dated key_id for easier key rotation
    key_id = f"server-{datetime.now(timezone.utc).strftime('%Y-%m')}"

    store_key(
        owner="_server",
        key_id=key_id,
        public_key=public_bytes,
        private_key=private_bytes,
    )

    return get_server_key()


def deprecate_key(owner: str, key_id: str) -> bool:
    """
    Mark a key as deprecated.

    Args:
        owner: MRS identity
        key_id: The key identifier

    Returns:
        True if key was deprecated, False if not found
    """
    with get_cursor() as cursor:
        cursor.execute(
            "UPDATE keys SET deprecated = 1 WHERE owner = ? AND key_id = ?",
            (owner, key_id),
        )
        return cursor.rowcount > 0
