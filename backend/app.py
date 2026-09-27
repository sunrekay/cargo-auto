"""Storefront API over the parsed car catalogue.

Serves the data the crawler collected: listings with filters, a full detail
record (every characteristic the source page carried), and the photos — from
object storage when they have been uploaded, from local disk otherwise.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import db, mapping, queries

MEDIA_DIR = Path(os.getenv("MEDIA_DIR", "data/images"))
MEDIA_BASE = os.getenv("MEDIA_BASE_URL", "/media")
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", "frontend"))
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

# filter key -> the source's own fuel_type values
FUEL_GROUPS = {
    "electric": ["BEV", "EV"],
    "hybrid": ["PHEV", "HEV", "REEV"],
    "petrol": ["Gasoline", "Petrol"],
    "diesel": ["Diesel"],
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.open_pool()
    try:
        yield
    finally:
        await db.close_pool()


app = FastAPI(title="Cargo Auto API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["GET"],
    allow_headers=["*"],
)


def _fuel_values(fuel: str | None) -> list[str]:
    if not fuel:
        return []
    return FUEL_GROUPS.get(fuel, [fuel])


@app.get("/api/health")
async def health():
    row = await db.fetch_one("select count(*) as cars from cars")
    return {"status": "ok", "cars": row["cars"] if row else 0,
            "engine": db.engine(),
            "usd_rub_rate": mapping.USD_RUB_RATE or None}


@app.get("/api/cars")
async def list_cars(
    brand: str | None = None,
    model: str | None = None,
    body: str | None = None,
    fuel: str | None = Query(None, description="electric | hybrid | petrol | diesel"),
    min_price: float | None = Query(None, description="USD"),
    max_price: float | None = Query(None, description="USD"),
    max_price_rub: float | None = Query(None, description="converted with USD_RUB_RATE"),
    min_year: int | None = None,
    max_year: int | None = None,
    max_km: float | None = None,
    q: str | None = None,
    sort: str = Query("newest", pattern="^(newest|price_asc|price_desc|year_desc|mileage_asc)$"),
    limit: int = Query(24, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    if max_price_rub and mapping.USD_RUB_RATE > 0:
        converted = max_price_rub / mapping.USD_RUB_RATE
        max_price = min(max_price, converted) if max_price else converted

    where, params = queries.build_filters(
        brand=brand, model=model, body=body.lower() if body else None,
        fuel_values=_fuel_values(fuel), min_price=min_price, max_price=max_price,
        min_year=min_year, max_year=max_year, max_km=max_km, q=q)

    rows = await db.fetch_all(queries.list_cars(where, queries.ORDER_BY[sort]),
                              {**params, "limit": limit, "offset": offset})
    total = (await db.fetch_one(queries.count_cars(where), params))["total"]

    return {
        "items": [mapping.car_summary(r, MEDIA_BASE) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
        "usd_rub_rate": mapping.USD_RUB_RATE or None,
    }


@app.get("/api/cars/{listing_id}")
async def get_car(listing_id: str):
    row = await db.fetch_one(queries.GET_CAR, {"id": listing_id})
    if not row:
        raise HTTPException(status_code=404, detail="car not found")

    car = mapping.car_summary(row, MEDIA_BASE)
    photos = await db.fetch_all(queries.GET_PHOTOS, {"id": listing_id})
    specs = await db.fetch_all(queries.GET_SPECS, {"id": listing_id})

    car["photos"] = [{
        "position": p["position"],
        "url": mapping.photo_url(p["file_path"], p["s3_url"], MEDIA_BASE),
        "source_url": p["url"],
        # the page's own smaller rendition, for thumbnail strips: a fifth of
        # the bytes of the full-resolution copy
        "thumb": p["source_url"] or mapping.photo_url(p["file_path"], p["s3_url"], MEDIA_BASE),
        "alt": p["alt"],
        "kind": p["kind"],
    } for p in photos]
    # every characteristic the source page carried, grouped as label/value
    car["specs"] = [{"label": s["label"], "value": s["value"],
                     "field": s["canonical_field"]} for s in specs]
    car["spec_count"] = len(specs)
    return car


@app.get("/api/brands")
async def brands():
    rows = await db.fetch_all(queries.BRANDS)
    return [{"slug": r["slug"], "name": r["name"], "count": r["count"],
             "price_from_usd": mapping._int(r["price_from"]),
             "price_from": mapping.money_rub(r["price_from"])} for r in rows]


@app.get("/api/models")
async def models(brand: str | None = None):
    rows = await (db.fetch_all(queries.MODELS_FOR_BRAND, {"brand": brand})
                  if brand else db.fetch_all(queries.MODELS_ALL))
    return [{"slug": r["slug"], "name": r["name"], "brand": r["brand"],
             "brand_name": r["brand_name"], "count": r["count"],
             "price_from_usd": mapping._int(r["price_from"]),
             "price_from": mapping.money_rub(r["price_from"])} for r in rows]


@app.get("/api/filters")
async def filters():
    facets = await db.fetch_one(queries.FACETS)
    bodies = await db.fetch_all(queries.BODIES)
    fuels = await db.fetch_all(queries.FUELS)

    grouped: dict[str, int] = {}
    for f in fuels:
        key, _ = mapping.fuel(f["name"])
        grouped[key] = grouped.get(key, 0) + f["count"]

    return {
        "totals": {k: facets[k] for k in ("cars", "photos", "specs")},
        "price_usd": {"min": mapping._int(facets["price_min"]),
                      "max": mapping._int(facets["price_max"])},
        "year": {"min": facets["year_min"], "max": facets["year_max"]},
        "mileage_km_max": mapping._int(facets["km_max"]),
        "bodies": [{"slug": b["slug"], "name": mapping.body(b["name"])[1],
                    "count": b["count"]} for b in bodies],
        "fuels": [{"slug": k, "name": mapping.FUEL_TYPE.get(
            next((s for s, v in mapping.FUEL_TYPE.items() if v[0] == k), ""),
            (k, k))[1], "count": n} for k, n in grouped.items()],
        "usd_rub_rate": mapping.USD_RUB_RATE or None,
    }


# photos on local disk; uploaded copies are served straight from object storage
if MEDIA_DIR.is_dir():
    app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

# the storefront itself, mounted last so /api and /media win
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
