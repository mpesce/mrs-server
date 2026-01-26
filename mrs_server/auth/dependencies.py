"""FastAPI authentication dependencies."""

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from mrs_server.models import UserInfo

from .bearer import AuthError, validate_token

# HTTP Bearer scheme for OpenAPI docs
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> UserInfo:
    """
    Get the currently authenticated user from the request.

    This dependency extracts the Bearer token from the Authorization header
    and validates it.

    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    try:
        return validate_token(credentials.credentials)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> UserInfo | None:
    """
    Get the current user if authenticated, or None if not.

    Useful for endpoints that behave differently for authenticated vs
    anonymous users.
    """
    if not credentials:
        return None

    try:
        return validate_token(credentials.credentials)
    except AuthError:
        return None


def require_local_user(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """
    Require that the authenticated user is a local user.

    Useful for management endpoints that should only work for users
    managed by this server.

    Raises:
        HTTPException: If user is not local
    """
    if not user.is_local:
        raise HTTPException(
            status_code=403, detail="This endpoint requires a local user account"
        )
    return user
