-- Schema for the Guazi car research dataset.
-- Loaded by Postgres on first boot (docker-entrypoint-initdb.d) and applied
-- idempotently by the parser at startup, so both paths stay in sync.

CREATE TABLE IF NOT EXISTS cars (
    id                  bigserial PRIMARY KEY,
    listing_id          text        NOT NULL UNIQUE,
    url                 text        NOT NULL,
    title               text,
    heading             text,

    -- prices and figures are kept both raw (as shown) and parsed (for analysis)
    price_raw           text,
    price_value         numeric(14, 2),
    price_currency      text,
    original_price_raw  text,
    original_price_value numeric(14, 2),
    year_raw            text,
    year_value          smallint,
    mileage_raw         text,
    mileage_km          numeric(12, 1),

    make                text,
    model               text,
    -- stored rather than derived, so SQLite and Postgres answer identical SQL
    brand_slug          text,
    model_slug          text,
    body_slug           text,
    trim                text,
    body_type           text,
    transmission        text,
    engine              text,
    power               text,
    fuel_type           text,
    fuel_consumption    text,
    drive_type          text,
    emission_standard   text,
    colour              text,
    interior            text,
    seats               text,
    doors               text,
    owners              text,
    condition           text,
    vin                 text,
    plate_location      text,
    insurance           text,
    inspection_due      text,
    transfer_count      text,
    stock_id            text,

    image_count         integer     NOT NULL DEFAULT 0,
    images_downloaded   integer     NOT NULL DEFAULT 0,
    images_dir          text,

    page_text           text,              -- full visible text, nothing lost
    specs               jsonb       NOT NULL DEFAULT '{}'::jsonb,
    json_ld             jsonb,
    state_blobs         jsonb,
    raw_html_path       text,

    first_seen          timestamptz NOT NULL DEFAULT now(),
    scraped_at          timestamptz NOT NULL DEFAULT now()
);

-- Every characteristic as its own row, so arbitrary labels stay queryable
-- even when they have no dedicated column.
CREATE TABLE IF NOT EXISTS car_specs (
    car_id          bigint NOT NULL REFERENCES cars(id) ON DELETE CASCADE,
    label           text   NOT NULL,
    value           text   NOT NULL,
    canonical_field text,
    PRIMARY KEY (car_id, label)
);

CREATE TABLE IF NOT EXISTS car_images (
    id          bigserial PRIMARY KEY,
    car_id      bigint  NOT NULL REFERENCES cars(id) ON DELETE CASCADE,
    position    integer NOT NULL,
    url         text    NOT NULL,     -- full-resolution URL that was requested
    source_url  text,                 -- thumbnail URL as found in the markup
    final_url   text,                 -- after redirects
    alt         text,                 -- caption, e.g. "Front Left 45 Deg"
    kind        text,                 -- exterior / interior / detail / gallery
    file_path   text,
    bytes       bigint,
    downloaded  boolean NOT NULL DEFAULT false,
    s3_key      text,                 -- object key once uploaded
    s3_url      text,
    s3_uploaded_at timestamptz,
    UNIQUE (car_id, position)
);

CREATE INDEX IF NOT EXISTS cars_make_model_idx   ON cars (make, model);
CREATE INDEX IF NOT EXISTS cars_brand_slug_idx   ON cars (brand_slug);
CREATE INDEX IF NOT EXISTS cars_model_slug_idx   ON cars (model_slug);
CREATE INDEX IF NOT EXISTS cars_body_slug_idx    ON cars (body_slug);
CREATE INDEX IF NOT EXISTS cars_price_idx        ON cars (price_value);
CREATE INDEX IF NOT EXISTS cars_year_idx         ON cars (year_value);
CREATE INDEX IF NOT EXISTS cars_specs_gin        ON cars USING gin (specs);
CREATE INDEX IF NOT EXISTS car_specs_label_idx   ON car_specs (label);
CREATE INDEX IF NOT EXISTS car_images_car_idx    ON car_images (car_id);

-- Convenience view for the research team: one row per car, photos folded in.
CREATE OR REPLACE VIEW cars_overview AS
SELECT c.listing_id,
       c.title,
       c.make, c.model, c.trim, c.year_value AS year,
       c.price_value, c.price_currency, c.price_raw,
       c.mileage_km, c.mileage_raw,
       c.body_type, c.transmission, c.engine, c.power,
       c.fuel_type, c.drive_type, c.colour, c.condition,
       c.image_count, c.images_downloaded,
       (SELECT count(*) FROM car_specs s WHERE s.car_id = c.id) AS spec_count,
       c.url, c.scraped_at
FROM cars c
ORDER BY c.scraped_at DESC;
