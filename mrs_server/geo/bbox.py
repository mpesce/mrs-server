"""Bounding box computation for spatial indexing."""

import math

from mrs_server.models import BoundingBox, Location, SphereGeometry

from .constants import EARTH_RADIUS_M


def compute_bounding_box(geometry: SphereGeometry) -> BoundingBox:
    """
    Compute an axis-aligned bounding box for a sphere geometry.

    The bounding box is used for efficient spatial indexing in the database.
    It's an approximation that may include areas outside the actual sphere,
    but will never exclude areas inside the sphere.

    Args:
        geometry: A sphere geometry

    Returns:
        Bounding box that contains the entire sphere
    """
    center = geometry.center
    radius = geometry.radius

    # Convert radius in meters to degrees latitude
    # This is constant regardless of longitude
    lat_delta = (radius / EARTH_RADIUS_M) * (180 / math.pi)

    # Convert radius to degrees longitude
    # This varies with latitude - at higher latitudes, degrees of longitude
    # cover less distance, so we need more degrees for the same radius
    # Handle edge case near poles where cos approaches 0
    cos_lat = math.cos(math.radians(center.lat))
    if cos_lat < 0.001:  # Very close to pole
        lon_delta = 180  # Entire longitude range
    else:
        lon_delta = lat_delta / cos_lat

    return BoundingBox(
        min_lat=max(-90, center.lat - lat_delta),
        max_lat=min(90, center.lat + lat_delta),
        min_lon=max(-180, center.lon - lon_delta),
        max_lon=min(180, center.lon + lon_delta),
    )


def bounding_box_for_search(location: Location, range_m: float) -> BoundingBox:
    """
    Compute a bounding box for a search query.

    Args:
        location: Center of the search
        range_m: Search radius in meters

    Returns:
        Bounding box for the search area
    """
    # Create a temporary sphere geometry to reuse the computation
    temp_geo = SphereGeometry(type="sphere", center=location, radius=range_m)
    return compute_bounding_box(temp_geo)


def bounding_boxes_intersect(box1: BoundingBox, box2: BoundingBox) -> bool:
    """
    Test if two bounding boxes intersect.

    Args:
        box1: First bounding box
        box2: Second bounding box

    Returns:
        True if the boxes overlap
    """
    # Check for no overlap conditions
    if box1.max_lat < box2.min_lat or box1.min_lat > box2.max_lat:
        return False
    if box1.max_lon < box2.min_lon or box1.min_lon > box2.max_lon:
        return False
    return True
