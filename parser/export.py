"""Write cars.json and a flat cars.csv.

The CSV carries the normalised fields first, then every extra spec label seen
across the whole dataset, so no harvested characteristic is lost in the flat view.
"""
import csv
import json
import sys

from . import config

CORE = ["listing_id", "url", "title", "heading", "price", "original_price", "year",
        "mileage", "make", "model", "trim", "body_type", "transmission", "engine",
        "power", "fuel_type", "fuel_consumption", "drive_type", "emission_standard",
        "colour", "interior", "seats", "doors", "owners", "condition", "vin",
        "plate_location", "insurance", "inspection_due", "transfer_count", "stock_id",
        "image_count", "images_downloaded", "images_dir"]


def write(cars: list[dict]) -> None:
    config.CARS_JSON.write_text(
        json.dumps(cars, ensure_ascii=False, indent=2), encoding="utf-8")

    spec_keys = sorted({k for c in cars for k in (c.get("specs") or {})})
    header = CORE + [f"spec: {k}" for k in spec_keys] + ["image_urls"]

    with config.CARS_CSV.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for c in cars:
            specs = c.get("specs") or {}
            urls = " | ".join(i.get("final_url") or i["url"] for i in (c.get("images") or []))
            w.writerow([c.get(k, "") for k in CORE] +
                       [specs.get(k, "") for k in spec_keys] + [urls])

    print(f"[export] {len(cars)} cars -> {config.CARS_JSON} and {config.CARS_CSV} "
          f"({len(header)} columns)")


def main() -> None:
    if not config.CARS_JSON.exists():
        print("[export] nothing to export — run the parser first")
        sys.exit(1)
    write(json.loads(config.CARS_JSON.read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
