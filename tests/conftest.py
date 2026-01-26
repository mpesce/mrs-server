"""Pytest configuration and fixtures for MRS tests."""

import importlib
import os
import tempfile
import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="function")
def temp_db_path():
    """Create a temporary database path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture(scope="function")
def client(temp_db_path):
    """Create a test client with fresh database."""
    # Set environment before importing modules
    os.environ["MRS_DATABASE_PATH"] = temp_db_path
    os.environ["MRS_SERVER_URL"] = "http://testserver"
    os.environ["MRS_SERVER_DOMAIN"] = "testserver"
    os.environ["MRS_ADMIN_EMAIL"] = "admin@testserver"

    # Reset all MRS module state
    import mrs_server.config
    import mrs_server.database

    # Close any existing connection
    if mrs_server.database._connection is not None:
        mrs_server.database._connection.close()
    mrs_server.database._connection = None
    mrs_server.database._db_path = None

    # Reload config to pick up new environment
    importlib.reload(mrs_server.config)

    # Reload main to get fresh lifespan
    import mrs_server.main

    importlib.reload(mrs_server.main)

    from mrs_server.main import app

    with TestClient(app) as test_client:
        yield test_client

    # Cleanup
    mrs_server.database.close_database()


@pytest.fixture
def auth_token(client):
    """Create a test user and return their auth token."""
    # Use unique username to avoid conflicts
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    response = client.post(
        "/auth/register",
        json={"username": username, "password": "testpassword123"},
    )
    assert response.status_code == 201, f"Failed to register user: {response.json()}"
    return response.json()["token"]


@pytest.fixture
def auth_headers(auth_token):
    """Return authorization headers with the test user's token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def test_user(client):
    """Create a test user and return username and token."""
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    response = client.post(
        "/auth/register",
        json={"username": username, "password": "testpassword123"},
    )
    assert response.status_code == 201
    return {
        "username": username,
        "password": "testpassword123",
        "token": response.json()["token"],
        "identity": f"{username}@testserver",
    }
