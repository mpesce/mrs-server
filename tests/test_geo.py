"""Tests for geometry utilities."""

import math

import pytest

from mrs_server.geo import (
    bounding_box_for_search,
    compute_bounding_box,
    compute_volume,
    haversine_distance,
    sphere_contains_point,
    sphere_intersects_search,
    spheres_intersect,
)
from mrs_server.models import Location, SphereGeometry


class TestHaversineDistance:
    """Tests for haversine distance calculation."""

    def test_same_point(self):
        """Distance from a point to itself should be zero."""
        loc = Location(lat=-33.8568, lon=151.2153, ele=0)
        assert haversine_distance(loc, loc) == pytest.approx(0, abs=0.1)

    def test_known_distance(self):
        """Test against a known distance (Sydney Opera House to Harbour Bridge)."""
        opera_house = Location(lat=-33.8568, lon=151.2153, ele=0)
        harbour_bridge = Location(lat=-33.8523, lon=151.2108, ele=0)
        # These are about 700m apart
        distance = haversine_distance(opera_house, harbour_bridge)
        assert 600 < distance < 800

    def test_antipodal_points(self):
        """Distance between antipodal points should be roughly half Earth's circumference."""
        north_pole = Location(lat=90, lon=0, ele=0)
        south_pole = Location(lat=-90, lon=0, ele=0)
        # Half circumference is about 20,000 km
        distance = haversine_distance(north_pole, south_pole)
        assert 19_000_000 < distance < 21_000_000


class TestBoundingBox:
    """Tests for bounding box computation."""

    def test_small_sphere(self):
        """A small sphere should have a tight bounding box."""
        sphere = SphereGeometry(
            type="sphere",
            center=Location(lat=0, lon=0, ele=0),
            radius=1000,  # 1km
        )
        bbox = compute_bounding_box(sphere)

        # Should be roughly symmetric around center
        assert bbox.min_lat < 0 < bbox.max_lat
        assert bbox.min_lon < 0 < bbox.max_lon

        # Should be small (1km radius ~ 0.009 degrees)
        assert (bbox.max_lat - bbox.min_lat) < 0.1
        assert (bbox.max_lon - bbox.min_lon) < 0.1

    def test_near_pole(self):
        """Bounding box near pole should have wide longitude range."""
        sphere = SphereGeometry(
            type="sphere",
            center=Location(lat=89, lon=0, ele=0),
            radius=10000,  # 10km
        )
        bbox = compute_bounding_box(sphere)

        # Longitude range should be wider due to convergence
        lon_range = bbox.max_lon - bbox.min_lon
        assert lon_range > 1  # Much wider than at equator


class TestSphereIntersection:
    """Tests for sphere intersection."""

    def test_point_inside_sphere(self):
        """A point inside a sphere should be contained."""
        sphere = SphereGeometry(
            type="sphere",
            center=Location(lat=0, lon=0, ele=0),
            radius=1000,
        )
        point = Location(lat=0.001, lon=0.001, ele=0)
        assert sphere_contains_point(sphere, point)

    def test_point_outside_sphere(self):
        """A point outside a sphere should not be contained."""
        sphere = SphereGeometry(
            type="sphere",
            center=Location(lat=0, lon=0, ele=0),
            radius=100,  # 100m
        )
        point = Location(lat=1, lon=1, ele=0)  # ~157km away
        assert not sphere_contains_point(sphere, point)

    def test_overlapping_spheres(self):
        """Two overlapping spheres should intersect."""
        s1 = SphereGeometry(
            type="sphere",
            center=Location(lat=0, lon=0, ele=0),
            radius=1000,
        )
        s2 = SphereGeometry(
            type="sphere",
            center=Location(lat=0.01, lon=0, ele=0),  # ~1.1km away
            radius=1000,
        )
        assert spheres_intersect(s1, s2)

    def test_non_overlapping_spheres(self):
        """Two distant spheres should not intersect."""
        s1 = SphereGeometry(
            type="sphere",
            center=Location(lat=0, lon=0, ele=0),
            radius=100,
        )
        s2 = SphereGeometry(
            type="sphere",
            center=Location(lat=1, lon=1, ele=0),
            radius=100,
        )
        assert not spheres_intersect(s1, s2)


class TestSearchIntersection:
    """Tests for search area intersection."""

    def test_sphere_in_search_area(self):
        """A sphere within the search range should intersect."""
        sphere = SphereGeometry(
            type="sphere",
            center=Location(lat=-33.8568, lon=151.2153, ele=0),
            radius=50,
        )
        search_center = Location(lat=-33.8570, lon=151.2155, ele=0)
        search_range = 100

        assert sphere_intersects_search(sphere, search_center, search_range)

    def test_sphere_outside_search_area(self):
        """A sphere outside the search range should not intersect."""
        sphere = SphereGeometry(
            type="sphere",
            center=Location(lat=-33.8568, lon=151.2153, ele=0),
            radius=50,
        )
        search_center = Location(lat=-33.8600, lon=151.2200, ele=0)  # ~500m away
        search_range = 100

        assert not sphere_intersects_search(sphere, search_center, search_range)


class TestVolume:
    """Tests for volume computation."""

    def test_volume_formula(self):
        """Volume should follow the sphere volume formula."""
        radius = 100
        sphere = SphereGeometry(
            type="sphere",
            center=Location(lat=0, lon=0, ele=0),
            radius=radius,
        )

        expected = (4 / 3) * math.pi * (radius**3)
        assert compute_volume(sphere) == pytest.approx(expected)

    def test_larger_sphere_larger_volume(self):
        """A larger sphere should have greater volume."""
        small = SphereGeometry(
            type="sphere",
            center=Location(lat=0, lon=0, ele=0),
            radius=10,
        )
        large = SphereGeometry(
            type="sphere",
            center=Location(lat=0, lon=0, ele=0),
            radius=100,
        )

        assert compute_volume(large) > compute_volume(small)
