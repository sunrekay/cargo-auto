"""Dump the catalogue into a single SQLite file.

The file is self-contained and small enough to travel with the repository, so
the site can be served anywhere without provisioning a database. Photo bytes are
not in it — those live in object storage and the rows carry their URLs.

    python -m tools.export_sqlite            # -> data/cargo-auto.db
"""
import os
import sqlite3
import sys
from pathlib import Path

from parser import db as pdb

OUT = Path(os.getenv("SQLITE_OUT", "data/cargo-auto.db"))

# page_text and the raw payload blobs are what make the dump large; they are
# research material, not something the storefront reads.
# SQLite has no declared-type enforcement, but the declared type drives its
# affinity: leaving numbers as TEXT makes "10033" sort before "3658".
NUMERIC_COLUMNS = {
    "price_value": "REAL", "original_price_value": "REAL", "mileage_km": "REAL",
    "year_value": "INTEGER", "image_count": "INTEGER", "images_downloaded": "INTEGER",
}

CAR_COLUMNS = [
    "listing_id", "url", "title", "heading", "price_raw", "price_value",
    "price_currency", "original_price_raw", "original_price_value", "year_raw",
    "year_value", "mileage_raw", "mileage_km", "make", "model", "brand_slug",
    "model_slug", "body_slug", "trim", "body_type", "transmission", "engine",
    "power", "fuel_type", "fuel_consumption", "drive_type", "emission_standard",
    "colour", "interior", "seats", "doors", "owners", "condition", "vin",
    "plate_location", "insurance", "inspection_due", "transfer_count",
    "stock_id", "image_count", "images_downloaded", "scraped_at",
]

SCHEMA = f"""
PRAGMA journal_mode = DELETE;   -- one file, no -wal companion to commit

CREATE TABLE cars (
    id INTEGER PRIMARY KEY,
    {', '.join(f'{c} {NUMERIC_COLUMNS.get(c, "TEXT")}' for c in CAR_COLUMNS)}
);
CREATE UNIQUE INDEX cars_listing_id ON cars (listing_id);
CREATE INDEX cars_brand_slug ON cars (brand_slug);
CREATE INDEX cars_model_slug ON cars (model_slug);
CREATE INDEX cars_body_slug  ON cars (body_slug);
CREATE INDEX cars_price      ON cars (price_value);

CREATE TABLE car_specs (
    car_id INTEGER NOT NULL REFERENCES cars(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    value TEXT NOT NULL,
    canonical_field TEXT,
    PRIMARY KEY (car_id, label)
);
CREATE INDEX car_specs_label ON car_specs (label);

CREATE TABLE car_images (
    id INTEGER PRIMARY KEY,
    car_id INTEGER NOT NULL REFERENCES cars(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    url TEXT, source_url TEXT, final_url TEXT,
    alt TEXT, kind TEXT, file_path TEXT, bytes INTEGER,
    downloaded INTEGER NOT NULL DEFAULT 0,
    s3_key TEXT, s3_url TEXT
);
CREATE INDEX car_images_car ON car_images (car_id);
"""


def main() -> int:
    if not pdb.enabled():
        print("[sqlite] DATABASE_URL is not set")
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    out = sqlite3.connect(OUT)
    out.executescript(SCHEMA)

    with pdb.connect() as pg:
        cars = pg.execute(
            f"select id, {', '.join(CAR_COLUMNS)} from cars order by id").fetchall()
        def cast(col: str, value):
            if value is None:
                return None
            if col in NUMERIC_COLUMNS:
                try:
                    return (int(value) if NUMERIC_COLUMNS[col] == "INTEGER"
                            else float(value))
                except (TypeError, ValueError):
                    return None
            return value if isinstance(value, (int, float)) else str(value)

        out.executemany(
            f"insert into cars (id, {', '.join(CAR_COLUMNS)}) "
            f"values ({', '.join('?' * (len(CAR_COLUMNS) + 1))})",
            [(row[0], *(cast(c, v) for c, v in zip(CAR_COLUMNS, row[1:])))
             for row in cars])

        specs = pg.execute(
            "select car_id, label, value, canonical_field from car_specs").fetchall()
        out.executemany("insert or ignore into car_specs values (?,?,?,?)", specs)

        imgs = pg.execute(
            "select id, car_id, position, url, source_url, final_url, alt, kind,"
            " file_path, bytes, downloaded, s3_key, s3_url from car_images"
            " order by car_id, position").fetchall()
        out.executemany(
            "insert into car_images values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [tuple(int(v) if isinstance(v, bool) else v for v in row) for row in imgs])

    out.commit()
    out.execute("VACUUM")
    out.close()

    size = OUT.stat().st_size
    print(f"[sqlite] {len(cars)} cars, {len(specs)} specs, {len(imgs)} photos "
          f"-> {OUT} ({size / 1024 / 1024:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
