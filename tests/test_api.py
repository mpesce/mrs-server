"""Tests for MRS API endpoints."""

import pytest


class TestRootEndpoints:
    """Tests for root and health endpoints."""

    def test_root(self, client):
        """Root endpoint should return server info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "MRS Server"
        assert "version" in data

    def test_health(self, client):
        """Health endpoint should return healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestAuth:
    """Tests for authentication endpoints."""

    def test_register_user(self, client):
        """Should be able to register a new user."""
        response = client.post(
            "/auth/register",
            json={"username": "newuser", "password": "password123"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "token" in data

    def test_register_duplicate_user(self, client):
        """Should not be able to register duplicate username."""
        # Register first
        response1 = client.post(
            "/auth/register",
            json={"username": "duplicateuser", "password": "password123"},
        )
        assert response1.status_code == 201

        # Try to register same username again
        response2 = client.post(
            "/auth/register",
            json={"username": "duplicateuser", "password": "password123"},
        )
        assert response2.status_code == 400

    def test_login(self, client, test_user):
        """Should be able to login with valid credentials."""
        response = client.post(
            "/auth/login",
            json={"username": test_user["username"], "password": test_user["password"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data

    def test_login_wrong_password(self, client, test_user):
        """Should not login with wrong password."""
        response = client.post(
            "/auth/login",
            json={"username": test_user["username"], "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_get_me(self, client, test_user):
        """Should get current user info with valid token."""
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user["identity"]
        assert data["is_local"] is True

    def test_get_me_no_auth(self, client):
        """Should fail without authentication."""
        response = client.get("/auth/me")
        assert response.status_code == 401


class TestRegistration:
    """Tests for registration endpoints."""

    def test_register_space(self, client, test_user):
        """Should be able to register a space."""
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        response = client.post(
            "/register",
            headers=headers,
            json={
                "space": {
                    "type": "sphere",
                    "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                    "radius": 50,
                },
                "service_point": "https://example.com/my-space",
                "foad": False,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "registered"
        assert data["registration"]["id"].startswith("reg_")
        assert data["registration"]["owner"] == test_user["identity"]

    def test_register_space_foad(self, client, auth_headers):
        """Should be able to register with foad=true and no service_point."""
        response = client.post(
            "/register",
            headers=auth_headers,
            json={
                "space": {
                    "type": "sphere",
                    "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                    "radius": 50,
                },
                "foad": True,
            },
        )
        assert response.status_code == 201

    def test_register_space_missing_service_point(self, client, auth_headers):
        """Should fail without service_point when foad=false."""
        response = client.post(
            "/register",
            headers=auth_headers,
            json={
                "space": {
                    "type": "sphere",
                    "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                    "radius": 50,
                },
                "foad": False,
            },
        )
        assert response.status_code == 400

    def test_register_space_no_auth(self, client):
        """Should fail without authentication."""
        response = client.post(
            "/register",
            json={
                "space": {
                    "type": "sphere",
                    "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                    "radius": 50,
                },
                "service_point": "https://example.com/my-space",
            },
        )
        assert response.status_code == 401

    def test_register_invalid_coordinates(self, client, auth_headers):
        """Should reject invalid coordinates."""
        response = client.post(
            "/register",
            headers=auth_headers,
            json={
                "space": {
                    "type": "sphere",
                    "center": {"lat": 100, "lon": 200, "ele": 0},  # Invalid
                    "radius": 50,
                },
                "service_point": "https://example.com/my-space",
            },
        )
        assert response.status_code == 422  # Validation error


class TestRelease:
    """Tests for release endpoint."""

    def test_release_own_registration(self, client, auth_headers):
        """Should be able to release own registration."""
        # First create a registration
        create_response = client.post(
            "/register",
            headers=auth_headers,
            json={
                "space": {
                    "type": "sphere",
                    "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                    "radius": 50,
                },
                "service_point": "https://example.com/my-space",
            },
        )
        reg_id = create_response.json()["registration"]["id"]

        # Release it
        response = client.post(
            "/release",
            headers=auth_headers,
            json={"id": reg_id},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "released"

    def test_release_nonexistent(self, client, auth_headers):
        """Should fail to release nonexistent registration."""
        response = client.post(
            "/release",
            headers=auth_headers,
            json={"id": "reg_doesnotexist"},
        )
        assert response.status_code == 404


class TestSearch:
    """Tests for search endpoint."""

    def test_search_empty(self, client):
        """Search with no registrations should return empty results."""
        response = client.post(
            "/search",
            json={
                "location": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                "range": 100,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["results"] == []

    def test_search_finds_registration(self, client, auth_headers):
        """Search should find nearby registrations."""
        # Create a registration
        client.post(
            "/register",
            headers=auth_headers,
            json={
                "space": {
                    "type": "sphere",
                    "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                    "radius": 50,
                },
                "service_point": "https://example.com/opera-house",
            },
        )

        # Search near it
        response = client.post(
            "/search",
            json={
                "location": {"lat": -33.8570, "lon": 151.2155, "ele": 0},
                "range": 100,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["service_point"] == "https://example.com/opera-house"

    def test_search_excludes_foad(self, client, auth_headers):
        """Search should not return foad registrations."""
        # Create a foad registration
        client.post(
            "/register",
            headers=auth_headers,
            json={
                "space": {
                    "type": "sphere",
                    "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                    "radius": 50,
                },
                "foad": True,
            },
        )

        # Search should find nothing
        response = client.post(
            "/search",
            json={
                "location": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                "range": 100,
            },
        )
        assert response.status_code == 200
        assert len(response.json()["results"]) == 0

    def test_search_sorts_by_volume(self, client, auth_headers):
        """Search results should be sorted by volume (smallest first)."""
        # Create a large registration
        client.post(
            "/register",
            headers=auth_headers,
            json={
                "space": {
                    "type": "sphere",
                    "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                    "radius": 500,
                },
                "service_point": "https://example.com/large",
            },
        )

        # Create a small registration
        client.post(
            "/register",
            headers=auth_headers,
            json={
                "space": {
                    "type": "sphere",
                    "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                    "radius": 10,
                },
                "service_point": "https://example.com/small",
            },
        )

        # Search
        response = client.post(
            "/search",
            json={
                "location": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                "range": 1000,
            },
        )
        results = response.json()["results"]
        assert len(results) == 2
        # Smallest should be first
        assert results[0]["service_point"] == "https://example.com/small"
        assert results[1]["service_point"] == "https://example.com/large"


class TestWellKnown:
    """Tests for well-known endpoints."""

    def test_well_known_mrs(self, client):
        """Should return server metadata."""
        response = client.get("/.well-known/mrs")
        assert response.status_code == 200
        data = response.json()
        assert data["mrs_version"] == "0.5.0"
        assert data["server"] == "http://testserver"
        assert "capabilities" in data
        assert "sphere" in data["capabilities"]["geometry_types"]

    def test_server_key(self, client):
        """Should return server public key."""
        response = client.get("/.well-known/mrs/keys/_server")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "_server@testserver"
        assert data["public_key"]["type"] == "Ed25519"
        assert "key" in data["public_key"]
