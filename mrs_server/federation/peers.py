"""Peer management for MRS federation."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from mrs_server.database import get_cursor


@dataclass
class Peer:
    """A known MRS peer server."""

    server_url: str
    hint: str | None
    last_seen: datetime | None
    is_configured: bool
    authoritative_regions: list | None


def add_peer(
    server_url: str,
    hint: str | None = None,
    is_configured: bool = False,
    authoritative_regions: list | None = None,
) -> None:
    """
    Add or update a known peer.

    Args:
        server_url: The peer's base URL
        hint: Human-readable description
        is_configured: True if manually configured (bootstrap peer)
        authoritative_regions: List of geometry objects the peer claims
    """
    now = datetime.now(timezone.utc).isoformat()
    regions_json = json.dumps(authoritative_regions) if authoritative_regions else None

    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO peers (server_url, hint, last_seen, is_configured, authoritative_regions)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(server_url) DO UPDATE SET
                hint = COALESCE(excluded.hint, hint),
                last_seen = excluded.last_seen,
                is_configured = MAX(is_configured, excluded.is_configured),
                authoritative_regions = COALESCE(excluded.authoritative_regions, authoritative_regions)
            """,
            (server_url, hint, now, int(is_configured), regions_json),
        )


def remove_peer(server_url: str) -> bool:
    """
    Remove a peer from the database.

    Args:
        server_url: The peer's base URL

    Returns:
        True if peer was removed, False if not found
    """
    with get_cursor() as cursor:
        cursor.execute("DELETE FROM peers WHERE server_url = ?", (server_url,))
        return cursor.rowcount > 0


def get_peer(server_url: str) -> Peer | None:
    """
    Get a specific peer by URL.

    Args:
        server_url: The peer's base URL

    Returns:
        Peer object or None if not found
    """
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM peers WHERE server_url = ?", (server_url,))
        row = cursor.fetchone()

        if not row:
            return None

        return _row_to_peer(row)


def get_all_peers() -> list[Peer]:
    """
    Get all known peers.

    Returns:
        List of peers, configured peers first, then by last_seen
    """
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT * FROM peers
            ORDER BY is_configured DESC, last_seen DESC
            """
        )
        return [_row_to_peer(row) for row in cursor.fetchall()]


def get_configured_peers() -> list[Peer]:
    """
    Get only manually configured (bootstrap) peers.

    Returns:
        List of configured peers
    """
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM peers WHERE is_configured = 1")
        return [_row_to_peer(row) for row in cursor.fetchall()]


def update_peer_last_seen(server_url: str) -> None:
    """
    Update the last_seen timestamp for a peer.

    Called when we successfully communicate with a peer.
    """
    now = datetime.now(timezone.utc).isoformat()
    with get_cursor() as cursor:
        cursor.execute(
            "UPDATE peers SET last_seen = ? WHERE server_url = ?",
            (now, server_url),
        )


def learn_peer_from_referral(server_url: str, hint: str | None = None) -> None:
    """
    Learn about a peer from a referral in a search response.

    Peers learned this way are not marked as configured.

    Args:
        server_url: The peer's base URL
        hint: Optional hint from the referral
    """
    add_peer(server_url, hint=hint, is_configured=False)


def _row_to_peer(row) -> Peer:
    """Convert a database row to a Peer object."""
    return Peer(
        server_url=row["server_url"],
        hint=row["hint"],
        last_seen=(
            datetime.fromisoformat(row["last_seen"]) if row["last_seen"] else None
        ),
        is_configured=bool(row["is_configured"]),
        authoritative_regions=(
            json.loads(row["authoritative_regions"])
            if row["authoritative_regions"]
            else None
        ),
    )
