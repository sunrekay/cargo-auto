"""Portable SQL for the storefront.

The same statements run on Postgres and on SQLite. Two things make that work:
brand/model/body slugs are stored columns rather than expressions, and filters
are assembled only for the values actually supplied — so there are no
"parameter is null" comparisons for Postgres to complain about and no
dialect-specific casts.

Placeholders are written in the named `:name` form, which SQLite takes directly
and the Postgres adapter rewrites.
"""

# one representative photo, as a correlated subquery rather than LATERAL
FIRST_PHOTO = """
    (select ci.file_path from car_images ci
      where ci.car_id = c.id and ci.downloaded = 1 order by ci.position limit 1) as file_path,
    (select ci.s3_url from car_images ci
      where ci.car_id = c.id and ci.downloaded = 1 order by ci.position limit 1) as s3_url
"""

CAR_COLUMNS = """
    c.listing_id, c.title, c.make, c.model, c.trim, c.year_value, c.price_value,
    c.price_currency, c.mileage_km, c.power, c.fuel_type, c.body_type, c.engine,
    c.transmission, c.drive_type, c.colour, c.seats, c.image_count, c.url,
    c.condition, c.vin, c.emission_standard, c.owners, c.scraped_at,
    c.brand_slug, c.model_slug, c.body_slug
"""

ORDER_BY = {
    "newest": "c.scraped_at desc, c.id desc",
    "price_asc": "c.price_value asc",
    "price_desc": "c.price_value desc",
    "year_desc": "c.year_value desc",
    "mileage_asc": "c.mileage_km asc",
}


def build_filters(*, brand=None, model=None, body=None, fuel_values=None,
                  min_price=None, max_price=None, min_year=None, max_year=None,
                  max_km=None, q=None) -> tuple[str, dict]:
    """WHERE clause plus parameters, containing only the filters in use."""
    where: list[str] = []
    params: dict = {}

    def add(sql: str, **kw):
        where.append(sql)
        params.update(kw)

    if brand:
        add("c.brand_slug = :brand", brand=brand)
    if model:
        add("c.model_slug = :model", model=model)
    if body:
        add("c.body_slug = :body", body=body)
    if fuel_values:
        names = [f"fuel{i}" for i in range(len(fuel_values))]
        add("c.fuel_type in (" + ", ".join(f":{n}" for n in names) + ")",
            **dict(zip(names, fuel_values)))
    if min_price is not None:
        add("c.price_value >= :min_price", min_price=min_price)
    if max_price is not None:
        add("c.price_value <= :max_price", max_price=max_price)
    if min_year is not None:
        add("c.year_value >= :min_year", min_year=min_year)
    if max_year is not None:
        add("c.year_value <= :max_year", max_year=max_year)
    if max_km is not None:
        add("c.mileage_km <= :max_km", max_km=max_km)
    if q:
        add("(lower(c.title) like :q_like or lower(c.make) like :q_like"
            " or lower(c.model) like :q_like)", q_like=f"%{q.lower()}%")

    clause = (" where " + " and ".join(where)) if where else ""
    return clause, params


def list_cars(where: str, order: str) -> str:
    return (f"select {CAR_COLUMNS}, {FIRST_PHOTO} from cars c{where}"
            f" order by {order} limit :limit offset :offset")


def count_cars(where: str) -> str:
    return f"select count(*) as total from cars c{where}"


GET_CAR = f"select {CAR_COLUMNS}, {FIRST_PHOTO} from cars c where c.listing_id = :id"

GET_PHOTOS = """
select position, url, s3_url, file_path, alt, kind, bytes
from car_images
where car_id = (select id from cars where listing_id = :id) and downloaded = 1
order by position
"""

GET_SPECS = """
select label, value, canonical_field
from car_specs
where car_id = (select id from cars where listing_id = :id)
order by label
"""

BRANDS = """
select make as name, brand_slug as slug, count(*) as count,
       min(price_value) as price_from
from cars where make is not null and brand_slug is not null
group by make, brand_slug
order by count(*) desc, make
"""

MODELS_ALL = """
select model as name, model_slug as slug, make as brand_name, brand_slug as brand,
       count(*) as count, min(price_value) as price_from
from cars where model is not null and model_slug is not null
group by make, brand_slug, model, model_slug
order by count(*) desc, model
"""

MODELS_FOR_BRAND = MODELS_ALL.replace(
    "where model is not null and model_slug is not null",
    "where model is not null and model_slug is not null and brand_slug = :brand")

FACETS = """
select
  (select count(*) from cars) as cars,
  (select count(*) from car_images where downloaded = 1) as photos,
  (select count(*) from car_specs) as specs,
  (select min(price_value) from cars) as price_min,
  (select max(price_value) from cars) as price_max,
  (select min(year_value) from cars) as year_min,
  (select max(year_value) from cars) as year_max,
  (select max(mileage_km) from cars) as km_max
"""

BODIES = """
select body_type as name, body_slug as slug, count(*) as count
from cars where body_type is not null and body_slug is not null
group by body_type, body_slug order by count(*) desc
"""

FUELS = """
select fuel_type as name, count(*) as count
from cars where fuel_type is not null and fuel_type <> ''
group by fuel_type order by count(*) desc
"""
