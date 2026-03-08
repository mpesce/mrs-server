"""Tests for admin export/import endpoints."""

import json

import pytest

def _get_require_localhost():
    """Get the current require_localhost dependency (survives module reloads)."""
    from mrs_server.api.admin import require_localhost

    return require_localhost


@pytest.fixture(autouse=True)
def _allow_test_client(client):
    """Override the localhost guard so the TestClient (host='testclient') is allowed."""
    from mrs_server.main import app

    async def _noop():
        pass

    guard = _get_require_localhost()
    app.dependency_overrides[guard] = _noop
    yield
    app.dependency_overrides.pop(guard, None)


class TestLocalhostGuard:
    """Admin endpoints must reject non-loopback clients."""

    def test_export_blocked_without_override(self, client):
        """When the guard is restored, non-localhost should be 403."""
        from mrs_server.main import app

        # Remove the override so the real guard runs
        app.dependency_overrides.pop(_get_require_localhost(), None)

        response = client.get("/admin/export")
        assert response.status_code == 403
        assert "localhost" in response.json()["detail"].lower()

    def test_import_blocked_without_override(self, client):
        """When the guard is restored, non-localhost should be 403."""
        from mrs_server.main import app

        app.dependency_overrides.pop(_get_require_localhost(), None)

        response = client.post(
            "/admin/import",
            content=json.dumps({"registrations": [], "tombstones": [], "peers": []}),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 403

    def test_export_allowed_with_localhost(self, client):
        """With override (simulating localhost), export should succeed."""
        response = client.get("/admin/export")
        assert response.status_code == 200

    def test_import_allowed_with_localhost(self, client):
        """With override (simulating localhost), import should succeed."""
        response = client.post(
            "/admin/import",
            content=json.dumps({"registrations": [], "tombstones": [], "peers": []}),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200


class TestExportEmpty:
    """Export from a fresh database."""

    def test_export_structure(self, client):
        response = client.get("/admin/export")
        assert response.status_code == 200
        data = response.json()
        assert data["mrs_version"] == "0.5.0"
        assert "exported_at" in data
        assert data["registrations"] == []
        assert data["tombstones"] == []


class TestRoundTrip:
    """Export then import should be perfectly reflexive."""

    def _register(self, client, auth_headers, lat, lon, radius, service_point):
        return client.post(
            "/register",
            headers=auth_headers,
            json={
                "space": {
                    "type": "sphere",
                    "center": {"lat": lat, "lon": lon, "ele": 0},
                    "radius": radius,
                },
                "service_point": service_point,
                "foad": False,
            },
        )

    def test_export_contains_registrations(self, client, auth_headers):
        """Export should include all registrations."""
        r1 = self._register(client, auth_headers, -33.8568, 151.2153, 50, "https://example.com/a")
        r2 = self._register(client, auth_headers, 40.7128, -74.0060, 100, "https://example.com/b")
        assert r1.status_code == 201
        assert r2.status_code == 201

        export = client.get("/admin/export").json()
        assert len(export["registrations"]) == 2
        ids = {r["id"] for r in export["registrations"]}
        assert r1.json()["registration"]["id"] in ids
        assert r2.json()["registration"]["id"] in ids

    def test_full_round_trip(self, client, auth_headers):
        """Export -> import into same DB should be idempotent."""
        self._register(client, auth_headers, -33.8568, 151.2153, 50, "https://example.com/opera")
        self._register(client, auth_headers, 51.5074, -0.1278, 200, "https://example.com/london")

        export_data = client.get("/admin/export").json()
        assert len(export_data["registrations"]) == 2

        # Import the same data back (upsert - should not duplicate)
        import_resp = client.post(
            "/admin/import",
            content=json.dumps(export_data),
            headers={"Content-Type": "application/json"},
        )
        assert import_resp.status_code == 200
        counts = import_resp.json()
        assert counts["registrations"] == 2

        # Export again - should still be exactly 2
        export_after = client.get("/admin/export").json()
        assert len(export_after["registrations"]) == 2

    def test_round_trip_preserves_fields(self, client, auth_headers):
        """All fields should survive a round trip exactly."""
        self._register(client, auth_headers, -33.8568, 151.2153, 50, "https://example.com/exact")

        export_data = client.get("/admin/export").json()
        original = export_data["registrations"][0]

        # Import into the same DB
        client.post(
            "/admin/import",
            content=json.dumps(export_data),
            headers={"Content-Type": "application/json"},
        )

        # Export again and compare
        re_export = client.get("/admin/export").json()
        restored = re_export["registrations"][0]

        assert original["id"] == restored["id"]
        assert original["owner"] == restored["owner"]
        assert original["space"] == restored["space"]
        assert original["service_point"] == restored["service_point"]
        assert original["foad"] == restored["foad"]
        assert original["origin_server"] == restored["origin_server"]
        assert original["origin_id"] == restored["origin_id"]
        assert original["version"] == restored["version"]
        assert original["created"] == restored["created"]
        assert original["updated"] == restored["updated"]

    def test_round_trip_with_tombstones(self, client, auth_headers):
        """Tombstones from releases should round-trip."""
        reg = self._register(client, auth_headers, -33.8568, 151.2153, 50, "https://example.com/doomed")
        reg_id = reg.json()["registration"]["id"]

        client.post("/release", headers=auth_headers, json={"id": reg_id})

        export_data = client.get("/admin/export").json()
        assert len(export_data["tombstones"]) >= 1

        tomb = next(t for t in export_data["tombstones"] if t["origin_id"] == reg_id)

        # Re-import
        client.post(
            "/admin/import",
            content=json.dumps(export_data),
            headers={"Content-Type": "application/json"},
        )

        re_export = client.get("/admin/export").json()
        re_tomb = next(t for t in re_export["tombstones"] if t["origin_id"] == reg_id)
        assert tomb == re_tomb

    def test_round_trip_with_peers(self, client):
        """Peers should round-trip."""
        peer_data = {
            "registrations": [],
            "tombstones": [],
            "peers": [
                {
                    "server_url": "https://sydney.mrs.example",
                    "hint": "Sydney metro",
                    "last_seen": "2026-03-07T00:00:00+00:00",
                    "is_configured": False,
                    "authoritative_regions": None,
                },
            ],
        }
        resp = client.post(
            "/admin/import",
            content=json.dumps(peer_data),
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200

        export_data = client.get("/admin/export").json()
        urls = {p["server_url"] for p in export_data["peers"]}
        assert "https://sydney.mrs.example" in urls

    def test_search_finds_imported_data(self, client, auth_headers):
        """Data loaded via import should be searchable."""
        self._register(client, auth_headers, -33.8568, 151.2153, 50, "https://example.com/imported")
        export_data = client.get("/admin/export").json()

        reg_id = export_data["registrations"][0]["id"]
        client.post("/release", headers=auth_headers, json={"id": reg_id})

        # Verify it's gone
        search_gone = client.post(
            "/search",
            json={"location": {"lat": -33.8568, "lon": 151.2153, "ele": 0}, "range": 100},
        )
        assert len(search_gone.json()["results"]) == 0

        # Re-import (strip tombstones so it's not conflicted)
        export_data["tombstones"] = []
        client.post(
            "/admin/import",
            content=json.dumps(export_data),
            headers={"Content-Type": "application/json"},
        )

        # Now searchable again
        search_back = client.post(
            "/search",
            json={"location": {"lat": -33.8568, "lon": 151.2153, "ele": 0}, "range": 100},
        )
        assert len(search_back.json()["results"]) == 1
        assert search_back.json()["results"][0]["service_point"] == "https://example.com/imported"
