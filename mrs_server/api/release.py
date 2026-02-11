"""Release endpoint for MRS."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from mrs_server.auth import get_current_user
from mrs_server.config import settings
from mrs_server.database import get_cursor
from mrs_server.models import ReleaseRequest, ReleaseResponse, UserInfo

router = APIRouter()


@router.post("/release", response_model=ReleaseResponse)
async def release_registration(
    request: ReleaseRequest,
    user: UserInfo = Depends(get_current_user),
) -> ReleaseResponse:
    """
    Release (delete) a registration.

    Only the owner can release a registration.
    """
    with get_cursor() as cursor:
        # Fetch the registration to verify ownership
        cursor.execute(
            "SELECT owner, origin_server, origin_id, version FROM registrations WHERE id = ?",
            (request.id,),
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Registration not found")

        if row["owner"] != user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to release this registration"
            )

        if row["origin_server"] != settings.server_url:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "not_authoritative",
                    "message": "This server is not authoritative for the registration",
                    "origin_server": row["origin_server"],
                    "origin_id": row["origin_id"],
                },
            )

        deleted_at = datetime.now(timezone.utc).isoformat()

        # Record tombstone for sync propagation
        cursor.execute(
            """
            INSERT INTO tombstones (origin_server, origin_id, version, deleted_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(origin_server, origin_id)
            DO UPDATE SET
                version = excluded.version,
                deleted_at = excluded.deleted_at
            """,
            (
                row["origin_server"],
                row["origin_id"],
                int(row["version"]) + 1,
                deleted_at,
            ),
        )

        # Delete the registration
        cursor.execute("DELETE FROM registrations WHERE id = ?", (request.id,))

    return ReleaseResponse(id=request.id)
