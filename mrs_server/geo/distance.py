"""Distance calculations using the Haversine formula."""

import math

from mrs_server.models import Location

from .constants import EARTH_RADIUS_M


def haversine_distance(loc1: Location, loc2: Location) -> float:
    """
    Calculate the great-circle distance between two points on Earth.

    Uses the Haversine formula for accuracy at all distances.

    Args:
        loc1: First location
        loc2: Second location

    Returns:
        Distance in meters
    """
    lat1 = math.radians(loc1.lat)
    lon1 = math.radians(loc1.lon)
    lat2 = math.radians(loc2.lat)
    lon2 = math.radians(loc2.lon)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return EARTH_RADIUS_M * c


def distance_3d(loc1: Location, loc2: Location) -> float:
    """
    Calculate 3D distance including elevation difference.

    For most MRS use cases, the 2D haversine distance is sufficient,
    but this can be useful for precise vertical positioning.

    Args:
        loc1: First location
        loc2: Second location

    Returns:
        Distance in meters including elevation
    """
    horizontal = haversine_distance(loc1, loc2)
    vertical = abs(loc1.ele - loc2.ele)

    return math.sqrt(horizontal**2 + vertical**2)
