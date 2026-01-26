"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from mrs_server.auth import (
    AuthError,
    authenticate_user,
    create_token,
    create_user,
    get_current_user,
)
from mrs_server.config import settings
from mrs_server.models import (
    TokenResponse,
    UserInfo,
    UserLoginRequest,
    UserRegisterRequest,
)

from .register import get_registrations_by_owner

router = APIRouter(prefix="/auth")


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register_user(request: UserRegisterRequest) -> TokenResponse:
    """
    Register a new user account.

    Creates a local user account on this server and returns a bearer token.
    The user's MRS identity will be username@server_domain.
    """
    try:
        identity = create_user(
            username=request.username,
            password=request.password,
            domain=settings.server_domain,
        )
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    # Create and return a token
    return create_token(identity)


@router.post("/login", response_model=TokenResponse)
async def login_user(request: UserLoginRequest) -> TokenResponse:
    """
    Log in and get a bearer token.

    Authenticates the user and returns a bearer token for subsequent requests.
    """
    try:
        identity = authenticate_user(
            username=request.username,
            password=request.password,
            domain=settings.server_domain,
        )
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    return create_token(identity)


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    user: UserInfo = Depends(get_current_user),
) -> UserInfo:
    """
    Get information about the currently authenticated user.
    """
    return user


@router.get("/me/registrations")
async def get_my_registrations(
    user: UserInfo = Depends(get_current_user),
):
    """
    Get all registrations owned by the current user.
    """
    registrations = get_registrations_by_owner(user.id)
    return {"registrations": registrations}
