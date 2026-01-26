"""Referral generation for federated search."""

from mrs_server.models import Location, Referral

from .peers import Peer, get_all_peers


def generate_referrals(
    location: Location,
    search_range: float,
    exclude_servers: set[str] | None = None,
) -> list[Referral]:
    """
    Generate referrals for a search query.

    The referral strategy is:
    1. Always include configured (bootstrap) peers
    2. Include learned peers if they claim authority over a region
       that intersects the search area
    3. Exclude any servers in the exclude set (e.g., servers that
       have already been queried)

    Args:
        location: Search center
        search_range: Search radius in meters
        exclude_servers: Set of server URLs to exclude

    Returns:
        List of referrals
    """
    exclude_servers = exclude_servers or set()
    referrals = []
    peers = get_all_peers()

    for peer in peers:
        # Skip excluded servers
        if peer.server_url in exclude_servers:
            continue

        # Always include configured peers
        if peer.is_configured:
            referrals.append(
                Referral(server=peer.server_url, hint=peer.hint)
            )
            continue

        # For learned peers, check if they claim authority over relevant region
        if peer.authoritative_regions:
            if _peer_covers_area(peer, location, search_range):
                referrals.append(
                    Referral(server=peer.server_url, hint=peer.hint)
                )

    return referrals


def _peer_covers_area(peer: Peer, location: Location, search_range: float) -> bool:
    """
    Check if a peer's authoritative regions intersect the search area.

    For now, this is a simple check. A more sophisticated implementation
    would do proper geometry intersection testing.

    Args:
        peer: The peer to check
        location: Search center
        search_range: Search radius in meters

    Returns:
        True if the peer might have relevant data
    """
    if not peer.authoritative_regions:
        return False

    # Import here to avoid circular dependency
    from mrs_server.geo import sphere_intersects_search
    from mrs_server.models import SphereGeometry

    for region in peer.authoritative_regions:
        # Currently only support sphere regions
        if region.get("type") == "sphere":
            try:
                sphere = SphereGeometry(
                    type="sphere",
                    center=Location(
                        lat=region["center"]["lat"],
                        lon=region["center"]["lon"],
                        ele=region["center"].get("ele", 0),
                    ),
                    radius=region["radius"],
                )
                if sphere_intersects_search(sphere, location, search_range):
                    return True
            except (KeyError, ValueError):
                # Invalid region data, skip it
                continue

    return False
