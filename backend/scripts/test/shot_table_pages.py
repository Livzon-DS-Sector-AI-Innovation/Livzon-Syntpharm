"""临时脚本：4 个改版表格页截图 + 控制台报错检查。"""

import asyncio
import sys

sys.path.insert(0, "/app")

from sqlalchemy import select

from app.core.database import async_session_factory
from app.platform.identity.models import User
from app.platform.identity.service import generate_jwt

PAGES = [
    ("auth-letter", "/registration/authorization-letter", "table tbody tr, div[class*=emptyBody]"),
    ("ref-standard", "/registration/reference-standard", "table tbody tr, div[class*=emptyBody]"),
    ("supp-reply", "/registration/supplementary-reply", "table tbody tr, div[class*=emptyBody]"),
    ("dossier-writer", "/registration/dossier-writer", "table tbody tr, div[class*=emptyBody]"),
]


async def main() -> None:
    async with async_session_factory() as db:
        user = (
            await db.execute(
                select(User).where(User.status == "active", User.name == "陈莹莹").limit(1)
            )
        ).scalar_one()
    token = generate_jwt(user)

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            args=["--host-resolver-rules=MAP localhost frontend"]
        )
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        await ctx.add_cookies([{"name": "auth_token", "value": token, "url": "http://localhost:3000"}])
        page = await ctx.new_page()
        for name, path, wait in PAGES:
            errors: list[str] = []
            page.on("console", lambda m: errors.append(m.text[:120]) if m.type == "error" else None)
            await page.goto("http://localhost:3000" + path, wait_until="domcontentloaded")
            try:
                await page.wait_for_selector(wait, timeout=60000, state="visible")
            except Exception:
                print(f"{name}: wait timeout (may be empty list)")
            await page.wait_for_timeout(2500)
            # 抽取页头标题与表格容器样式做快速核对
            info = await page.evaluate("""() => {
              const h1 = document.querySelector('[class*=pageTitle] h1')
              const th = document.querySelector('thead th')
              const cs = el => el ? getComputedStyle(el) : null
              return {
                title: h1?.textContent,
                titleSize: cs(h1)?.fontSize,
                thBg: cs(th)?.backgroundColor,
                thSize: cs(th)?.fontSize,
              }
            }""")
            print(f"{name}: {info} errors={errors if errors else 'none'}")
            await page.screenshot(path=f"/tmp/page-{name}.png")
        await browser.close()


asyncio.run(main())
