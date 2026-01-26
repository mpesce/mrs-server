"""API endpoints for MRS protocol."""

from fastapi import APIRouter

from . import auth, register, release, search, wellknown

# Create a combined router for all API endpoints
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(register.router, tags=["registrations"])
api_router.include_router(release.router, tags=["registrations"])
api_router.include_router(search.router, tags=["search"])
api_router.include_router(wellknown.router, tags=["discovery"])
api_router.include_router(auth.router, tags=["auth"])
