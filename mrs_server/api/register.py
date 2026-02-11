"""Registration endpoint for MRS."""

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from mrs_server.auth import get_current_user
from mrs_server.config import settings
from mrs_server.database import get_cursor
from mrs_server.geo import compute_bounding_box
from mrs_server.models import (
    Registration,
    RegistrationRequest,
    RegistrationResponse,
    SphereGeometry,
    UserInfo,
)

router = APIRouter()


def generate_registration_id() -> str:
    """Generate a unique registration ID."""
    return f"reg_{secrets.token_urlsafe(9)}"


@router.post("/register", response_model=RegistrationResponse, status_code=201)
async def create_registration(
    request: RegistrationRequest,
    user: UserInfo = Depends(get_current_user),
) -> RegistrationResponse:
    """
    Register a new space in MRS.

    Requires authentication. The authenticated user becomes the owner
    of the registration.
    """
    # Validate service_point is provided unless foad is true
    if not request.foad and not request.service_point:
        raise HTTPException(
            status_code=400,
            detail="service_point is required unless foad is true",
        )

    # Validate radius against server maximum
    if request.space.radius > settings.max_radius:
        raise HTTPException(
            status_code=400,
            detail=f"radius exceeds maximum of {settings.max_radius} meters",
        )

    # Check registration limit if configured
    if settings.max_registrations_per_user > 0:
        with get_cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) as count FROM registrations WHERE owner = ?",
                (user.id,),
            )
            count = cursor.fetchone()["count"]
            if count >= settings.max_registrations_per_user:
                raise HTTPException(
                    status_code=400,
                    detail=f"Maximum registrations ({settings.max_registrations_per_user}) reached",
                )

    # Compute bounding box for spatial indexing
    bbox = compute_bounding_box(request.space)

    # Generate ID and timestamps
    reg_id = generate_registration_id()
    now = datetime.now(timezone.utc)
    now_str = now.isoformat()

    # Insert registration
    origin_server = settings.server_url
    origin_id = reg_id
    version = 1

    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO registrations (
                id, owner, geo_type,
                center_lat, center_lon, center_ele, radius,
                service_point, foad,
                origin_server, origin_id, version,
                created_at, updated_at,
                bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reg_id,
                user.id,
                request.space.type,
                request.space.center.lat,
                request.space.center.lon,
                request.space.center.ele,
                request.space.radius,
                request.service_point,
                int(request.foad),
                origin_server,
                origin_id,
                version,
                now_str,
                now_str,
                bbox.min_lat,
                bbox.max_lat,
                bbox.min_lon,
                bbox.max_lon,
            ),
        )

    # Return the registration
    registration = Registration(
        id=reg_id,
        space=request.space,
        service_point=request.service_point,
        foad=request.foad,
        owner=user.id,
        origin_server=origin_server,
        origin_id=origin_id,
        version=version,
        created=now,
        updated=now,
    )

    return RegistrationResponse(registration=registration)


@router.put("/register/{reg_id}", response_model=RegistrationResponse)
async def update_registration(
    reg_id: str,
    request: RegistrationRequest,
    user: UserInfo = Depends(get_current_user),
) -> RegistrationResponse:
    """
    Update an existing registration.

    Only the owner can update a registration.
    """
    # Fetch existing registration
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT owner, created_at, origin_server, origin_id, version FROM registrations WHERE id = ?",
            (reg_id,),
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Registration not found")

        if row["owner"] != user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to update this registration"
            )

        created_at = row["created_at"]
        origin_server = row["origin_server"]
        origin_id = row["origin_id"]
        current_version = int(row["version"])

    # Validate service_point
    if not request.foad and not request.service_point:
        raise HTTPException(
            status_code=400,
            detail="service_point is required unless foad is true",
        )

    # Validate radius
    if request.space.radius > settings.max_radius:
        raise HTTPException(
            status_code=400,
            detail=f"radius exceeds maximum of {settings.max_radius} meters",
        )

    # Compute new bounding box
    bbox = compute_bounding_box(request.space)
    now = datetime.now(timezone.utc)
    now_str = now.isoformat()

    # Update registration
    with get_cursor() as cursor:
        cursor.execute(
            """
            UPDATE registrations SET
                geo_type = ?,
                center_lat = ?, center_lon = ?, center_ele = ?, radius = ?,
                service_point = ?, foad = ?,
                version = version + 1,
                updated_at = ?,
                bbox_min_lat = ?, bbox_max_lat = ?, bbox_min_lon = ?, bbox_max_lon = ?
            WHERE id = ?
            """,
            (
                request.space.type,
                request.space.center.lat,
                request.space.center.lon,
                request.space.center.ele,
                request.space.radius,
                request.service_point,
                int(request.foad),
                now_str,
                bbox.min_lat,
                bbox.max_lat,
                bbox.min_lon,
                bbox.max_lon,
                reg_id,
            ),
        )

    # Return updated registration
    registration = Registration(
        id=reg_id,
        space=request.space,
        service_point=request.service_point,
        foad=request.foad,
        owner=user.id,
        origin_server=origin_server,
        origin_id=origin_id,
        version=current_version + 1,
        created=datetime.fromisoformat(created_at),
        updated=now,
    )

    return RegistrationResponse(registration=registration)


def get_registration_by_id(reg_id: str) -> Registration | None:
    """
    Fetch a registration by ID.

    Utility function for other modules.
    """
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM registrations WHERE id = ?", (reg_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return _row_to_registration(row)


def get_registrations_by_owner(owner: str) -> list[Registration]:
    """
    Fetch all registrations for an owner.
    """
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT * FROM registrations WHERE owner = ? ORDER BY created_at DESC",
            (owner,),
        )
        return [_row_to_registration(row) for row in cursor.fetchall()]


def _row_to_registration(row) -> Registration:
    """Convert a database row to a Registration model."""
    from mrs_server.models import Location

    return Registration(
        id=row["id"],
        space=SphereGeometry(
            type="sphere",
            center=Location(
                lat=row["center_lat"],
                lon=row["center_lon"],
                ele=row["center_ele"],
            ),
            radius=row["radius"],
        ),
        service_point=row["service_point"],
        foad=bool(row["foad"]),
        owner=row["owner"],
        origin_server=row["origin_server"],
        origin_id=row["origin_id"],
        version=int(row["version"]),
        created=datetime.fromisoformat(row["created_at"]),
        updated=datetime.fromisoformat(row["updated_at"]),
    )
