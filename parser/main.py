"""Crawl en.guazi.com listings into data/cars.json + data/cars.csv + photos.

Resumable: already-parsed cars are kept in data/cars.json and skipped, so an
interrupted run continues where it stopped. The site's human check is never
solved here — when it appears the run pauses for the person at noVNC.
"""
import asyncio
import json
import sys
import traceback

from . import browser, config, db, detail, export, images, listing, robots
from . import photos as photosmod
from . import slug as slugmod
from . import specs as specsmod


def _load_existing() -> tuple[list[dict], set[str]]:
    if not config.CARS_JSON.exists():
        return [], set()
    try:
        cars = json.loads(config.CARS_JSON.read_text(encoding="utf-8"))
        return cars, {c.get("url", "") for c in cars}
    except Exception:
        return [], set()


def _log(msg: str) -> None:
    print(msg, flush=True)
    with config.LOG.open("a", encoding="utf-8") as fh:
        fh.write(msg + "\n")


async def run() -> int:
    raw = robots.load()
    _log(f"[robots] loaded {len(raw)} bytes — query URLs, /api/ and /os/ are off limits")
    db.init()

    cars, done = _load_existing()
    if cars:
        _log(f"[resume] {len(cars)} cars already in {config.CARS_JSON}")
    need = config.TARGET_CARS - len(cars)
    if need <= 0:
        _log(f"[done] target {config.TARGET_CARS} already met")
        export.write(cars)
        return 0

    async with browser.Browser() as b:
        page = await b.page()

        # Collect a surplus of links: some pages fail or repeat.
        urls = await listing.collect(page, want=int(need * 1.4) + 10)
        urls = [u for u in urls if u not in done]
        _log(f"[listing] {len(urls)} candidate detail pages")
        if not urls:
            _log("[listing] no car links found — see data/recon/ and the noVNC window")
            return 2

        for i, url in enumerate(urls, 1):
            if len(cars) >= config.TARGET_CARS:
                break
            _log(f"[car {len(cars)+1}/{config.TARGET_CARS}] {url}")
            try:
                car = await detail.fetch(page, url)
            except Exception as e:
                _log(f"          failed: {type(e).__name__}: {e}")
                continue
            if not car:
                continue

            if config.DOWNLOAD_IMAGES:
                car = await images.download_car(car, await b.ctx.cookies())
            cars.append(car)
            done.add(url)

            _log(f"          {car.get('title','?')[:70]!r} | price={car.get('price','?')} "
                 f"| specs={len(car.get('specs') or {})} "
                 f"| photos={car.get('images_downloaded', car.get('image_count', 0))}")

            if len(cars) % 5 == 0:      # checkpoint, so a crash never loses work
                export.write(cars)
                db.save_all(cars[-5:])

    export.write(cars)
    db.save_all(cars)
    _log(f"[done] {len(cars)} cars collected")
    return 0 if len(cars) >= config.TARGET_CARS else 1


async def login() -> int:
    """Open the site and hand the browser to the person at noVNC.

    Use this once before parsing: clear the site's human check and, if you want,
    sign in — in the noVNC window, with your own credentials. Everything lands in
    the persistent profile under data/profile and the parser reuses it.
    """
    robots.load()
    start = listing.seed_urls()[0]
    async with browser.Browser() as b:
        page = await b.page()
        print(f"[login] opening {start}")
        try:
            await page.goto(start, wait_until="domcontentloaded")
        except Exception as e:
            print(f"[login] navigation issue (harmless if the page is up): {e}")
        print("\n" + "=" * 72)
        print("  Open  ->  http://localhost:6080/")
        print("  In that window: clear the check, and sign in if you want to.")
        print("  Nothing you type there is visible to the parser — only cookies persist.")
        print(f"  This session stays open for {config.HUMAN_WAIT}s, or Ctrl-C when done.")
        print("=" * 72 + "\n", flush=True)

        for left in range(config.HUMAN_WAIT, 0, -15):
            await asyncio.sleep(15)
            ok = not await browser.is_challenged(page)
            names = {c["name"] for c in await b.ctx.cookies()}
            print(f"[login] check_cleared={ok} cookies={len(names)} ({left}s left)", flush=True)
        print("[login] window elapsed — profile saved to", config.PROFILE)
    return 0


def backfill() -> int:
    """Fill make/model/colour/drive/seats from each car's URL, in place.

    The site states these only in the URL it generates, so cars collected before
    the slug parser existed can be completed without crawling anything again.
    """
    if not config.CARS_JSON.exists():
        _log("[backfill] no cars.json")
        return 1
    cars = json.loads(config.CARS_JSON.read_text(encoding="utf-8"))
    aliases = {"engine_from_slug": "engine", "mileage_from_slug": "mileage",
               "transmission_from_slug": "transmission"}
    filled = respecced = 0
    for car in cars:
        # re-read the saved page: no crawling, and it carries far more specs
        raw = config.RAW / f"{car.get('listing_id')}.html"
        if raw.exists():
            try:
                html = raw.read_text(encoding="utf-8")
            except Exception:
                html = ""
            if html:
                payload_specs = specsmod.extract(html)
                if len(payload_specs) > len(car.get("specs") or {}):
                    merged = dict(payload_specs)
                    merged.update({k: v for k, v in (car.get("specs") or {}).items()
                                   if k not in payload_specs})
                    car["specs"] = merged
                    respecced += 1
                    for label, value in merged.items():
                        field = detail._canonical(label)
                        if field and not car.get(field):
                            car[field] = value
        parsed = slugmod.parse(car.get("slug") or car.get("url", "").split("/")[-1]
                               .removesuffix(".html"))
        if not parsed:
            continue
        car["slug_fields"] = parsed
        before = sum(1 for f in ("make", "model", "colour", "drive_type", "seats")
                     if car.get(f))
        for key, value in parsed.items():
            field = aliases.get(key, key)
            if field != "listing_id" and not car.get(field):
                car[field] = value
        after = sum(1 for f in ("make", "model", "colour", "drive_type", "seats")
                    if car.get(f))
        filled += after > before

    export.write(cars)
    db.init()
    db.save_all(cars)
    _log(f"[backfill] {filled} cars completed from their URLs, "
         f"{respecced} re-read from saved HTML for the full spec set")
    return 0


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    if mode == "backfill":
        sys.exit(backfill())
    if mode == "load-db":            # push an existing cars.json into Postgres
        db.load_json_into_db()
        sys.exit(0)
    try:
        code = asyncio.run(login() if mode == "login" else run())
    except KeyboardInterrupt:
        print("\n[main] interrupted — progress is in data/cars.json")
        code = 130
    except Exception:
        traceback.print_exc()
        code = 1
    sys.exit(code)


if __name__ == "__main__":
    main()
