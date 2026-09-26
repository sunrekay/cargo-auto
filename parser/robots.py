"""robots.txt enforcement.

en.guazi.com allows public pages but blocks every query-string URL plus /api/
and /os/, so the crawler sticks to clean path URLs. Rules are fetched live and
re-checked for each URL rather than hardcoded.
"""
import urllib.parse
from urllib.robotparser import RobotFileParser

import httpx

from . import config

_rp: RobotFileParser | None = None
_raw = ""


def load() -> str:
    """Fetch and parse robots.txt. Fails closed only for the hard-coded rules."""
    global _rp, _raw
    url = f"{config.BASE_URL}/robots.txt"
    try:
        r = httpx.get(url, timeout=30, headers={"User-Agent": config.USER_AGENT},
                      follow_redirects=True)
        r.raise_for_status()
        _raw = r.text
    except Exception as e:                      # keep the explicit rules below
        _raw = ""
        print(f"[robots] could not fetch {url}: {e}")
    _rp = RobotFileParser()
    _rp.parse(_raw.splitlines())
    return _raw


def allowed(url: str) -> bool:
    """True when the crawler may fetch this URL."""
    parts = urllib.parse.urlsplit(url)
    # Disallow: /*?*  — Python's parser handles wildcards poorly, so enforce it here
    if parts.query:
        return False
    path = parts.path or "/"
    if path.startswith(("/api/", "/os/")):
        return False
    if _rp is not None and not _rp.can_fetch("*", url):
        return False
    return True


def strip_query(url: str) -> str:
    """Drop query and fragment so a discovered link becomes a crawlable one."""
    p = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, "", ""))
