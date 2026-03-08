"""Tests for email whitelist registration authorisation."""

import importlib
import json
import os
import tempfile
import uuid

import pytest
from fastapi.testclient import TestClient

from mrs_server.api.admin import require_localhost


@pytest.fixture(scope="function")
def whitelist_client():
    """Create a test client with whitelist enforcement enabled."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    os.environ["MRS_DATABASE_PATH"] = path
    os.environ["MRS_SERVER_URL"] = "http://testserver"
    os.environ["MRS_SERVER_DOMAIN"] = "testserver"
    os.environ["MRS_ADMIN_EMAIL"] = "admin@testserver"
    os.environ["MRS_REGISTRATION_REQUIRES_WHITELIST"] = "true"

    import mrs_server.config
    import mrs_server.database

    if mrs_server.database._connection is not None:
        mrs_server.database._connection.close()
    mrs_server.database._connection = None
    mrs_server.database._db_path = None

    importlib.reload(mrs_server.config)

    # Reload modules that import settings at module level
    import mrs_server.auth.bearer
    import mrs_server.auth
    import mrs_server.api.auth

    importlib.reload(mrs_server.auth.bearer)
    importlib.reload(mrs_server.auth)
    importlib.reload(mrs_server.api.auth)

    import mrs_server.main

    importlib.reload(mrs_server.main)

    from mrs_server.main import app

    # Override localhost guard for admin endpoints
    async def _noop():
        pass

    app.dependency_overrides[require_localhost] = _noop

    with TestClient(app) as test_client:
        yield test_client

    mrs_server.database.close_database()
    app.dependency_overrides.pop(require_localhost, None)

    # Clean up env
    os.environ.pop("MRS_REGISTRATION_REQUIRES_WHITELIST", None)
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture(autouse=True)
def _allow_admin(client):
    """Override localhost guard for whitelist admin endpoints."""
    from mrs_server.main import app

    async def _noop():
        pass

    app.dependency_overrides[require_localhost] = _noop
    yield
    app.dependency_overrides.pop(require_localhost, None)


class TestWhitelistDisabled:
    """When whitelist is disabled (default), anyone can register."""

    def test_register_without_whitelist(self, client):
        """Registration should succeed without whitelist."""
        response = client.post(
            "/auth/register",
            json={
                "username": "freeuser",
                "password": "password123",
                "email": "free@example.com",
            },
        )
        assert response.status_code == 201
        assert "token" in response.json()

    def test_register_requires_email(self, client):
        """Registration should require an email field."""
        response = client.post(
            "/auth/register",
            json={"username": "noemail", "password": "password123"},
        )
        assert response.status_code == 422

    def test_register_validates_email_format(self, client):
        """Registration should reject invalid email formats."""
        for bad_email in ["notanemail", "@nodomain", "no@", "no@domain"]:
            response = client.post(
                "/auth/register",
                json={
                    "username": f"user_{uuid.uuid4().hex[:6]}",
                    "password": "password123",
                    "email": bad_email,
                },
            )
            assert response.status_code == 422, f"Expected 422 for email: {bad_email}"

    def test_email_normalised_to_lowercase(self, client):
        """Email should be normalised to lowercase."""
        response = client.post(
            "/auth/register",
            json={
                "username": "caseuser",
                "password": "password123",
                "email": "CaseUser@Example.COM",
            },
        )
        assert response.status_code == 201


class TestWhitelistEnabled:
    """When whitelist is enabled, only whitelisted emails can register."""

    def test_register_blocked_without_whitelist_entry(self, whitelist_client):
        """Registration should be rejected if email not in whitelist."""
        response = whitelist_client.post(
            "/auth/register",
            json={
                "username": "blocked",
                "password": "password123",
                "email": "blocked@example.com",
            },
        )
        assert response.status_code == 403
        assert "not authorised" in response.json()["detail"].lower()

    def test_register_succeeds_with_whitelist_entry(self, whitelist_client):
        """Registration should succeed when email is whitelisted."""
        # Add to whitelist
        add_resp = whitelist_client.post(
            "/admin/whitelist",
            content=json.dumps({"email": "allowed@example.com"}),
            headers={"Content-Type": "application/json"},
        )
        assert add_resp.status_code == 201

        # Now register
        response = whitelist_client.post(
            "/auth/register",
            json={
                "username": "allowed",
                "password": "password123",
                "email": "allowed@example.com",
            },
        )
        assert response.status_code == 201
        assert "token" in response.json()

    def test_whitelist_case_insensitive(self, whitelist_client):
        """Whitelist check should be case-insensitive."""
        whitelist_client.post(
            "/admin/whitelist",
            content=json.dumps({"email": "Mixed@Example.COM"}),
            headers={"Content-Type": "application/json"},
        )

        response = whitelist_client.post(
            "/auth/register",
            json={
                "username": "mixedcase",
                "password": "password123",
                "email": "MIXED@example.com",
            },
        )
        assert response.status_code == 201


class TestWhitelistAdminEndpoints:
    """Tests for whitelist CRUD admin endpoints."""

    def test_list_empty_whitelist(self, client):
        """Empty whitelist should return empty list."""
        response = client.get("/admin/whitelist")
        assert response.status_code == 200
        assert response.json()["emails"] == []

    def test_add_single_email(self, client):
        """Should add a single email to the whitelist."""
        response = client.post(
            "/admin/whitelist",
            content=json.dumps({"email": "test@example.com"}),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 201
        assert response.json()["added"] == 1

        # Verify it's listed
        listing = client.get("/admin/whitelist")
        emails = [e["email"] for e in listing.json()["emails"]]
        assert "test@example.com" in emails

    def test_add_multiple_emails(self, client):
        """Should add multiple emails at once."""
        response = client.post(
            "/admin/whitelist",
            content=json.dumps({"emails": ["a@b.com", "c@d.com", "e@f.com"]}),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 201
        assert response.json()["added"] == 3

    def test_add_duplicate_email_is_idempotent(self, client):
        """Adding the same email twice should not error."""
        client.post(
            "/admin/whitelist",
            content=json.dumps({"email": "dup@example.com"}),
            headers={"Content-Type": "application/json"},
        )
        response = client.post(
            "/admin/whitelist",
            content=json.dumps({"email": "dup@example.com"}),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 201
        assert response.json()["added"] == 0

    def test_remove_email(self, client):
        """Should remove an email from the whitelist."""
        client.post(
            "/admin/whitelist",
            content=json.dumps({"email": "remove@example.com"}),
            headers={"Content-Type": "application/json"},
        )

        response = client.delete("/admin/whitelist/remove@example.com")
        assert response.status_code == 200
        assert response.json()["status"] == "removed"

        # Verify it's gone
        listing = client.get("/admin/whitelist")
        emails = [e["email"] for e in listing.json()["emails"]]
        assert "remove@example.com" not in emails

    def test_remove_nonexistent_email(self, client):
        """Removing a non-existent email should return 404."""
        response = client.delete("/admin/whitelist/nonexistent@example.com")
        assert response.status_code == 404

    def test_add_invalid_email_rejected(self, client):
        """Should reject invalid email addresses."""
        response = client.post(
            "/admin/whitelist",
            content=json.dumps({"email": "notanemail"}),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400

    def test_whitelist_localhost_guard(self, client):
        """Whitelist endpoints should be blocked for non-localhost."""
        from mrs_server.main import app

        # Remove the override so the real guard runs
        app.dependency_overrides.pop(require_localhost, None)

        response = client.get("/admin/whitelist")
        assert response.status_code == 403
