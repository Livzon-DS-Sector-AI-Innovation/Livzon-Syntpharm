"""临时脚本：第二批 6 页截图 + 控制台报错检查。"""

import asyncio
import sys

sys.path.insert(0, "/app")

from sqlalchemy import select

from app.core.database import async_session_factory
from app.platform.identity.models import User
from app.platform.identity.service import generate_jwt


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
        errors: list[str] = []
        page.on("console", lambda m: errors.append(f"{page.url}: {m.text[:120]}") if m.type == "error" else None)

        simple_pages = [
            ("reg-dashboard", "/registration/regulation", "h1"),
            ("reg-list", "/registration/regulation/list", "h1"),
            ("va-list", "/registration/validation-audit", "h1"),
            ("va-new", "/registration/validation-audit/new", "h1"),
        ]
        for name, path, wait in simple_pages:
            await page.goto("http://localhost:3000" + path, wait_until="domcontentloaded")
            await page.wait_for_selector(wait, timeout=60000)
            await page.wait_for_timeout(3000)
            title = await page.evaluate("document.querySelector('h1')?.textContent")
            print(f"{name}: title={title}")
            await page.screenshot(path=f"/tmp/p2-{name}.png")

        # 法规详情：从列表点第一行进入
        await page.goto("http://localhost:3000/registration/regulation/list", wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)
        clicked = await page.evaluate("""() => {
          const rows = document.querySelectorAll('[class*=panel] div[style*=border-left]')
          if (rows.length) { rows[0].dispatchEvent(new MouseEvent('click', {bubbles:true})); return true }
          return false
        }""")
        if clicked:
            await page.wait_for_timeout(4000)
            print("reg-detail: url=", page.url)
            await page.screenshot(path="/tmp/p2-reg-detail.png")
        else:
            print("reg-detail: no rows, skipped")

        # 验证审计详情：从列表点第一行「查看」
        await page.goto("http://localhost:3000/registration/validation-audit", wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)
        clicked = await page.evaluate("""() => {
          const btn = document.querySelector('tbody tr button[class*=opLink]')
          if (btn) { btn.dispatchEvent(new MouseEvent('click', {bubbles:true})); return true }
          return false
        }""")
        if clicked:
            await page.wait_for_timeout(4000)
            print("va-detail: url=", page.url)
            await page.screenshot(path="/tmp/p2-va-detail.png")
        else:
            print("va-detail: no rows, skipped")

        print("CONSOLE_ERRORS:", errors if errors else "none")
        await browser.close()


asyncio.run(main())
