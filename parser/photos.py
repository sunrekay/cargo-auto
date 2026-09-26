"""Pull the car's real photo gallery out of the page's own data.

Scraping <img> tags on this site yields interface chrome — brand logos, flags,
48x48 icons — because the gallery is rendered by Next.js from a streamed data
payload. That payload also carries the authoritative list: for every photo a
full-resolution `imgUrl` (1280x960), a thumbnail, and a caption such as
"Front Left 45 Deg", "Steering Wheel" or "Engine Bay".

`images` is the whole gallery; the three themed lists are its parts and are read
as well, so a page that ships only the parts still yields everything.
"""
import json
import re

from . import nextdata

# ordered: the union list first, then the themed lists it is composed of
LIST_KEYS = ("images", "exteriorImageList", "interiorImageList", "detailImageList")
KIND = {"exteriorImageList": "exterior", "interiorImageList": "interior",
        "detailImageList": "detail", "images": "gallery"}

PHOTO_HOSTS = ("global-image-pub.guazistatic-global.com",
               "image-oversea.guazistatic-global.com")


flight_blob = nextdata.flight_blob


_json_array_at = nextdata.json_array_at


def original(url: str) -> str:
    """Strip the CDN's processing query to get the untouched upload."""
    return (url or "").split("?")[0]


def extract(html: str, limit: int | None = None) -> list[dict]:
    """Every gallery photo on the page, largest variant first, deduplicated."""
    blob = flight_blob(html)
    out: list[dict] = []
    seen: set[str] = set()

    for key in LIST_KEYS:
        for m in re.finditer(rf'"{key}"\s*:\s*\[', blob):
            arr = _json_array_at(blob, m.end() - 1)
            if not arr:
                continue
            try:
                items = json.loads(arr)
            except Exception:
                continue
            for it in items:
                if not isinstance(it, dict):
                    continue
                big = original(it.get("imgUrl") or "")
                small = original(it.get("smallImgUrl") or "")
                url = big or small
                if not url or not any(h in url for h in PHOTO_HOSTS) or url in seen:
                    continue
                seen.add(url)
                out.append({
                    "url": url,                      # full resolution
                    "source_url": small or big,      # thumbnail the page showed
                    "alt": it.get("alt"),            # e.g. "Front Left 45 Deg"
                    "kind": KIND.get(key, key),
                    "index": it.get("ind"),
                })
    return out[:limit] if limit else out


def videos(html: str) -> list[dict]:
    """Condition videos, when the listing has them."""
    blob = flight_blob(html)
    m = re.search(r'"conditionVideos"\s*:\s*\[', blob)
    if not m:
        return []
    arr = _json_array_at(blob, m.end() - 1)
    try:
        items = json.loads(arr) if arr else []
    except Exception:
        return []
    return [{"url": original(i.get("videoUrl") or ""), "name": i.get("showName"),
             "cover": original(i.get("coverUrl") or "")}
            for i in items if isinstance(i, dict) and i.get("videoUrl")]
