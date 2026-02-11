"""Tests for MRS API endpoints."""

from datetime import datetime, timezone

import pytest

from mrs_server.database import get_cursor


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
        assert data["registration"]["origin_server"]
        assert data["registration"]["origin_id"] == data["registration"]["id"]
        assert data["registration"]["version"] == 1

    def test_update_registration_increments_version(self, client, auth_headers):
        """Update should increment registration version."""
        create = client.post(
            "/register",
            headers=auth_headers,
            json={
                "space": {
                    "type": "sphere",
                    "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                    "radius": 50,
                },
                "service_point": "https://example.com/v1",
                "foad": False,
            },
        )
        assert create.status_code == 201
        reg = create.json()["registration"]
        assert reg["version"] == 1

        update = client.put(
            f"/register/{reg['id']}",
            headers=auth_headers,
            json={
                "space": {
                    "type": "sphere",
                    "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                    "radius": 60,
                },
                "service_point": "https://example.com/v2",
                "foad": False,
            },
        )
        assert update.status_code == 200
        updated = update.json()["registration"]
        assert updated["version"] == 2
        assert updated["origin_id"] == reg["origin_id"]

    def test_update_non_authoritative_registration_rejected(self, client, auth_headers):
        """Should reject updates for replicated (non-authoritative) registrations."""
        now = datetime.now(timezone.utc).isoformat()
        with get_cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id = (SELECT user_id FROM tokens LIMIT 1)")
            owner = cur.fetchone()["id"]
            cur.execute(
                """
                INSERT INTO registrations (
                    id, owner, geo_type,
                    center_lat, center_lon, center_ele, radius,
                    service_point, foad,
                    origin_server, origin_id, version,
                    created_at, updated_at,
                    bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon
                ) VALUES (?, ?, 'sphere', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "reg_replica_1",
                    owner,
                    -33.8568,
                    151.2153,
                    0.0,
                    50.0,
                    "https://example.com/replica",
                    0,
                    "https://origin.example",
                    "reg_origin_1",
                    3,
                    now,
                    now,
                    -33.8573,
                    -33.8563,
                    151.2148,
                    151.2158,
                ),
            )

        response = client.put(
            "/register/reg_replica_1",
            headers=auth_headers,
            json={
                "space": {
                    "type": "sphere",
                    "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                    "radius": 60,
                },
                "service_point": "https://example.com/new",
                "foad": False,
            },
        )
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["error"] == "not_authoritative"
        assert detail["origin_server"] == "https://origin.example"
        assert detail["origin_id"] == "reg_origin_1"

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

    def test_register_rejects_non_https_service_point(self, client, auth_headers):
        """Should reject non-HTTPS service_point URIs."""
        response = client.post(
            "/register",
            headers=auth_headers,
            json={
                "space": {
                    "type": "sphere",
                    "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                    "radius": 50,
                },
                "service_point": "javascript:alert(1)",
                "foad": False,
            },
        )
        assert response.status_code == 422

    def test_register_rejects_fragment_in_service_point(self, client, auth_headers):
        """Should reject service_point URIs with fragments."""
        response = client.post(
            "/register",
            headers=auth_headers,
            json={
                "space": {
                    "type": "sphere",
                    "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                    "radius": 50,
                },
                "service_point": "https://example.com/x#prompt",
                "foad": False,
            },
        )
        assert response.status_code == 422


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

    def test_release_non_authoritative_registration_rejected(self, client, auth_headers):
        """Should reject release for replicated (non-authoritative) registrations."""
        now = datetime.now(timezone.utc).isoformat()
        with get_cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id = (SELECT user_id FROM tokens LIMIT 1)")
            owner = cur.fetchone()["id"]
            cur.execute(
                """
                INSERT INTO registrations (
                    id, owner, geo_type,
                    center_lat, center_lon, center_ele, radius,
                    service_point, foad,
                    origin_server, origin_id, version,
                    created_at, updated_at,
                    bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon
                ) VALUES (?, ?, 'sphere', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "reg_replica_2",
                    owner,
                    -33.8568,
                    151.2153,
                    0.0,
                    50.0,
                    "https://example.com/replica2",
                    0,
                    "https://origin.example",
                    "reg_origin_2",
                    2,
                    now,
                    now,
                    -33.8573,
                    -33.8563,
                    151.2148,
                    151.2158,
                ),
            )

        response = client.post(
            "/release",
            headers=auth_headers,
            json={"id": "reg_replica_2"},
        )
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["error"] == "not_authoritative"
        assert detail["origin_server"] == "https://origin.example"
        assert detail["origin_id"] == "reg_origin_2"

    def test_release_nonexistent(self, client, auth_headers):
        """Should fail to release nonexistent registration."""
        response = client.post(
            "/release",
            headers=auth_headers,
            json={"id": "reg_doesnotexist"},
        )
        assert response.status_code == 404


class TestSync:
    """Tests for sync endpoints."""

    def test_sync_snapshot_returns_registrations(self, client, auth_headers):
        create = client.post(
            "/register",
            headers=auth_headers,
            json={
                "space": {
                    "type": "sphere",
                    "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                    "radius": 50,
                },
                "service_point": "https://example.com/sync-a",
                "foad": False,
            },
        )
        assert create.status_code == 201

        snap = client.get("/sync/snapshot")
        assert snap.status_code == 200
        data = snap.json()
        assert data["status"] == "ok"
        assert len(data["registrations"]) >= 1
        reg = data["registrations"][0]
        assert "origin_server" in reg
        assert "origin_id" in reg
        assert "version" in reg

    def test_sync_changes_includes_tombstones(self, client, auth_headers):
        create = client.post(
            "/register",
            headers=auth_headers,
            json={
                "space": {
                    "type": "sphere",
                    "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                    "radius": 50,
                },
                "service_point": "https://example.com/sync-b",
                "foad": False,
            },
        )
        assert create.status_code == 201
        reg_id = create.json()["registration"]["id"]

        since = "1970-01-01T00:00:00+00:00"
        changes_before = client.get("/sync/changes", params={"since": since})
        assert changes_before.status_code == 200
        assert any(r["id"] == reg_id for r in changes_before.json()["registrations"])

        rel = client.post("/release", headers=auth_headers, json={"id": reg_id})
        assert rel.status_code == 200

        changes_after = client.get("/sync/changes", params={"since": since})
        assert changes_after.status_code == 200
        tombs = changes_after.json()["tombstones"]
        assert any(t["origin_id"] == reg_id for t in tombs)


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
        reg_response = client.post(
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
        reg_data = reg_response.json()["registration"]

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
        result = data["results"][0]
        assert result["service_point"] == "https://example.com/opera-house"

        # Verify new fields are present and match registration
        assert result["owner"] == reg_data["owner"]
        assert result["origin_server"] == reg_data["origin_server"]
        assert result["origin_id"] == reg_data["origin_id"]
        assert result["version"] == reg_data["version"]
        assert result["created"] == reg_data["created"]
        assert result["updated"] == reg_data["updated"]

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

    def test_search_includes_owner_and_timestamps(self, client, auth_headers):
        """Search results should include owner, created, and updated fields."""
        # Create a registration
        reg_response = client.post(
            "/register",
            headers=auth_headers,
            json={
                "space": {
                    "type": "sphere",
                    "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                    "radius": 50,
                },
                "service_point": "https://example.com/test-space",
            },
        )
        assert reg_response.status_code == 201

        # Search for it
        search_response = client.post(
            "/search",
            json={
                "location": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
                "range": 100,
            },
        )
        assert search_response.status_code == 200
        results = search_response.json()["results"]
        assert len(results) == 1

        result = results[0]
        # Verify all required fields are present
        assert "owner" in result
        assert "origin_server" in result
        assert "origin_id" in result
        assert "version" in result
        assert "created" in result
        assert "updated" in result
        assert "id" in result
        assert "space" in result
        assert "service_point" in result
        assert "foad" in result
        assert "distance" in result

        # Verify values match the registration
        reg_data = reg_response.json()["registration"]
        assert result["owner"] == reg_data["owner"]
        assert result["origin_server"] == reg_data["origin_server"]
        assert result["origin_id"] == reg_data["origin_id"]
        assert result["version"] == reg_data["version"]
        assert result["created"] == reg_data["created"]
        assert result["updated"] == reg_data["updated"]

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
