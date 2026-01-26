"""Bearer token authentication."""

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt

from mrs_server.config import settings
from mrs_server.database import get_cursor
from mrs_server.models import TokenResponse, UserInfo


class AuthError(Exception):
    """Authentication error."""

    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def generate_token() -> str:
    """Generate a secure random bearer token."""
    return secrets.token_urlsafe(32)


def create_user(username: str, password: str, domain: str) -> str:
    """
    Create a new local user.

    Args:
        username: The username (without domain)
        password: The plaintext password
        domain: The server domain

    Returns:
        The full MRS identity (user@domain)

    Raises:
        AuthError: If user already exists
    """
    identity = f"{username}@{domain}"
    now = datetime.now(timezone.utc).isoformat()

    with get_cursor() as cursor:
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = ?", (identity,))
        if cursor.fetchone():
            raise AuthError(f"User {identity} already exists", 400)

        # Create user
        cursor.execute(
            """
            INSERT INTO users (id, password_hash, created_at, is_local)
            VALUES (?, ?, ?, 1)
            """,
            (identity, hash_password(password), now),
        )

    return identity


def authenticate_user(username: str, password: str, domain: str) -> str:
    """
    Authenticate a user and return their identity.

    Args:
        username: The username (without domain)
        password: The plaintext password
        domain: The server domain

    Returns:
        The full MRS identity

    Raises:
        AuthError: If authentication fails
    """
    identity = f"{username}@{domain}"

    with get_cursor() as cursor:
        cursor.execute(
            "SELECT password_hash FROM users WHERE id = ? AND is_local = 1",
            (identity,),
        )
        row = cursor.fetchone()

        if not row:
            raise AuthError("Invalid username or password")

        if not verify_password(password, row["password_hash"]):
            raise AuthError("Invalid username or password")

    return identity


def create_token(user_id: str) -> TokenResponse:
    """
    Create a new bearer token for a user.

    Args:
        user_id: The MRS identity

    Returns:
        TokenResponse with the token and expiry
    """
    token = generate_token()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=settings.token_expiry_hours)

    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO tokens (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, user_id, now.isoformat(), expires_at.isoformat()),
        )

    return TokenResponse(token=token, expires_at=expires_at)


def validate_token(token: str) -> UserInfo:
    """
    Validate a bearer token and return the user.

    Args:
        token: The bearer token

    Returns:
        UserInfo for the authenticated user

    Raises:
        AuthError: If token is invalid or expired
    """
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT t.user_id, t.expires_at, u.created_at, u.is_local
            FROM tokens t
            JOIN users u ON t.user_id = u.id
            WHERE t.token = ?
            """,
            (token,),
        )
        row = cursor.fetchone()

        if not row:
            raise AuthError("Invalid token")

        if row["expires_at"]:
            expires = datetime.fromisoformat(row["expires_at"])
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < datetime.now(timezone.utc):
                raise AuthError("Token expired")

        return UserInfo(
            id=row["user_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            is_local=bool(row["is_local"]),
        )


def revoke_token(token: str) -> bool:
    """
    Revoke a bearer token.

    Args:
        token: The token to revoke

    Returns:
        True if the token was revoked, False if it didn't exist
    """
    with get_cursor() as cursor:
        cursor.execute("DELETE FROM tokens WHERE token = ?", (token,))
        return cursor.rowcount > 0


def revoke_all_tokens(user_id: str) -> int:
    """
    Revoke all tokens for a user.

    Args:
        user_id: The MRS identity

    Returns:
        Number of tokens revoked
    """
    with get_cursor() as cursor:
        cursor.execute("DELETE FROM tokens WHERE user_id = ?", (user_id,))
        return cursor.rowcount


def cleanup_expired_tokens() -> int:
    """
    Remove expired tokens from the database.

    Returns:
        Number of tokens removed
    """
    now = datetime.now(timezone.utc).isoformat()
    with get_cursor() as cursor:
        cursor.execute(
            "DELETE FROM tokens WHERE expires_at IS NOT NULL AND expires_at < ?",
            (now,),
        )
        return cursor.rowcount
