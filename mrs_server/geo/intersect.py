"""Geometry intersection tests."""

from mrs_server.models import Location, SphereGeometry

from .distance import haversine_distance


def sphere_contains_point(sphere: SphereGeometry, point: Location) -> bool:
    """
    Test if a point is inside a sphere.

    Args:
        sphere: The sphere geometry
        point: The point to test

    Returns:
        True if the point is within the sphere's radius of its center
    """
    distance = haversine_distance(sphere.center, point)
    return distance <= sphere.radius


def spheres_intersect(sphere1: SphereGeometry, sphere2: SphereGeometry) -> bool:
    """
    Test if two spheres intersect.

    Args:
        sphere1: First sphere
        sphere2: Second sphere

    Returns:
        True if the spheres overlap
    """
    distance = haversine_distance(sphere1.center, sphere2.center)
    return distance <= (sphere1.radius + sphere2.radius)


def sphere_intersects_search(
    sphere: SphereGeometry, search_center: Location, search_range: float
) -> bool:
    """
    Test if a sphere intersects with a search area.

    The search area is treated as a sphere centered on search_center
    with radius search_range.

    Args:
        sphere: The registered sphere
        search_center: Center of the search
        search_range: Search radius in meters

    Returns:
        True if the sphere overlaps the search area
    """
    distance = haversine_distance(sphere.center, search_center)
    return distance <= (sphere.radius + search_range)


def compute_volume(sphere: SphereGeometry) -> float:
    """
    Compute the volume of a sphere in cubic meters.

    Used for sorting search results (smaller volumes first).

    Args:
        sphere: The sphere geometry

    Returns:
        Volume in cubic meters
    """
    import math

    return (4 / 3) * math.pi * (sphere.radius**3)
