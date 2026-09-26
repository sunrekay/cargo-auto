import asyncio, os, re
from pathlib import Path
from playwright.async_api import async_playwright

URL = os.getenv("START_URL")
OUT = Path("data/recon"); OUT.mkdir(parents=True, exist_ok=True)

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = await b.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900}, locale="en-US")
        p = await ctx.new_page()
        await p.goto(URL, wait_until="commit", timeout=40_000)
        for i in range(8):
            await p.wait_for_timeout(4000)
            html = await p.content()
            txt = re.sub(r"\s+", " ", await p.evaluate("document.body.innerText"))[:400]
            ck = [c["name"] for c in await ctx.cookies()]
            print(f"[{i*4+4:3d}s] url={p.url[:60]} html={len(html):7d} cookies={ck}")
            print(f"       text: {txt!r}")
            if len(html) > 60_000:
                print("       -> real content likely loaded")
                break
        (OUT / "challenge_state.html").write_text(await p.content(), encoding="utf-8")
        await p.screenshot(path=str(OUT / "challenge_state.png"))
        # is there an interactive captcha visible?
        frames = [f.url[:100] for f in p.frames]
        print("frames:", frames)
        await b.close()

asyncio.run(main())
