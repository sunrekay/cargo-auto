"""Turn a database row into the shape the storefront renders.

The parser stores what the source says; this module is the only place that
decides how those facts are presented — labels, slugs, formatted strings and
the currency conversion — so the raw data stays untouched and re-interpretable.
"""
import os
import re

# The source prices in USD. The rouble figure is a display conversion, not a
# quote: the rate is configuration and ships with every response.
USD_RUB_RATE = float(os.getenv("USD_RUB_RATE", "0") or 0)

FUEL_TYPE = {            # source value -> (filter key, Russian label)
    "BEV": ("electric", "Электро"),
    "EV": ("electric", "Электро"),
    "PHEV": ("hybrid", "Гибрид"),
    "HEV": ("hybrid", "Гибрид"),
    "REEV": ("hybrid", "Гибрид"),
    "Gasoline": ("petrol", "Бензин"),
    "Petrol": ("petrol", "Бензин"),
    "Diesel": ("diesel", "Дизель"),
}

BODY = {
    "sedan": "sedan", "suv": "suv", "wagon": "wagon", "estate": "wagon",
    "hatchback": "hatchback", "mpv": "mpv", "mini-van": "mpv", "minivan": "mpv",
    "van": "van", "pickup": "pickup", "pick-up": "pickup", "truck": "truck",
    "coupe": "coupe", "convertible": "convertible", "roadster": "convertible",
}
BODY_LABEL = {"sedan": "Седан", "suv": "Внедорожник", "wagon": "Универсал",
              "hatchback": "Хэтчбек", "mpv": "Минивэн", "van": "Фургон",
              "pickup": "Пикап", "truck": "Грузовик", "coupe": "Купе",
              "convertible": "Кабриолет"}


def slugify(value: str | None) -> str | None:
    if not value:
        return None
    s = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[\s_]+", "-", s).strip("-") or None


def fuel(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    return FUEL_TYPE.get(value.strip(), (slugify(value), value.strip()))


def body(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    key = BODY.get(value.strip().lower())
    return key, BODY_LABEL.get(key, value.strip()) if key else value.strip()


def trim_from_title(title: str | None, make: str | None, model: str | None,
                    year) -> str | None:
    """'Used Mazda 3 Axela 2023 2.0L Automatic Zhiqing Edition for Sale - …'
    -> '2.0L Automatic Zhiqing Edition'."""
    if not title:
        return None
    t = re.sub(r"\s+for Sale\b.*$", "", title.strip(), flags=re.I)
    t = re.sub(r"^\s*Used\s+", "", t, flags=re.I)
    for part in (make, model, str(year) if year else None):
        if part:
            t = re.sub(rf"^\s*{re.escape(part)}\s*", "", t, flags=re.I)
    t = t.strip(" -–|")
    return t or None


def _int(value) -> int | None:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def money_rub(price_usd) -> int | None:
    v = _int(price_usd)
    if v is None or USD_RUB_RATE <= 0:
        return None
    return int(round(v * USD_RUB_RATE))


def photo_url(file_path: str | None, s3_url: str | None, media_base: str) -> str | None:
    """Prefer the copy in object storage; fall back to the local file."""
    if s3_url:
        return s3_url
    if not file_path:
        return None
    rel = file_path.replace("data/images/", "").lstrip("/")
    return f"{media_base.rstrip('/')}/{rel}"


def car_summary(row: dict, media_base: str) -> dict:
    make, model = row.get("make"), row.get("model")
    fuel_key, fuel_label = fuel(row.get("fuel_type"))
    body_key, body_label = body(row.get("body_type"))
    km = _int(row.get("mileage_km"))
    power = _int(row.get("power"))
    usd = _int(row.get("price_value"))

    return {
        "id": row["listing_id"],
        "brand": slugify(make),
        "brand_name": make,
        "model": slugify(model),
        "model_name": model,
        "name": " ".join(p for p in (make, model) if p) or row.get("title"),
        "trim": trim_from_title(row.get("title"), make, model, row.get("year_value")),
        "year": row.get("year_value"),
        "type": fuel_key,
        "fuel": fuel_label,
        "body": body_key,
        "body_label": body_label,
        "km": f"{km:,} км".replace(",", " ") if km is not None else None,
        "mileage_km": km,
        "power": f"{power} л.с." if power else None,
        "power_ps": power,
        "engine": row.get("engine"),
        "transmission": row.get("transmission"),
        "drive": row.get("drive_type"),
        "colour": row.get("colour"),
        "seats": row.get("seats"),
        "price_usd": usd,
        "price": money_rub(usd),
        "image": photo_url(row.get("file_path"), row.get("s3_url"), media_base),
        "photo_count": row.get("image_count"),
        "source_url": row.get("url"),
    }
