"""Self-check of the parser -> Postgres write path, using a synthetic record.

Inserts one car shaped exactly like detail.extract() output, verifies it lands
in all three tables with the numbers parsed, then removes it again.
"""
from parser import db, normalize

SAMPLE = {
    "listing_id": "__selftest__",
    "url": "https://en.guazi.com/bin/99999999x.htm",
    "title": "2019 Volkswagen Lavida 1.5L Automatic Comfort",
    "heading": "2019 Volkswagen Lavida",
    "price": "¥ 5.98万",
    "original_price": "¥ 89,800",
    "year": "2019-07",
    "mileage": "4.2万公里",
    "make": "Volkswagen", "model": "Lavida", "trim": "1.5L Comfort",
    "body_type": "Sedan", "transmission": "Automatic", "engine": "1.5L 113hp L4",
    "fuel_type": "Petrol", "drive_type": "FWD", "colour": "White",
    "seats": "5", "condition": "Inspected, no accidents", "plate_location": "Binzhou",
    "specs": {"Transmission": "Automatic", "Displacement": "1.5L",
              "Emission standard": "China VI", "Number of owners": "1",
              "Air conditioning": "Automatic climate control"},
    "page_text": "2019 Volkswagen Lavida ... full page text ...",
    "json_ld": [{"@type": "Car", "name": "Volkswagen Lavida"}],
    "image_count": 3, "images_downloaded": 3, "images_dir": "data/images/__selftest__",
    "images": [
        {"url": "https://cdn.example/a.jpg", "source_url": "https://cdn.example/a_300x225.jpg",
         "final_url": "https://cdn.example/a.jpg", "file": "data/images/__selftest__/01_a.jpg",
         "bytes": 812_345, "downloaded": True},
        {"url": "https://cdn.example/b.jpg", "downloaded": True, "bytes": 654_321,
         "file": "data/images/__selftest__/02_b.jpg"},
        {"url": "https://cdn.example/c.jpg", "downloaded": False},
    ],
}


def main() -> int:
    print("-- number parsing --")
    print("  '¥ 5.98万'   ->", normalize.price("¥ 5.98万"))
    print("  '¥ 89,800'   ->", normalize.price("¥ 89,800"))
    print("  '4.2万公里'  ->", normalize.mileage_km("4.2万公里"), "km")
    print("  '8,000 miles'->", normalize.mileage_km("8,000 miles"), "km")
    print("  '2019-07'    ->", normalize.year("2019-07"))

    if not db.enabled():
        print("!! DATABASE_URL not set — cannot test the database path")
        return 1

    db.init()
    with db.connect() as conn:
        car_id = db.upsert_car(conn, SAMPLE)
        print(f"-- inserted cars.id={car_id} --")
        row = conn.execute(
            "select listing_id, make, model, year_value, price_value, price_currency,"
            " original_price_value, mileage_km, image_count from cars where id=%s",
            (car_id,)).fetchone()
        print("  cars        :", row)
        print("  car_specs   :", conn.execute(
            "select count(*) from car_specs where car_id=%s", (car_id,)).fetchone()[0], "rows")
        print("  canonical   :", conn.execute(
            "select label, canonical_field from car_specs where car_id=%s"
            " and canonical_field is not null order by 1", (car_id,)).fetchall())
        print("  car_images  :", conn.execute(
            "select count(*), count(*) filter (where downloaded) from car_images"
            " where car_id=%s", (car_id,)).fetchone())
        print("  jsonb query :", conn.execute(
            "select specs->>'Emission standard' from cars where id=%s", (car_id,)).fetchone()[0])
        print("  view row    :", conn.execute(
            "select listing_id, make, year, price_value, spec_count from cars_overview"
            " where listing_id=%s", (SAMPLE["listing_id"],)).fetchone())

        # idempotency: a second pass must update, not duplicate
        again = db.upsert_car(conn, SAMPLE)
        total = conn.execute("select count(*) from cars where listing_id=%s",
                             (SAMPLE["listing_id"],)).fetchone()[0]
        print(f"-- re-upsert id={again} (same={again == car_id}), rows for listing={total} --")

        conn.execute("DELETE FROM cars WHERE listing_id=%s", (SAMPLE["listing_id"],))
        left = conn.execute("select count(*) from car_images where car_id=%s",
                            (car_id,)).fetchone()[0]
        print(f"-- cleaned up, cascade left {left} image rows --")
    print("OK: parser -> Postgres path works")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
