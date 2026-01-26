"""Release endpoint for MRS."""

from fastapi import APIRouter, Depends, HTTPException

from mrs_server.auth import get_current_user
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
            "SELECT owner FROM registrations WHERE id = ?",
            (request.id,),
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Registration not found")

        if row["owner"] != user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to release this registration"
            )

        # Delete the registration
        cursor.execute("DELETE FROM registrations WHERE id = ?", (request.id,))

    return ReleaseResponse(id=request.id)
