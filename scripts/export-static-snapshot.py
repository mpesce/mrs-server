#!/usr/bin/env python3
"""Export current registrations as Level-0 static MRS JSON."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from mrs_server.database import init_database, get_cursor, close_database


def main() -> int:
    p = argparse.ArgumentParser(description="Export static MRS snapshot")
    p.add_argument("--db", default="./mrs.db", help="SQLite database path")
    p.add_argument("--out", required=True, help="Output JSON path")
    args = p.parse_args()

    init_database(args.db)
    try:
        with get_cursor() as cur:
            cur.execute(
                """
                SELECT id, owner, center_lat, center_lon, center_ele, radius,
                       service_point, foad, created_at, updated_at,
                       origin_server, origin_id, version
                FROM registrations
                ORDER BY updated_at DESC
                """
            )
            rows = cur.fetchall()

        regs = []
        for r in rows:
            regs.append(
                {
                    "id": r["id"],
                    "space": {
                        "type": "sphere",
                        "center": {
                            "lat": r["center_lat"],
                            "lon": r["center_lon"],
                            "ele": r["center_ele"],
                        },
                        "radius": r["radius"],
                    },
                    "service_point": r["service_point"],
                    "foad": bool(r["foad"]),
                    "owner": r["owner"],
                    "origin_server": r["origin_server"],
                    "origin_id": r["origin_id"],
                    "version": int(r["version"]),
                    "created": r["created_at"],
                    "updated": r["updated_at"],
                }
            )

        payload = {
            "mrs_static_version": "0.1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "registrations": regs,
        }

        out = Path(args.out)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {len(regs)} registrations to {out}")
        return 0
    finally:
        close_database()


if __name__ == "__main__":
    raise SystemExit(main())
