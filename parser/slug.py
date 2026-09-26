"""Decode the facts Guazi packs into a product URL.

The car's own page lists engine internals in detail (torque, valve train,
cylinder count) but never states make, model, colour, drive type or seat count.
The site does encode all of them in the URL it generates:

    volkswagen-magotan-2020-20l-yellow-141000km-at-2wd-5-seats-wbtxl2untx
    |________  ______| |__| |_| |____| |______| |_| |_| |_____| |_______|
       make   model    year  eng colour mileage box drive seats     id

Values parsed here are only used where the page itself says nothing, so page
data always wins.
"""
import json
import re
from pathlib import Path

from . import config

SLUG_RE = re.compile(
    r"^(?P<makemodel>.+?)"
    r"-(?P<year>(?:19|20)\d{2})"
    r"-(?P<engine>\d{2,3})l"
    r"(?:-(?P<colour>(?!\d+km)[a-z]+(?:-[a-z]+)?))?"
    r"-(?P<km>\d+)km"
    r"-(?P<gearbox>[a-z]+(?:-[a-z]+)?)"
    r"-(?P<drive>\d?wd|awd|fwd|rwd)"
    r"-(?P<seats>\d+)-seats"
    r"-(?P<id>[a-z0-9]+)$", re.I)

# brand slugs the site uses that are more than one word; the crawler adds to
# this from the /used-cars/<brand>/ category links it walks
MULTIWORD_BRANDS = {
    "geely-auto", "mercedes-benz", "land-rover", "alfa-romeo", "great-wall",
    "changan-auto", "gac-trumpchi", "aston-martin", "rolls-royce", "chery-auto",
    "beijing-auto", "dongfeng-fengxing", "roewe-auto", "faw-bestune", "jetta-vs",
}

GEARBOX = {"at": "Automatic", "mt": "Manual", "cvt": "CVT", "dct": "DCT",
           "amt": "AMT", "dsg": "DSG", "e-cvt": "E-CVT", "at-2wd": "Automatic"}
DRIVE = {"2wd": "2WD", "4wd": "4WD", "awd": "AWD", "fwd": "FWD", "rwd": "RWD"}

BRANDS_FILE = config.DATA / "brands.json"


def known_brands() -> set[str]:
    """Static list plus whatever brand slugs the crawler has seen on the site."""
    brands = set(MULTIWORD_BRANDS)
    try:
        brands |= set(json.loads(BRANDS_FILE.read_text(encoding="utf-8")))
    except Exception:
        pass
    return brands


def remember_brands(slugs) -> None:
    """Persist brand slugs discovered from category URLs."""
    try:
        existing = set(json.loads(BRANDS_FILE.read_text(encoding="utf-8")))
    except Exception:
        existing = set()
    merged = sorted(existing | {s.strip("/").lower() for s in slugs if s})
    BRANDS_FILE.write_text(json.dumps(merged, indent=2), encoding="utf-8")


def _titles(s: str) -> str:
    """'grand-voyager' -> 'Grand Voyager', keeping model codes uppercase."""
    words = []
    for w in s.split("-"):
        if re.fullmatch(r"[a-z]{1,3}\d*[a-z]?", w) and not w.isalpha():
            words.append(w.upper())          # a3, q2l, rav4, x1
        elif len(w) <= 3 and w in {"bmw", "byd", "gac", "faw", "suv", "gls", "glc"}:
            words.append(w.upper())
        else:
            words.append(w.capitalize())
    return " ".join(words)


def _split_make(makemodel: str, brands: set[str]) -> tuple[str, str]:
    """Longest brand slug that prefixes the string wins; else the first word."""
    best = ""
    for b in brands:
        if (makemodel == b or makemodel.startswith(b + "-")) and len(b) > len(best):
            best = b
    if not best:
        best = makemodel.split("-")[0]
    rest = makemodel[len(best):].strip("-")
    return _titles(best), _titles(rest)


def parse(slug: str, brands: set[str] | None = None) -> dict:
    """Fields encoded in a product slug; empty dict when it does not match."""
    m = SLUG_RE.match(slug.strip("/").lower())
    if not m:
        return {}
    g = m.groupdict()
    brands = brands if brands is not None else known_brands()
    make, model = _split_make(g["makemodel"], brands)

    engine = g["engine"]
    litres = f"{int(engine) / 10:.1f}L" if engine and int(engine) else None

    out = {
        "make": make or None,
        "model": model or None,
        "year": g["year"],
        "engine_from_slug": litres,
        "colour": _titles(g["colour"]) if g["colour"] else None,
        "mileage_from_slug": f"{int(g['km']):,} km",
        "transmission_from_slug": GEARBOX.get(g["gearbox"], g["gearbox"].upper()),
        "drive_type": DRIVE.get(g["drive"], g["drive"].upper()),
        "seats": g["seats"],
        "listing_id": g["id"],
    }
    if litres and int(engine) == 0:
        out["engine_from_slug"] = "Electric"
    return {k: v for k, v in out.items() if v}
