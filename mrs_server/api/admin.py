"""Admin endpoints for bulk database export/import.

These endpoints are restricted to localhost connections only.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from mrs_server.config import settings
from mrs_server.database import get_cursor
from mrs_server.geo import compute_bounding_box
from mrs_server.models import Location, SphereGeometry

router = APIRouter(prefix="/admin")

_LOOPBACK_ADDRS = {"127.0.0.1", "::1"}


async def require_localhost(request: Request) -> None:
    """Reject any request not originating from loopback."""
    client_host = request.client.host if request.client else None
    if client_host not in _LOOPBACK_ADDRS:
        raise HTTPException(status_code=403, detail="Admin endpoints are localhost-only")


@router.get("/export", dependencies=[Depends(require_localhost)])
async def export_database():
    """Export the full registry as JSON.

    Returns all registrations, tombstones, and peers in a format
    that ``POST /admin/import`` will accept for a round-trip restore.
    """
    with get_cursor() as cur:
        cur.execute("SELECT * FROM registrations ORDER BY id ASC")
        reg_rows = cur.fetchall()

        cur.execute(
            "SELECT origin_server, origin_id, version, deleted_at "
            "FROM tombstones ORDER BY origin_server, origin_id"
        )
        tomb_rows = cur.fetchall()

        cur.execute(
            "SELECT server_url, hint, last_seen, is_configured, authoritative_regions "
            "FROM peers ORDER BY server_url"
        )
        peer_rows = cur.fetchall()

    registrations = [
        {
            "id": r["id"],
            "owner": r["owner"],
            "space": {
                "type": r["geo_type"],
                "center": {
                    "lat": r["center_lat"],
                    "lon": r["center_lon"],
                    "ele": r["center_ele"],
                },
                "radius": r["radius"],
            },
            "service_point": r["service_point"],
            "foad": bool(r["foad"]),
            "origin_server": r["origin_server"],
            "origin_id": r["origin_id"],
            "version": int(r["version"]),
            "created": r["created_at"],
            "updated": r["updated_at"],
        }
        for r in reg_rows
    ]

    tombstones = [
        {
            "origin_server": t["origin_server"],
            "origin_id": t["origin_id"],
            "version": int(t["version"]),
            "deleted_at": t["deleted_at"],
        }
        for t in tomb_rows
    ]

    peers = [
        {
            "server_url": p["server_url"],
            "hint": p["hint"],
            "last_seen": p["last_seen"],
            "is_configured": bool(p["is_configured"]),
            "authoritative_regions": (
                json.loads(p["authoritative_regions"])
                if p["authoritative_regions"]
                else None
            ),
        }
        for p in peer_rows
    ]

    return {
        "mrs_version": "0.5.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "server": settings.server_url,
        "registrations": registrations,
        "tombstones": tombstones,
        "peers": peers,
    }


@router.post("/import", dependencies=[Depends(require_localhost)])
async def import_database(request: Request):
    """Import registrations, tombstones, and peers from JSON.

    Uses upsert semantics so it is safe to run repeatedly.
    Accepts the same format that ``GET /admin/export`` produces.
    """
    body = await request.json()

    registrations = body.get("registrations", [])
    tombstones = body.get("tombstones", [])
    peers = body.get("peers", [])

    reg_count = 0
    tomb_count = 0
    peer_count = 0

    with get_cursor() as cur:
        for reg in registrations:
            space = reg["space"]
            center = space["center"]

            # Recompute bounding box to guarantee consistency
            sphere = SphereGeometry(
                type="sphere",
                center=Location(
                    lat=center["lat"], lon=center["lon"], ele=center.get("ele", 0)
                ),
                radius=space["radius"],
            )
            bbox = compute_bounding_box(sphere)

            cur.execute(
                """
                INSERT INTO registrations (
                    id, owner, geo_type,
                    center_lat, center_lon, center_ele, radius,
                    service_point, foad,
                    origin_server, origin_id, version,
                    created_at, updated_at,
                    bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    owner = excluded.owner,
                    geo_type = excluded.geo_type,
                    center_lat = excluded.center_lat,
                    center_lon = excluded.center_lon,
                    center_ele = excluded.center_ele,
                    radius = excluded.radius,
                    service_point = excluded.service_point,
                    foad = excluded.foad,
                    origin_server = excluded.origin_server,
                    origin_id = excluded.origin_id,
                    version = excluded.version,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at,
                    bbox_min_lat = excluded.bbox_min_lat,
                    bbox_max_lat = excluded.bbox_max_lat,
                    bbox_min_lon = excluded.bbox_min_lon,
                    bbox_max_lon = excluded.bbox_max_lon
                """,
                (
                    reg["id"],
                    reg["owner"],
                    space.get("type", "sphere"),
                    center["lat"],
                    center["lon"],
                    center.get("ele", 0),
                    space["radius"],
                    reg.get("service_point"),
                    int(reg.get("foad", False)),
                    reg.get("origin_server", ""),
                    reg.get("origin_id", reg["id"]),
                    reg.get("version", 1),
                    reg["created"],
                    reg["updated"],
                    bbox.min_lat,
                    bbox.max_lat,
                    bbox.min_lon,
                    bbox.max_lon,
                ),
            )
            reg_count += 1

        for tomb in tombstones:
            cur.execute(
                """
                INSERT INTO tombstones (origin_server, origin_id, version, deleted_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(origin_server, origin_id) DO UPDATE SET
                    version = MAX(tombstones.version, excluded.version),
                    deleted_at = excluded.deleted_at
                """,
                (
                    tomb["origin_server"],
                    tomb["origin_id"],
                    tomb["version"],
                    tomb["deleted_at"],
                ),
            )
            tomb_count += 1

        for peer in peers:
            regions_json = (
                json.dumps(peer["authoritative_regions"])
                if peer.get("authoritative_regions")
                else None
            )
            cur.execute(
                """
                INSERT INTO peers (server_url, hint, last_seen, is_configured, authoritative_regions)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(server_url) DO UPDATE SET
                    hint = COALESCE(excluded.hint, peers.hint),
                    last_seen = excluded.last_seen,
                    is_configured = MAX(peers.is_configured, excluded.is_configured),
                    authoritative_regions = COALESCE(excluded.authoritative_regions, peers.authoritative_regions)
                """,
                (
                    peer["server_url"],
                    peer.get("hint"),
                    peer.get("last_seen"),
                    int(peer.get("is_configured", False)),
                    regions_json,
                ),
            )
            peer_count += 1

    return {
        "status": "imported",
        "registrations": reg_count,
        "tombstones": tomb_count,
        "peers": peer_count,
    }


# ---------------------------------------------------------------------------
# Whitelist management
# ---------------------------------------------------------------------------


@router.get("/whitelist", dependencies=[Depends(require_localhost)])
async def list_whitelist():
    """List all whitelisted email addresses."""
    with get_cursor() as cur:
        cur.execute("SELECT email, added_at FROM registration_whitelist ORDER BY email")
        rows = cur.fetchall()

    return {
        "emails": [{"email": r["email"], "added_at": r["added_at"]} for r in rows],
    }


@router.post("/whitelist", dependencies=[Depends(require_localhost)], status_code=201)
async def add_to_whitelist(request: Request):
    """Add an email address to the registration whitelist.

    Accepts ``{"email": "user@example.com"}`` or
    ``{"emails": ["a@b.com", "c@d.com"]}``.
    """
    body = await request.json()

    # Accept single email or list
    emails: list[str] = []
    if "email" in body:
        emails.append(body["email"])
    if "emails" in body:
        emails.extend(body["emails"])

    if not emails:
        raise HTTPException(status_code=400, detail="No email address provided")

    now = datetime.now(timezone.utc).isoformat()
    added = 0

    with get_cursor() as cur:
        for email in emails:
            normalised = email.strip().lower()
            if not normalised or "@" not in normalised:
                raise HTTPException(
                    status_code=400, detail=f"Invalid email address: {email}"
                )
            cur.execute(
                """
                INSERT INTO registration_whitelist (email, added_at)
                VALUES (?, ?)
                ON CONFLICT(email) DO NOTHING
                """,
                (normalised, now),
            )
            added += cur.rowcount

    return {"status": "added", "added": added}


@router.delete("/whitelist/{email}", dependencies=[Depends(require_localhost)])
async def remove_from_whitelist(email: str):
    """Remove an email address from the registration whitelist."""
    normalised = email.strip().lower()

    if not normalised:
        raise HTTPException(status_code=400, detail="No email address provided")

    with get_cursor() as cur:
        cur.execute(
            "DELETE FROM registration_whitelist WHERE email = ?", (normalised,)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Email not in whitelist")

    return {"status": "removed", "email": normalised}
