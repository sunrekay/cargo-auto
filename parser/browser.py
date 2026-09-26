"""Browser lifecycle and the human-in-the-loop handling of the site's check.

en.guazi.com sits behind Tencent EdgeOne, which answers automated traffic with
an interactive "check the box" CAPTCHA. This module never tries to solve or
evade that check: when it appears, the run pauses and asks the person watching
through noVNC to clear it. Because the profile is persistent, one pass is
usually enough for the whole session.
"""
import asyncio
import time

from playwright.async_api import async_playwright

from . import config

CHALLENGE_MARKERS = (
    "Verifying the safety of the connection",
    "Protected by Tencent Cloud EdgeOne",
    "solveChallenge",
    "gcaptcha",
    "TEOCaptcha",
)

LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
    "--window-size=1600,1000",
]


def _clear_stale_locks() -> None:
    """Drop Chromium's singleton locks left behind by a crashed run.

    They are symlinks naming a pid on a host that no longer exists, and they
    stop the next launch from opening the same profile.
    """
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        lock = config.PROFILE / name
        if lock.exists() or lock.is_symlink():
            lock.unlink(missing_ok=True)
            print(f"[browser] removed stale {name}")


class Browser:
    def __init__(self):
        self._pw = None
        self.ctx = None

    async def __aenter__(self):
        _clear_stale_locks()
        self._pw = await async_playwright().start()
        # A persistent profile keeps cookies (including a cleared check) between runs.
        self.ctx = await self._pw.chromium.launch_persistent_context(
            user_data_dir=str(config.PROFILE),
            headless=config.HEADLESS,
            args=LAUNCH_ARGS,
            user_agent=config.USER_AGENT,
            viewport={"width": 1600, "height": 950},
            locale="en-US",
            timezone_id="UTC",
        )
        self.ctx.set_default_navigation_timeout(config.NAV_TIMEOUT)
        self.ctx.set_default_timeout(config.NAV_TIMEOUT)
        return self

    async def __aexit__(self, *exc):
        try:
            if self.ctx:
                await self.ctx.close()
        finally:
            if self._pw:
                await self._pw.stop()

    async def page(self):
        pages = self.ctx.pages
        return pages[0] if pages else await self.ctx.new_page()


async def is_challenged(page) -> bool:
    """Is the current document the anti-bot interstitial rather than content?"""
    try:
        html = await page.content()
    except Exception:
        return False
    if len(html) > 60_000:
        return False
    return any(m in html for m in CHALLENGE_MARKERS)


async def goto(page, url: str, *, label: str = "") -> bool:
    """Navigate, then make sure real content (not the check) is on screen."""
    await page.goto(url, wait_until="domcontentloaded")
    try:
        await page.wait_for_load_state("networkidle", timeout=15_000)
    except Exception:
        pass
    if await is_challenged(page):
        return await wait_for_human(page, label or url)
    return True


async def wait_for_human(page, label: str) -> bool:
    """Pause until a person clears the site's check in the noVNC window.

    The check is deliberately left to a human — the crawler does not attempt it.
    """
    print("\n" + "=" * 72)
    print("  The site is asking for a human check (Tencent EdgeOne CAPTCHA).")
    print(f"  page: {label}")
    print("  Open  ->  http://localhost:6080/   and clear it in that browser.")
    print(f"  Waiting up to {config.HUMAN_WAIT}s, then giving up on this page.")
    print("=" * 72 + "\n", flush=True)

    deadline = time.monotonic() + config.HUMAN_WAIT
    while time.monotonic() < deadline:
        await asyncio.sleep(3)
        if not await is_challenged(page):
            print("[check] cleared, continuing\n", flush=True)
            await asyncio.sleep(1.5)
            return True
        left = int(deadline - time.monotonic())
        if left % 30 < 3:
            print(f"[check] still waiting ({left}s left)", flush=True)
    print("[check] not cleared in time — skipping this page", flush=True)
    return False
