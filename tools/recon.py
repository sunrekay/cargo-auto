"""Dump the real structure of the listing pages.

Runs on the same persistent profile as the parser, so the check cleared earlier
still applies. Writes link inventories, HTML and screenshots to data/recon/.
"""
import asyncio
import json
import re
import urllib.parse
from collections import Counter
from pathlib import Path

from parser import browser, config

OUT = Path("data/recon")

CANDIDATES = [
    "https://en.guazi.com/",
    "https://en.guazi.com/bin/",
    "https://en.guazi.com/bin/buy/",
]


async def probe(page, url: str) -> dict:
    print(f"\n=== {url}")
    ok = await browser.goto(page, url, label=url)
    if not ok:
        print("    blocked by the check")
        return {"url": url, "blocked": True}
    await page.wait_for_timeout(3000)
    for _ in range(5):
        await page.mouse.wheel(0, 5000)
        await page.wait_for_timeout(800)

    slug = re.sub(r"\W+", "_", urllib.parse.urlsplit(url).path) or "root"
    html = await page.content()
    (OUT / f"{slug}.html").write_text(html, encoding="utf-8")
    await page.screenshot(path=str(OUT / f"{slug}.png"), full_page=False)

    info = await page.evaluate("""() => {
        const A = [...document.querySelectorAll('a[href]')];
        return {
            title: document.title,
            url: location.href,
            anchors: A.length,
            hrefs: A.map(a => a.href),
            // clickable things that are NOT anchors (SPA cards)
            clickish: [...document.querySelectorAll('[onclick],[data-href],[data-url],[data-link],[role=link]')]
                        .slice(0, 20)
                        .map(e => e.tagName + ' ' + (e.className || '').toString().slice(0, 60)),
            text: document.body.innerText.replace(/\\s+/g, ' ').slice(0, 600),
            imgs: document.querySelectorAll('img').length,
        };
    }""")

    print(f"    title  : {info['title'][:80]}")
    print(f"    landed : {info['url']}")
    print(f"    anchors: {info['anchors']}  imgs: {info['imgs']}  non-anchor clickables: {len(info['clickish'])}")
    print(f"    text   : {info['text'][:220]}")

    hrefs = info["hrefs"]
    same = [h for h in hrefs if h.startswith(config.BASE_URL)]
    shapes = Counter(re.sub(r"\d+", "N", urllib.parse.urlsplit(h).path) for h in same)
    print(f"    {len(same)}/{len(hrefs)} links on this host, {len(shapes)} shapes:")
    for s, n in shapes.most_common(20):
        print(f"        {n:4d}  {s}")
    withq = [h for h in same if "?" in h]
    print(f"    links carrying a query string (robots-blocked): {len(withq)}")
    for h in withq[:5]:
        print(f"        {h[:110]}")
    if info["clickish"]:
        print("    non-anchor clickables:", info["clickish"][:6])

    (OUT / f"{slug}_links.json").write_text(
        json.dumps({"shapes": shapes.most_common(), "hrefs": sorted(set(same)),
                    "with_query": withq, **{k: info[k] for k in
                    ("title", "url", "anchors", "imgs", "clickish", "text")}},
                   indent=2, ensure_ascii=False), encoding="utf-8")
    return info


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    async with browser.Browser() as b:
        page = await b.page()
        for url in CANDIDATES:
            try:
                await probe(page, url)
            except Exception as e:
                print(f"    failed: {type(e).__name__}: {e}")
    print(f"\n[recon] dumps in {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
