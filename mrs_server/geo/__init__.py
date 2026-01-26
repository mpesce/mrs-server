"""Geometry utilities for spatial operations."""

from .bbox import bounding_box_for_search, bounding_boxes_intersect, compute_bounding_box
from .constants import EARTH_RADIUS_M
from .distance import distance_3d, haversine_distance
from .intersect import (
    compute_volume,
    sphere_contains_point,
    sphere_intersects_search,
    spheres_intersect,
)

__all__ = [
    "EARTH_RADIUS_M",
    "haversine_distance",
    "distance_3d",
    "compute_bounding_box",
    "bounding_box_for_search",
    "bounding_boxes_intersect",
    "sphere_contains_point",
    "spheres_intersect",
    "sphere_intersects_search",
    "compute_volume",
]
