# Static MRS (Level 0)

Level 0 provides a static JSON export of registrations for simple publishing/discovery.

## Export from server DB

```bash
python scripts/export-static-snapshot.py --db ./mrs.db --out ./mrs-static.json
```

Host `mrs-static.json` at a well-known URL (e.g. `https://example.com/.well-known/mrs-static.json`).

## Intended scope
- simple bootstrap datasets
- read-only distribution
- no auth or mutation semantics
- no cross-server conflict guarantees

For full dynamic behavior and federation consistency, use `mrs-server` API + sync endpoints.
