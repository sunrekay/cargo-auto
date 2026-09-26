"""Collect car detail-page URLs from the listing pages.

Guazi's English site puts every car at /products/<slug>.html and shows 20 per
listing page, with no path-based pagination — filters and paging live in query
strings, which robots.txt forbids. The crawler therefore fans out across the
site's own category paths (/used-cars/<make>/, /used-cars/<body-type>/,
/used-cars/<make>/<model>/), all of which are clean paths and robots-clean.
"""
import re
import urllib.parse

from . import browser, config, robots, slug as slugmod

DETAIL_RE = re.compile(r"^/products/[\w.-]+\.html?$", re.I)
CATEGORY_RE = re.compile(r"^/used-?cars(?:/[\w-]+){0,3}/?$", re.I)

# category pages that are not car listings
CATEGORY_SKIP = re.compile(r"/(blog|news|faq|about|contact|guide|policy|dealership)", re.I)

# /used-cars/<x>/ where x is a shape, not a make
BODY_TYPES = {"sedan", "suv", "mini-van", "hatchback", "wagon", "pick-up", "van",
              "truck", "mpv", "coupe", "convertible", "port-stock"}


def _path(url: str) -> str:
    return urllib.parse.urlsplit(url).path


def is_detail(url: str) -> bool:
    return bool(DETAIL_RE.match(_path(url)))


def is_category(url: str) -> bool:
    p = _path(url)
    return bool(CATEGORY_RE.match(p)) and not CATEGORY_SKIP.search(p)


async def _hrefs(page) -> list[str]:
    """Same-host links, query stripped, filtered through robots.txt."""
    raw = await page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    out = []
    for h in raw:
        if not h.startswith(config.BASE_URL):
            continue
        clean = robots.strip_query(h)
        if robots.allowed(clean):
            out.append(clean)
    return list(dict.fromkeys(out))


async def _load_fully(page) -> None:
    """Scroll until the card count stops growing (cards load lazily)."""
    seen = -1
    for _ in range(8):
        n = await page.evaluate(
            "document.querySelectorAll('a[href*=\"/products/\"]').length")
        if n == seen:
            break
        seen = n
        await page.mouse.wheel(0, 6000)
        await page.wait_for_timeout(1000)


def seed_urls() -> list[str]:
    """Entry points, all query-free so they stay robots-clean."""
    cands = [config.START_URL] if config.START_URL else []
    cands += [f"{config.BASE_URL}/used-cars/", f"{config.BASE_URL}/",
              f"{config.BASE_URL}/usedcars/port-stock/"]
    return [u for u in dict.fromkeys(cands) if u and robots.allowed(u)]


async def collect(page, want: int) -> list[str]:
    """Gather up to `want` distinct car URLs, fanning out over category pages."""
    found: list[str] = []
    visited: set[str] = set()
    queue = seed_urls()

    while queue and len(found) < want:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        if not await browser.goto(page, url, label=f"listing {url}"):
            continue
        await page.wait_for_timeout(int(config.REQUEST_DELAY * 1000))
        await _load_fully(page)

        hrefs = await _hrefs(page)
        new = [h for h in hrefs if is_detail(h) and h not in found]
        found.extend(new)

        # queue the site's own category pages, nearest first
        cats = [h for h in hrefs if is_category(h) and h not in visited and h not in queue]
        queue.extend(cats)

        # a /used-cars/<x>/ page is either a make or a body shape; the makes
        # teach the slug parser how to split "geely-auto-emgrand" correctly
        makes = {seg for h in cats
                 if len(parts := [q for q in _path(h).strip("/").split("/") if q]) == 2
                 for seg in [parts[1]] if seg not in BODY_TYPES}
        if makes:
            slugmod.remember_brands(makes)

        print(f"[listing] {url}\n"
              f"[listing]   +{len(new)} cars (total {len(found)}/{want}), "
              f"{len(cats)} new categories queued, {len(queue)} pending")

    if len(found) < want:
        print(f"[listing] exhausted category pages with {len(found)} cars — "
              f"the site pages through query strings, which robots.txt blocks")
    return found[:want]
