"""Look at the real listing page: how many cars per page, and how to page on."""
import asyncio, json, re, urllib.parse
from collections import Counter
from pathlib import Path
from parser import browser, config

OUT = Path("data/recon"); OUT.mkdir(parents=True, exist_ok=True)
PAGES = ["https://en.guazi.com/used-cars/", "https://en.guazi.com/used-cars/toyota/"]


async def look(page, url):
    print(f"\n=== {url}")
    if not await browser.goto(page, url, label=url):
        print("   blocked"); return
    await page.wait_for_timeout(2500)
    before = 0
    for i in range(8):                       # scroll: does it lazy-load more cars?
        await page.mouse.wheel(0, 6000); await page.wait_for_timeout(1200)
        n = await page.evaluate("document.querySelectorAll('a[href*=\"/products/\"]').length")
        if n == before and i > 2: break
        before = n
    info = await page.evaluate("""() => {
        const A = [...document.querySelectorAll('a[href]')].map(a => a.href);
        const prod = A.filter(h => h.includes('/products/'));
        return {
            title: document.title, url: location.href, total: A.length,
            products: [...new Set(prod)],
            others: [...new Set(A.filter(h => !h.includes('/products/')
                        && h.startsWith('https://en.guazi.com')))],
            pager: [...document.querySelectorAll('[class*=pag],[class*=Pag],[class*=next],[class*=more],[class*=load]')]
                     .slice(0,12).map(e => (e.tagName+'.'+(e.className||'')).slice(0,80)
                                            + ' :: ' + (e.innerText||'').replace(/\\s+/g,' ').slice(0,40)),
            text_tail: document.body.innerText.replace(/\\s+/g,' ').slice(-400),
        };
    }""")
    print(f"   title    : {info['title'][:70]}")
    print(f"   products : {len(info['products'])} unique car links (of {info['total']} anchors)")
    for h in info["products"][:3]:
        print(f"              {h}")
    shapes = Counter(re.sub(r"\d+","N",urllib.parse.urlsplit(h).path) for h in info["others"])
    pager_like = [s for s,_ in shapes.items() if re.search(r"/(p|page|o|pn)\d|/\d+/?$", s)]
    print(f"   pager-ish paths: {pager_like[:8] or 'none'}")
    print(f"   pager widgets  : {info['pager'][:6] or 'none'}")
    print(f"   page tail      : {info['text_tail'][-220:]}")
    slug = re.sub(r"\W+","_",urllib.parse.urlsplit(url).path)
    (OUT/f"listing{slug}.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    await page.screenshot(path=str(OUT/f"listing{slug}.png"))


async def main():
    async with browser.Browser() as b:
        page = await b.page()
        for u in PAGES:
            try: await look(page, u)
            except Exception as e: print(f"   failed: {type(e).__name__}: {e}")

asyncio.run(main())
