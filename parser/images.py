"""Download car photos at the best resolution the CDN will serve.

For each photo the upgraded (full-size) URL is tried first; if it 404s or comes
back smaller than the thumbnail, the original URL is kept instead — so the file
on disk is always the largest variant actually available.
"""
import asyncio
import hashlib
import mimetypes
from pathlib import Path

import httpx

from . import config

EXT_BY_TYPE = {"image/jpeg": ".jpg", "image/png": ".png",
               "image/webp": ".webp", "image/avif": ".avif"}


def _name(idx: int, url: str, ext: str) -> str:
    digest = hashlib.sha1(url.encode()).hexdigest()[:8]
    return f"{idx:02d}_{digest}{ext}"


async def _get(client: httpx.AsyncClient, url: str) -> httpx.Response | None:
    try:
        r = await client.get(url)
        if r.status_code == 200 and r.content and r.headers.get(
                "content-type", "").startswith("image/"):
            return r
    except Exception:
        pass
    return None


async def _one(client: httpx.AsyncClient, sem: asyncio.Semaphore, car_dir: Path,
               idx: int, img: dict) -> dict:
    full, thumb = img["url"], img.get("source_url", img["url"])
    async with sem:
        best = await _get(client, full)
        if best is None and thumb != full:
            best = await _get(client, thumb)
        elif best is not None and thumb != full:
            alt = await _get(client, thumb)
            if alt is not None and len(alt.content) > len(best.content):
                best = alt        # the "upgrade" was actually the smaller file

    if best is None:
        return {**img, "downloaded": False}

    ctype = best.headers.get("content-type", "").split(";")[0]
    ext = EXT_BY_TYPE.get(ctype) or mimetypes.guess_extension(ctype) or ".jpg"
    path = car_dir / _name(idx, full, ext)
    path.write_bytes(best.content)
    return {**img, "downloaded": True, "file": str(path),
            "bytes": len(best.content), "final_url": str(best.url)}


async def download_car(car: dict, cookies: list[dict]) -> dict:
    """Fetch every photo of one car into data/images/<listing_id>/."""
    imgs = car.get("images") or []
    if not imgs or not config.DOWNLOAD_IMAGES:
        return car

    car_dir = config.IMAGES / str(car.get("listing_id", "unknown"))
    car_dir.mkdir(parents=True, exist_ok=True)

    jar = {c["name"]: c["value"] for c in cookies if "guazi" in c.get("domain", "")}
    headers = {"User-Agent": config.USER_AGENT, "Referer": car.get("url", config.BASE_URL),
               "Accept": "image/avif,image/webp,image/png,image/*,*/*;q=0.8"}
    sem = asyncio.Semaphore(config.IMAGE_CONCURRENCY)

    async with httpx.AsyncClient(timeout=60, headers=headers, cookies=jar,
                                 follow_redirects=True) as client:
        results = await asyncio.gather(*[
            _one(client, sem, car_dir, i, img) for i, img in enumerate(imgs, 1)])

    car["images"] = results
    car["images_downloaded"] = sum(1 for r in results if r.get("downloaded"))
    car["images_dir"] = str(car_dir)
    return car
