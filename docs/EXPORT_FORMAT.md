# MRS Export Format

**Version:** 0.5.0
**Purpose:** JSON schema for the bulk export/import endpoints

---

## Overview

The export format is a single JSON document containing the complete state of an MRS server's registry. It is produced by `GET /admin/export` and consumed by `POST /admin/import`. The format is fully reflexive: exporting and re-importing produces identical state.

---

## Top-Level Structure

```json
{
  "mrs_version": "0.5.0",
  "exported_at": "2026-03-07T12:00:00.000000+00:00",
  "server": "https://owen.iz.net",
  "registrations": [],
  "tombstones": [],
  "peers": []
}
```

| Field | Type | Description |
|-------|------|-------------|
| `mrs_version` | string | Schema version. Used to detect format changes. |
| `exported_at` | string (ISO 8601) | Timestamp of when the export was generated. |
| `server` | string (URI) | The server URL that produced this export. |
| `registrations` | array | All spatial registrations. See [Registration](#registration). |
| `tombstones` | array | Delete records for sync consistency. See [Tombstone](#tombstone). |
| `peers` | array | Known federation peers. See [Peer](#peer). |

On import, only `registrations`, `tombstones`, and `peers` are required. The envelope fields (`mrs_version`, `exported_at`, `server`) are informational and ignored by the import endpoint.

---

## Registration

Each registration binds a geographic sphere to a service URI.

```json
{
  "id": "reg_a1b2c3d4e5f6",
  "owner": "mark@owen.iz.net",
  "space": {
    "type": "sphere",
    "center": {
      "lat": -33.85939,
      "lon": 151.20458,
      "ele": 10.0
    },
    "radius": 50.0
  },
  "service_point": "https://example.com/spaces/sydney-opera-house",
  "foad": false,
  "origin_server": "https://owen.iz.net",
  "origin_id": "reg_a1b2c3d4e5f6",
  "version": 1,
  "created": "2026-01-15T10:30:00+00:00",
  "updated": "2026-01-15T10:30:00+00:00"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique registration identifier. Format: `reg_` + 12 URL-safe characters. |
| `owner` | string | Yes | MRS identity of the registrant (`user@domain`). |
| `space` | object | Yes | The spatial geometry. See [Space](#space). |
| `service_point` | string or null | No | HTTPS URI for the service at this location. Required if `foad` is false. |
| `foad` | boolean | Yes | If true, the space is registered but provides no services ("Fuck Off And Die"). |
| `origin_server` | string | No | URL of the server that created this registration. Defaults to `""`. |
| `origin_id` | string | No | Original registration ID on the origin server. Defaults to `id`. |
| `version` | integer | No | Monotonically increasing version number. Defaults to `1`. |
| `created` | string (ISO 8601) | Yes | When the registration was first created. |
| `updated` | string (ISO 8601) | Yes | When the registration was last modified. |

### Space

Currently only sphere geometry is supported.

```json
{
  "type": "sphere",
  "center": {
    "lat": -33.85939,
    "lon": 151.20458,
    "ele": 10.0
  },
  "radius": 50.0
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"sphere"` for now. |
| `center` | object | Center point of the sphere. |
| `center.lat` | float | Latitude in degrees. Range: -90.0 to 90.0. |
| `center.lon` | float | Longitude in degrees. Range: -180.0 to 180.0. |
| `center.ele` | float | Elevation in meters above sea level. Default: 0. |
| `radius` | float | Radius in meters. Range: >0 to 1,000,000. |

---

## Tombstone

A tombstone records that a registration was deleted. Used for sync consistency between federated servers.

```json
{
  "origin_server": "https://owen.iz.net",
  "origin_id": "reg_a1b2c3d4e5f6",
  "version": 2,
  "deleted_at": "2026-02-01T08:00:00+00:00"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `origin_server` | string | Yes | The server that originally created the deleted registration. |
| `origin_id` | string | Yes | The original registration ID. |
| `version` | integer | Yes | Version at time of deletion (original version + 1). |
| `deleted_at` | string (ISO 8601) | Yes | When the registration was deleted. |

---

## Peer

A known federation peer server.

```json
{
  "server_url": "https://sydney.mrs.example",
  "hint": "Authoritative for Sydney metropolitan area",
  "last_seen": "2026-03-01T00:00:00+00:00",
  "is_configured": false,
  "authoritative_regions": [
    {
      "type": "sphere",
      "center": {"lat": -33.8688, "lon": 151.2093, "ele": 0},
      "radius": 50000
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `server_url` | string | Yes | The peer's base URL. |
| `hint` | string or null | No | Human-readable description of the peer. |
| `last_seen` | string (ISO 8601) or null | No | When we last communicated with this peer. |
| `is_configured` | boolean | No | `true` if manually configured as a bootstrap peer. Default: false. |
| `authoritative_regions` | array or null | No | Geometry objects describing regions the peer claims authority over. Same format as [Space](#space). |

---

## Import Behaviour

- **Upsert semantics**: If a registration ID already exists, it is updated. If new, it is inserted.
- **Idempotent**: Importing the same file multiple times produces identical state.
- **Bounding boxes**: Recomputed on import from the geometry, so they are not included in the format.
- **Tombstone conflict resolution**: On conflict, the higher version number wins.
- **Peer merge**: On conflict, configured status is preserved (`MAX`), hints and regions use `COALESCE`.

---

## Example: Minimal Valid Import

The smallest valid import document:

```json
{
  "registrations": [
    {
      "id": "reg_test12345678",
      "owner": "admin@owen.iz.net",
      "space": {
        "type": "sphere",
        "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
        "radius": 50
      },
      "service_point": "https://example.com/test",
      "foad": false,
      "created": "2026-03-07T00:00:00+00:00",
      "updated": "2026-03-07T00:00:00+00:00"
    }
  ]
}
```

The `tombstones` and `peers` arrays default to empty if omitted.
