"""Authentication module for MRS server."""

from .bearer import (
    AuthError,
    authenticate_user,
    cleanup_expired_tokens,
    create_token,
    create_user,
    revoke_all_tokens,
    revoke_token,
    validate_token,
)
from .dependencies import get_current_user, get_optional_user, require_local_user
from .keys import ensure_server_key, get_public_key, get_server_key

__all__ = [
    "AuthError",
    "create_user",
    "authenticate_user",
    "create_token",
    "validate_token",
    "revoke_token",
    "revoke_all_tokens",
    "cleanup_expired_tokens",
    "get_current_user",
    "get_optional_user",
    "require_local_user",
    "get_server_key",
    "get_public_key",
    "ensure_server_key",
]
