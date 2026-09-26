# Guazi car parser

Collects used-car listings from [en.guazi.com](https://en.guazi.com) for research:
every characteristic shown on a car's page, its photos at the highest resolution
the CDN serves, and the raw HTML so the data can be re-extracted later without
crawling again. Output goes to Postgres, JSON and CSV at the same time.

Everything runs in Docker — nothing is installed on the host.

## Quick start

```bash
make check     # docker, compose and the daemon are reachable
make run       # parse 150 cars into ./data and Postgres
```

`make run` starts Postgres, builds the image and crawls. Watch progress with
`make logs`, and query the result with `make psql`.

### The site asks for a human check

en.guazi.com sits behind Tencent EdgeOne, which answers automated traffic with an
interactive "check the box" CAPTCHA. **The parser never solves or evades it.**
When the check appears the run pauses and prints:

```
The site is asking for a human check (Tencent EdgeOne CAPTCHA).
Open  ->  http://localhost:6080/   and clear it in that browser.
```

Open that address: it is a live view (noVNC) of the Chromium running inside the
container. Click **Connect**, clear the check, and the run continues on its own.
The browser profile is persistent (`data/profile`), so one pass usually covers the
whole session. `make login` opens the same window deliberately — use it to clear
the check, or to sign in to the site, before a long run.

## What gets collected

Per car:

* **Identity** — the site's own id, URL, title, and the slug (which encodes
  make, model, year, engine, colour, mileage, gearbox, drive and seats).
* **Normalised fields** — price, mileage, year, make, model, trim, body type,
  transmission, engine, power, fuel type and consumption, drive type, emission
  standard, colour, interior, seats, doors, owners, condition, VIN, plate
  location, insurance, inspection, transfers, stock id.
* **Every other characteristic** — all label/value pairs found anywhere on the
  page (definition lists, tables, spec rows), kept verbatim in `specs`.
* **Structured data** — JSON-LD and any embedded page-state blobs.
* **Full page text** — so nothing visible on the page is lost.
* **Photos** — 17–27 per car at 1280x960, each with the caption the site gives
  it ("Front Left 45 Deg", "Engine Bay", "Center Console") and its section
  (exterior / interior / detail). Condition videos are recorded when present.

Photos are not scraped from `<img>` tags: this is a Next.js site whose DOM holds
mostly interface chrome (brand logos, 48x48 icons), so `parser/photos.py`
reassembles the page's streamed data payload and reads the gallery lists from
it, then strips the CDN's `?x-bce-process=` parameters to get the original
upload. If that payload ever changes shape the parser says so in the log
(`gallery data missing`) and falls back to the DOM rather than silently
collecting the wrong files.

Prices and distances are stored both as shown (`price_raw`) and parsed
(`price_value`, `price_currency`, `mileage_km`), including Chinese conventions
such as `5.98万` → 59 800 and `4.2万公里` → 42 000 km.

## Output

```
data/
├── cars.json          every car, complete
├── cars.csv           flat view: normalised columns + every spec label seen
├── images/<car-id>/   photos, largest available variant
├── raw/<car-id>.html  page source, for re-extraction without re-crawling
├── profile/           browser profile (keeps the cleared check)
└── parser.log
```

In Postgres: `cars` (one row per car, with `specs` as `jsonb`), `car_specs`
(one row per characteristic, queryable by label), `car_images`, and the
`cars_overview` view.

```bash
make sql Q="select make, count(*), round(avg(price_value)) from cars group by 1 order by 2 desc"
make sql Q="select label, count(*) from car_specs group by 1 order by 2 desc limit 20"
```

## Crawling rules

The site's `robots.txt` allows public pages but forbids every query-string URL
plus `/api/` and `/os/`. The crawler enforces this: it strips queries, checks
each URL against the live `robots.txt`, and never touches the internal API.

Because paging and filtering on Guazi happen through query strings, the crawler
reaches breadth through the site's own category paths instead —
`/used-cars/<make>/`, `/used-cars/<body-type>/`, `/used-cars/<make>/<model>/` —
each listing 20 cars. It also pauses `REQUEST_DELAY` seconds between pages.

## Configuration

Settings live in `.env` (created from `.env.example`; it holds the local
Postgres password). Common knobs:

| Variable | Default | Meaning |
|---|---|---|
| `TARGET_CARS` | 150 | how many cars to collect |
| `MAX_IMAGES_PER_CAR` | 40 | photo cap per car |
| `DOWNLOAD_IMAGES` | 1 | set to 0 to record URLs without downloading |
| `REQUEST_DELAY` | 2.5 | seconds between page loads |
| `HUMAN_WAIT` | 900 | seconds to wait for a person to clear a check |
| `CONCURRENCY` | 4 | parallel image downloads |
| `START_URL` | `https://en.guazi.com/bin/` | entry page |

Runs are resumable: cars already in `data/cars.json` are skipped, and progress is
checkpointed every five cars.

## Make targets

```
make check     docker/compose/daemon are healthy
make up        start Postgres
make login     open the live browser to clear the check or sign in
make run       parse TARGET_CARS cars
make stats     how much has been collected
make psql      psql shell on the data
make sql Q=".."run a single query
make csv       rebuild cars.csv from cars.json
make load-db   load an existing cars.json into Postgres
make recon     dump the site's current structure to data/recon
make shell     shell inside the container
make clean-data / clean-db / clean-profile / clean
```

## Layout

```
parser/     config, robots enforcement, browser, listing crawl,
            detail extraction, image download, normalisation, db, export
tools/      recon and self-check scripts
db/         schema.sql (applied by Postgres on boot and by the parser)
docker/     entrypoint that starts Xvfb + noVNC
```
