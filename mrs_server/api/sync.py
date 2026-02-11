"""Sync endpoints for federation bootstrap and incremental changes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Query

from mrs_server.database import get_cursor
from mrs_server.models import (
    Location,
    Registration,
    SphereGeometry,
    SyncChangesResponse,
    SyncSnapshotResponse,
    Tombstone,
)

router = APIRouter()


def _row_to_registration(row) -> Registration:
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


@router.get("/sync/snapshot", response_model=SyncSnapshotResponse)
async def get_snapshot(
    cursor: str | None = Query(default=None, description="Pagination cursor (registration id)"),
    limit: int = Query(default=200, ge=1, le=1000),
) -> SyncSnapshotResponse:
    """Return a paginated snapshot of registrations."""
    with get_cursor() as cur:
        if cursor:
            cur.execute(
                """
                SELECT * FROM registrations
                WHERE id > ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (cursor, limit + 1),
            )
        else:
            cur.execute(
                """
                SELECT * FROM registrations
                ORDER BY id ASC
                LIMIT ?
                """,
                (limit + 1,),
            )
        rows = cur.fetchall()

    has_more = len(rows) > limit
    rows = rows[:limit]
    regs = [_row_to_registration(r) for r in rows]
    next_cursor = rows[-1]["id"] if has_more and rows else None

    return SyncSnapshotResponse(registrations=regs, next_cursor=next_cursor)


@router.get("/sync/changes", response_model=SyncChangesResponse)
async def get_changes(
    since: str = Query(description="ISO8601 timestamp cursor"),
    limit: int = Query(default=500, ge=1, le=5000),
) -> SyncChangesResponse:
    """Return incremental registration and tombstone changes since cursor."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT * FROM registrations
            WHERE updated_at > ?
            ORDER BY updated_at ASC
            LIMIT ?
            """,
            (since, limit),
        )
        reg_rows = cur.fetchall()

        cur.execute(
            """
            SELECT origin_server, origin_id, version, deleted_at
            FROM tombstones
            WHERE deleted_at > ?
            ORDER BY deleted_at ASC
            LIMIT ?
            """,
            (since, limit),
        )
        tomb_rows = cur.fetchall()

    regs = [_row_to_registration(r) for r in reg_rows]
    tombs = [
        Tombstone(
            origin_server=r["origin_server"],
            origin_id=r["origin_id"],
            version=int(r["version"]),
            deleted_at=datetime.fromisoformat(r["deleted_at"]),
        )
        for r in tomb_rows
    ]

    newest = since
    if reg_rows:
        newest = max(newest, max(r["updated_at"] for r in reg_rows))
    if tomb_rows:
        newest = max(newest, max(r["deleted_at"] for r in tomb_rows))
    if newest == since:
        newest = datetime.now(timezone.utc).isoformat()

    return SyncChangesResponse(registrations=regs, tombstones=tombs, next_cursor=newest)
