"""Search endpoint for MRS."""

from fastapi import APIRouter

from mrs_server.config import settings
from mrs_server.database import get_cursor
from mrs_server.federation import generate_referrals
from mrs_server.geo import (
    bounding_box_for_search,
    compute_volume,
    haversine_distance,
    sphere_intersects_search,
)
from mrs_server.models import (
    Location,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SphereGeometry,
)

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search_registrations(request: SearchRequest) -> SearchResponse:
    """
    Search for registrations near a location.

    This endpoint is public and does not require authentication.
    It returns:
    - All non-foad registrations that intersect the search area
    - Referrals to other MRS servers that may have additional results
    """
    # Compute search bounding box for database query
    search_bbox = bounding_box_for_search(request.location, request.range)

    # Query registrations with overlapping bounding boxes
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT * FROM registrations
            WHERE foad = 0
              AND bbox_max_lat >= ?
              AND bbox_min_lat <= ?
              AND bbox_max_lon >= ?
              AND bbox_min_lon <= ?
            """,
            (
                search_bbox.min_lat,
                search_bbox.max_lat,
                search_bbox.min_lon,
                search_bbox.max_lon,
            ),
        )
        rows = cursor.fetchall()

    # Filter by actual geometry intersection and compute distances
    results = []
    for row in rows:
        sphere = SphereGeometry(
            type="sphere",
            center=Location(
                lat=row["center_lat"],
                lon=row["center_lon"],
                ele=row["center_ele"],
            ),
            radius=row["radius"],
        )

        # Check actual intersection (bounding box is just an approximation)
        if not sphere_intersects_search(sphere, request.location, request.range):
            continue

        # Compute distance from query point to sphere center
        distance = haversine_distance(request.location, sphere.center)

        results.append(
            SearchResult(
                id=row["id"],
                space=sphere,
                service_point=row["service_point"],
                foad=bool(row["foad"]),
                distance=distance,
                owner=row["owner"],
                created=row["created_at"],
                updated=row["updated_at"],
            )
        )

    # Sort by volume (smallest first), then by distance
    results.sort(key=lambda r: (compute_volume(r.space), r.distance))

    # Limit results
    results = results[: settings.max_results]

    # Generate referrals to other servers
    referrals = generate_referrals(
        location=request.location,
        search_range=request.range,
        exclude_servers={settings.server_url},  # Don't refer to ourselves
    )

    return SearchResponse(results=results, referrals=referrals)
