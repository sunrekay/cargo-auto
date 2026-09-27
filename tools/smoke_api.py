"""Hit every endpoint and fail loudly on any non-200.

The API runs against Postgres in development and against the SQLite file in
production. A column present in one and absent from the other only shows up as
a 500 on a single route, which is easy to miss — this walks them all.

    python -m tools.smoke_api http://localhost:8000
"""
import json
import sys
import urllib.error
import urllib.request


def get(base: str, path: str):
    try:
        with urllib.request.urlopen(base + path, timeout=20) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:120].decode("utf-8", "replace")
    except Exception as e:                       # noqa: BLE001
        return 0, str(e)


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")

    status, health = get(base, "/api/health")
    if status != 200:
        print(f"FAIL /api/health -> {status} {health}")
        return 1
    print(f"  /api/health          200  engine={health.get('engine')} cars={health.get('cars')}")

    status, page = get(base, "/api/cars?limit=3")
    if status != 200 or not page.get("items"):
        print(f"FAIL /api/cars -> {status} {page}")
        return 1
    print(f"  /api/cars            200  total={page['total']}")

    routes = ["/api/brands", "/api/models", "/api/filters",
              "/api/cars?brand=toyota&sort=price_asc&limit=2",
              "/api/cars?max_price=6000", "/api/cars?q=golf"]
    # the detail route for a real car, which is where a schema mismatch bites
    routes += [f"/api/cars/{c['id']}" for c in page["items"]]

    failed = 0
    for route in routes:
        status, body = get(base, route)
        ok = status == 200
        failed += not ok
        extra = ""
        if ok and isinstance(body, dict) and "photos" in body:
            extra = f"photos={len(body['photos'])} specs={body.get('spec_count')}"
        elif ok and isinstance(body, list):
            extra = f"{len(body)} items"
        print(f"  {'' if ok else 'FAIL '}{route:42.42s} {status}  {extra}"
              + ("" if ok else f"  {body}"))

    print(f"\n  {len(routes) + 2 - failed}/{len(routes) + 2} endpoints OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
