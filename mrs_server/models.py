"""
Pydantic models for MRS protocol.

These models define the request/response structures for the MRS API.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from mrs_server.validation import validate_service_point_uri


# -----------------------------------------------------------------------------
# Core Geometry Models
# -----------------------------------------------------------------------------


class Location(BaseModel):
    """A point in 3D space (WGS84 coordinates)."""

    lat: float = Field(..., ge=-90, le=90, description="Latitude in degrees")
    lon: float = Field(..., ge=-180, le=180, description="Longitude in degrees")
    ele: float = Field(default=0, description="Elevation in meters above sea level")


class SphereGeometry(BaseModel):
    """A spherical region in space."""

    type: Literal["sphere"] = "sphere"
    center: Location
    radius: float = Field(..., gt=0, le=1_000_000, description="Radius in meters")


# For now, only sphere is supported. This can be extended later:
# SpaceGeometry = SphereGeometry | PolygonGeometry
SpaceGeometry = SphereGeometry


class BoundingBox(BaseModel):
    """Axis-aligned bounding box for spatial indexing."""

    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float


# -----------------------------------------------------------------------------
# Registration Models
# -----------------------------------------------------------------------------


class RegistrationRequest(BaseModel):
    """Request to register a space."""

    space: SpaceGeometry
    service_point: str | None = Field(
        default=None, description="URI for this space's service endpoint"
    )
    foad: bool = Field(default=False, description="Fuck Off And Die - hide from searches")

    @field_validator("service_point")
    @classmethod
    def validate_service_point(cls, v: str | None, info) -> str | None:
        # service_point presence vs foad is validated in endpoints.
        if v is None:
            return None
        return validate_service_point_uri(v)


class Registration(BaseModel):
    """A registered space in MRS."""

    id: str
    space: SpaceGeometry
    service_point: str | None
    foad: bool
    owner: str
    origin_server: str | None = None
    origin_id: str | None = None
    version: int = 1
    created: datetime
    updated: datetime


class RegistrationResponse(BaseModel):
    """Response after successful registration."""

    status: Literal["registered"] = "registered"
    registration: Registration


class ReleaseRequest(BaseModel):
    """Request to release (delete) a registration."""

    id: str


class ReleaseResponse(BaseModel):
    """Response after successful release."""

    status: Literal["released"] = "released"
    id: str


# -----------------------------------------------------------------------------
# Search Models
# -----------------------------------------------------------------------------


class SearchRequest(BaseModel):
    """Request to search for registrations."""

    location: Location
    range: float = Field(..., gt=0, le=1_000_000, description="Search radius in meters")


class SearchResult(BaseModel):
    """A single search result."""

    id: str
    space: SpaceGeometry
    service_point: str | None
    foad: bool
    distance: float = Field(description="Distance from query point in meters")
    owner: str
    origin_server: str | None = None
    origin_id: str | None = None
    version: int = 1
    created: datetime
    updated: datetime


class Referral(BaseModel):
    """A referral to another MRS server."""

    server: str
    hint: str | None = None


class SearchResponse(BaseModel):
    """Response from a search query."""

    status: Literal["ok"] = "ok"
    results: list[SearchResult]
    referrals: list[Referral] = []


# -----------------------------------------------------------------------------
# Sync Models
# -----------------------------------------------------------------------------


class SyncSnapshotResponse(BaseModel):
    """Paginated snapshot response for bootstrap sync."""

    status: Literal["ok"] = "ok"
    registrations: list[Registration]
    next_cursor: str | None = None


class Tombstone(BaseModel):
    """Delete event for replicated consistency."""

    origin_server: str
    origin_id: str
    version: int
    deleted_at: datetime


class SyncChangesResponse(BaseModel):
    """Incremental changes response since a cursor."""

    status: Literal["ok"] = "ok"
    registrations: list[Registration]
    tombstones: list[Tombstone]
    next_cursor: str


# -----------------------------------------------------------------------------
# Auth Models
# -----------------------------------------------------------------------------


class UserRegisterRequest(BaseModel):
    """Request to register a new user account."""

    username: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8, max_length=128)


class UserLoginRequest(BaseModel):
    """Request to log in and get a bearer token."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Response containing a bearer token."""

    token: str
    expires_at: datetime | None = None


class UserInfo(BaseModel):
    """Information about the current user."""

    id: str
    created_at: datetime
    is_local: bool


# -----------------------------------------------------------------------------
# Well-Known Models
# -----------------------------------------------------------------------------


class ServerCapabilities(BaseModel):
    """Server capabilities advertised in /.well-known/mrs."""

    geometry_types: list[str] = ["sphere"]
    max_radius: float


class PeerInfo(BaseModel):
    """Information about a known peer."""

    server: str
    hint: str | None = None


class WellKnownMRS(BaseModel):
    """Response for /.well-known/mrs endpoint."""

    mrs_version: str = "0.5.0"
    server: str
    operator: str
    authoritative_regions: list[SpaceGeometry] = []
    known_peers: list[PeerInfo] = []
    capabilities: ServerCapabilities


class PublicKey(BaseModel):
    """A public key for identity verification."""

    type: str = "Ed25519"
    key: str  # base64-encoded


class KeyResponse(BaseModel):
    """Response for /.well-known/mrs/keys/{identity}."""

    id: str
    public_key: PublicKey
    created: datetime


# -----------------------------------------------------------------------------
# Error Models
# -----------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: str | None = None
