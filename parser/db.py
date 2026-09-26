"""Postgres persistence.

Optional: with no DATABASE_URL the parser still writes JSON/CSV and simply
skips the database. The schema comes from db/schema.sql — the same file Postgres
runs on first boot — so there is one definition, not two.
"""
import json
import os
import re
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from . import config, normalize

DATABASE_URL = os.getenv("DATABASE_URL", "")
SCHEMA_FILE = Path(os.getenv("SCHEMA_FILE", "db/schema.sql"))

# car dict key -> cars column, for the plain text columns
def slugify(value: str | None) -> str | None:
    """Stable key for a name: 'Geely Auto' -> 'geely-auto'."""
    if not value:
        return None
    out = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return out or None


TEXT_COLUMNS = (
    "url", "title", "heading", "make", "model", "trim", "body_type", "transmission",
    "engine", "power", "fuel_type", "fuel_consumption", "drive_type",
    "emission_standard", "colour", "interior", "seats", "doors", "owners",
    "condition", "vin", "plate_location", "insurance", "inspection_due",
    "transfer_count", "stock_id", "images_dir",
)


def enabled() -> bool:
    return bool(DATABASE_URL)


def connect() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL, autocommit=True)


def init() -> None:
    """Apply the schema. Safe to call on every run (all DDL is IF NOT EXISTS)."""
    if not enabled():
        print("[db] DATABASE_URL not set — skipping database output")
        return
    if not SCHEMA_FILE.exists():
        print(f"[db] schema file {SCHEMA_FILE} missing — skipping")
        return
    with connect() as conn:
        conn.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
    print(f"[db] schema applied from {SCHEMA_FILE}")


def _row(car: dict) -> dict:
    price_val, currency = normalize.price(car.get("price"))
    orig_val, _ = normalize.price(car.get("original_price"))
    row = {
        "listing_id": str(car.get("listing_id") or "")[:200],
        "price_raw": car.get("price"),
        "price_value": price_val,
        "price_currency": currency,
        "original_price_raw": car.get("original_price"),
        "original_price_value": orig_val,
        "year_raw": car.get("year"),
        "year_value": normalize.year(car.get("year") or car.get("title")),
        "mileage_raw": car.get("mileage"),
        "mileage_km": normalize.mileage_km(car.get("mileage")),
        "image_count": int(car.get("image_count") or 0),
        "images_downloaded": int(car.get("images_downloaded") or 0),
        "page_text": car.get("page_text"),
        "specs": Jsonb(car.get("specs") or {}),
        "json_ld": Jsonb(car["json_ld"]) if car.get("json_ld") else None,
        "state_blobs": Jsonb(car["state_blobs"]) if car.get("state_blobs") else None,
        "raw_html_path": str(config.RAW / f"{car.get('listing_id')}.html"),
        "brand_slug": slugify(car.get("make")),
        "model_slug": slugify(car.get("model")),
        "body_slug": slugify(car.get("body_type")),
    }
    for col in TEXT_COLUMNS:
        row[col] = car.get(col)
    return row


def upsert_car(conn: psycopg.Connection, car: dict) -> int:
    """Insert or refresh one car with its specs and photos. Returns cars.id."""
    row = _row(car)
    cols = list(row)
    placeholders = ", ".join(f"%({c})s" for c in cols)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != "listing_id")

    sql = (f"INSERT INTO cars ({', '.join(cols)}) VALUES ({placeholders}) "
           f"ON CONFLICT (listing_id) DO UPDATE SET {updates}, scraped_at = now() "
           f"RETURNING id")
    with conn.cursor() as cur:
        cur.execute(sql, row)
        car_id = cur.fetchone()[0]

        # specs: replace wholesale, the page is the source of truth
        cur.execute("DELETE FROM car_specs WHERE car_id = %s", (car_id,))
        specs = car.get("specs") or {}
        if specs:
            from .detail import _canonical
            cur.executemany(
                "INSERT INTO car_specs (car_id, label, value, canonical_field) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (car_id, label) DO NOTHING",
                [(car_id, k[:300], v[:2000], _canonical(k)) for k, v in specs.items()])

        # Photo rows are rebuilt wholesale, but where each photo already lives
        # in object storage is not something the page can tell us again — carry
        # it across by URL so a re-import does not orphan the uploads.
        cur.execute("select url, s3_key, s3_url, s3_uploaded_at from car_images"
                    " where car_id = %s and s3_key is not null", (car_id,))
        kept = {r[0]: r[1:] for r in cur.fetchall()}
        cur.execute("DELETE FROM car_images WHERE car_id = %s", (car_id,))
        imgs = car.get("images") or []
        if imgs:
            cur.executemany(
                "INSERT INTO car_images (car_id, position, url, source_url, final_url,"
                " alt, kind, file_path, bytes, downloaded, s3_key, s3_url,"
                " s3_uploaded_at)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                [(car_id, i, im.get("url"), im.get("source_url"), im.get("final_url"),
                  im.get("alt"), im.get("kind"), im.get("file"), im.get("bytes"),
                  bool(im.get("downloaded")), *kept.get(im.get("url"), (None, None, None)))
                 for i, im in enumerate(imgs, 1)])
    return car_id


def save_all(cars: list[dict]) -> None:
    """Persist every car. Never fatal: JSON/CSV remain the primary output."""
    if not enabled():
        return
    try:
        with connect() as conn:
            for car in cars:
                upsert_car(conn, car)
            n = conn.execute("SELECT count(*) FROM cars").fetchone()[0]
            imgs = conn.execute("SELECT count(*) FROM car_images").fetchone()[0]
            specs = conn.execute("SELECT count(*) FROM car_specs").fetchone()[0]
        print(f"[db] stored {len(cars)} cars (table now: {n} cars, "
              f"{specs} spec rows, {imgs} image rows)")
    except Exception as e:
        print(f"[db] write failed ({type(e).__name__}: {e}) — JSON/CSV still written")


def load_json_into_db() -> None:
    """Load data/cars.json into Postgres without re-crawling."""
    if not config.CARS_JSON.exists():
        print("[db] no cars.json to load")
        return
    init()
    save_all(json.loads(config.CARS_JSON.read_text(encoding="utf-8")))


if __name__ == "__main__":
    load_json_into_db()
