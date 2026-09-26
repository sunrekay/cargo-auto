"""Extract everything a car detail page exposes.

Deliberately generic: rather than betting on one set of selectors, it harvests
label/value pairs from every structure the page might use (definition lists,
tables, spec rows, JSON-LD, embedded state blobs) and merges them into one
`specs` dict. Known labels are additionally normalised into stable top-level
fields so the CSV has usable columns; nothing is dropped either way.
"""
import json
import re
import urllib.parse

from . import browser, config, photos, specs as specsmod, slug as slugmod

# canonical field  ->  label fragments seen on the page (lowercased)
FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "price":            ("price", "selling price", "sale price"),
    "original_price":   ("original price", "list price", "msrp", "new car price"),
    "year":             ("year", "registration date", "first registration", "reg date", "model year"),
    "mileage":          ("mileage", "kilometres", "kilometers", "odometer", "km travelled", "distance"),
    "make":             ("make", "brand", "manufacturer"),
    "model":            ("model", "series"),
    "trim":             ("trim", "variant", "configuration", "version", "edition"),
    "body_type":        ("body type", "body style", "vehicle type", "category"),
    "transmission":     ("transmission", "gearbox", "gear"),
    "engine":           ("engine", "displacement", "engine size", "engine model"),
    "power":            ("power", "horsepower", "max power", "kw", "hp"),
    "fuel_type":        ("fuel type", "fuel", "energy type", "power type"),
    "fuel_consumption": ("fuel consumption", "consumption", "mpg", "l/100"),
    "drive_type":       ("drive", "drivetrain", "drive type", "traction"),
    "emission_standard": ("emission", "euro ", "environmental standard"),
    "colour":           ("colour", "color", "exterior colour", "exterior color", "paint"),
    "interior":         ("interior", "upholstery", "seat material"),
    "seats":            ("seats", "seating", "number of seats"),
    "doors":            ("doors", "number of doors"),
    "owners":           ("owner", "previous owners", "number of owners"),
    "condition":        ("condition", "grade", "inspection", "score"),
    "vin":              ("vin", "chassis", "frame number"),
    "plate_location":   ("plate", "licence", "license", "registered in", "location", "city"),
    "insurance":        ("insurance", "compulsory insurance"),
    "inspection_due":   ("inspection valid", "mot", "annual inspection", "roadworthy"),
    "transfer_count":   ("transfer", "transfers"),
    "stock_id":         ("stock", "listing id", "car id", "item no", "sku"),
}

IMG_EXT = re.compile(r"\.(?:jpe?g|png|webp|avif)(?:$|[?#])", re.I)


def _clean(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip(" :\t\n ")


def _matches(fragment: str, text: str) -> bool:
    """Whole-word match, so 'condition' does not claim 'Air conditioning'."""
    frag = fragment.strip()
    if not frag.isalpha() and " " not in frag:      # 'l/100', 'mpg.' etc.
        return frag in text
    return re.search(rf"(?<!\w){re.escape(frag)}(?!\w)", text) is not None


def _canonical(label: str) -> str | None:
    """Map a page label onto a stable field name; longest match wins."""
    low = label.lower()
    best, best_len = None, 0
    for field, frags in FIELD_ALIASES.items():
        for frag in frags:
            if len(frag.strip()) > best_len and _matches(frag, low):
                best, best_len = field, len(frag.strip())
    return best


# ---- browser-side harvesting -------------------------------------------------

JS_PAIRS = r"""
() => {
  const out = [];
  const push = (k, v) => {
    k = (k || '').replace(/\s+/g, ' ').trim().replace(/[:：]\s*$/, '');
    v = (v || '').replace(/\s+/g, ' ').trim();
    if (k && v && k.length < 60 && v.length < 400 && k !== v) out.push([k, v]);
  };

  // definition lists
  document.querySelectorAll('dl').forEach(dl => {
    const dts = [...dl.querySelectorAll('dt')], dds = [...dl.querySelectorAll('dd')];
    dts.forEach((dt, i) => dds[i] && push(dt.innerText, dds[i].innerText));
  });

  // two-cell table rows, and th/td pairs
  document.querySelectorAll('tr').forEach(tr => {
    const cells = [...tr.children].filter(c => /^(TD|TH)$/.test(c.tagName));
    for (let i = 0; i + 1 < cells.length; i += 2) push(cells[i].innerText, cells[i + 1].innerText);
  });

  // generic "label + value" rows: an element whose two children are leaf text
  document.querySelectorAll('li, .item, [class*=param], [class*=spec], [class*=config], [class*=info]')
    .forEach(el => {
      const kids = [...el.children].filter(c => c.innerText && c.innerText.trim());
      if (kids.length === 2 && !kids.some(k => k.children.length > 1))
        push(kids[0].innerText, kids[1].innerText);
      else if (kids.length === 0) {
        const m = el.innerText.match(/^([^:：]{2,40})[:：]\s*(.+)$/);
        if (m) push(m[1], m[2]);
      }
    });

  return out;
}
"""

JS_IMAGES = r"""
() => {
  const urls = new Set();
  const add = u => { if (u && /^https?:/.test(u)) urls.add(u.split(' ')[0]); };

  document.querySelectorAll('img').forEach(img => {
    add(img.currentSrc); add(img.src);
    for (const a of ['data-src','data-original','data-lazy','data-echo','data-url','data-big'])
      add(img.getAttribute(a));
    const ss = img.getAttribute('srcset');
    if (ss) ss.split(',').forEach(p => add(p.trim().split(/\s+/)[0]));
  });
  document.querySelectorAll('source[srcset]').forEach(s =>
    s.getAttribute('srcset').split(',').forEach(p => add(p.trim().split(/\s+/)[0])));
  document.querySelectorAll('[style*="url("]').forEach(el => {
    const m = /url\(["']?(https?:[^"')]+)/.exec(el.getAttribute('style') || '');
    if (m) add(m[1]);
  });
  // photo urls embedded in inline JSON/state
  const re = /https?:\/\/[^"'\\\s)]+\.(?:jpe?g|png|webp|avif)/gi;
  document.querySelectorAll('script:not([src])').forEach(s => {
    const t = s.textContent || '';
    if (t.length < 400000) (t.match(re) || []).forEach(add);
  });
  return [...urls];
}
"""

JS_JSONLD = r"""
() => [...document.querySelectorAll('script[type="application/ld+json"]')]
        .map(s => s.textContent).filter(Boolean)
"""

JS_BLOBS = r"""
() => {
  const out = {};
  for (const k of Object.keys(window)) {
    if (!/^(__|_)?(NUXT|NEXT|INITIAL|PRELOAD|APP_?DATA|PAGE_?DATA|G_|GZ|CAR)/i.test(k)) continue;
    try { const s = JSON.stringify(window[k]); if (s && s.length < 400000) out[k] = s; } catch (e) {}
  }
  return out;
}
"""


def upgrade_image_url(url: str) -> str:
    """Point a thumbnail URL at the full-resolution original.

    CDNs here encode the rendition in the filename or query, e.g.
    `foo_300x225.jpg`, `foo.jpg@base@tag=imgScale&w=400`, `foo.jpg?x-oss-process=…`.
    Stripping those yields the untouched upload.
    """
    u = url.split("@")[0]                                  # alibaba-style processors
    u = re.sub(r"[?&](?:x-oss-process|imageView2|imageMogr2|w|h|width|height|size)=[^&]*", "", u)
    u = u.rstrip("?&")
    u = re.sub(r"[_-](?:\d{2,4}x\d{2,4}|small|thumb|middle|big|s|m)(\.(?:jpe?g|png|webp|avif))$",
               r"\1", u, flags=re.I)
    u = re.sub(r"/(?:thumb|small|middle|preview)/", "/", u, flags=re.I)
    return u


def _plausible_photo(url: str) -> bool:
    if not IMG_EXT.search(url):
        return False
    low = url.lower()
    junk = ("logo", "icon", "sprite", "avatar", "qrcode", "qr_", "placeholder",
            "banner", "advert", "/ad/", "blank", "loading", "default", "watermark",
            "wechat", "appstore", "download", "arrow", "btn", "button", "star")
    return not any(j in low for j in junk)


async def extract(page, url: str, html: str = "") -> dict:
    """Parse the currently loaded detail page into a flat record."""
    car: dict = {"url": url}

    car["listing_id"] = _listing_id(url)
    car["slug"] = re.sub(r"^/products/|\.html?$", "", urllib.parse.urlsplit(url).path)
    car["title"] = _clean(await page.title())
    for sel, key in (("h1", "heading"), ("meta[property='og:title']", "og_title"),
                     ("meta[name='description']", "meta_description")):
        try:
            if sel.startswith("meta"):
                v = await page.get_attribute(sel, "content")
            else:
                v = await page.inner_text(sel)
            if v:
                car[key] = _clean(v)
        except Exception:
            pass

    # The payload behind the page holds the full spec set (100+ entries);
    # the DOM shows only a headline subset, so payload values win.
    specs: dict[str, str] = {}
    if html:
        specs.update(specsmod.extract(html))
    try:
        for k, v in await page.evaluate(JS_PAIRS):
            k, v = _clean(k), _clean(v)
            if k and v:
                specs.setdefault(k, v)
    except Exception as e:
        print(f"[detail] pair harvest failed: {e}")
    car["specs"] = specs

    # normalised columns
    for label, value in specs.items():
        field = _canonical(label)
        if field and field not in car:
            car[field] = value

    # the page never names make, model, colour, drive or seats — the URL does
    parsed = slugmod.parse(car.get("slug", ""))
    if parsed:
        car["slug_fields"] = parsed
        aliases = {"engine_from_slug": "engine",
                   "mileage_from_slug": "mileage",
                   "transmission_from_slug": "transmission"}
        for key, value in parsed.items():
            field = aliases.get(key, key)
            if field in ("listing_id",):
                continue
            if not car.get(field):
                car[field] = value

    # prices are often outside any label/value structure
    if "price" not in car:
        car["price"] = await _first_text(page, [
            "[class*=price] :text-matches('[0-9]')", "[class*=price]",
            "[class*=Price]", "strong:has-text('¥')", "*:has-text('¥')"])

    # structured data
    ld = []
    for blob in await page.evaluate(JS_JSONLD):
        try:
            ld.append(json.loads(blob))
        except Exception:
            pass
    if ld:
        car["json_ld"] = ld
    blobs = await page.evaluate(JS_BLOBS)
    if blobs:
        car["state_blobs"] = {k: (json.loads(v) if v.strip().startswith(("{", "["))
                                  else v) for k, v in blobs.items()}

    # full visible text, so nothing on the page is lost
    try:
        car["page_text"] = _clean(await page.evaluate("document.body.innerText"))[:20_000]
    except Exception:
        pass

    # photos: the page's own gallery data, which is the only reliable source
    gallery = photos.extract(html or await page.content(),
                             limit=config.MAX_IMAGES_PER_CAR)
    if not gallery:                       # fallback: scrape the DOM
        seen = set()
        for u in await page.evaluate(JS_IMAGES):
            if not _plausible_photo(u):
                continue
            full = upgrade_image_url(u)
            if full not in seen:
                seen.add(full)
                gallery.append({"url": full, "source_url": u, "kind": "dom"})
        gallery = gallery[:config.MAX_IMAGES_PER_CAR]
        print("[detail] gallery data missing, fell back to DOM images")

    car["images"] = gallery
    car["image_count"] = len(gallery)
    car["videos"] = photos.videos(html) if html else []
    return car


async def _first_text(page, selectors: list[str]) -> str:
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                t = _clean(await el.inner_text())
                if t and re.search(r"\d", t):
                    return t[:120]
        except Exception:
            continue
    return ""


def _listing_id(url: str) -> str:
    """The site's own id for a car.

    Detail URLs look like
    /products/toyota-corolla-2023-12l-white-26200km-at-2wd-5-seats-jgxhm6tezn.html
    and the final slug token is the stable per-car id.
    """
    path = urllib.parse.urlsplit(url).path
    m = re.search(r"/products/(.+?)\.html?$", path, re.I)
    if m:
        slug = m.group(1)
        tail = slug.rsplit("-", 1)[-1]
        if re.fullmatch(r"[a-z0-9]{6,}", tail, re.I):
            return tail
        return slug[-60:]
    m = re.search(r"(\d{5,}[a-z]?)(?:\.html?)?/?$", path, re.I)
    if m:
        return m.group(1)
    return re.sub(r"[^\w]+", "_", path.strip("/"))[-60:] or "unknown"


async def fetch(page, url: str) -> dict | None:
    """Open a detail page and extract it; None if the check blocked the page."""
    if not await browser.goto(page, url, label=f"car {url}"):
        return None
    await page.wait_for_timeout(int(config.REQUEST_DELAY * 1000))
    # trigger lazy galleries
    for _ in range(3):
        await page.mouse.wheel(0, 3000)
        await page.wait_for_timeout(600)
    html = ""
    try:
        html = await page.content()
        (config.RAW / f"{_listing_id(url)}.html").write_text(html, encoding="utf-8")
    except Exception:
        pass
    return await extract(page, url, html)
