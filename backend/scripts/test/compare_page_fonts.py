"""临时脚本：对比概览页与申报进度页的字号阶梯。"""

import asyncio
import sys

sys.path.insert(0, "/app")

from sqlalchemy import select

from app.core.database import async_session_factory
from app.platform.identity.models import User
from app.platform.identity.service import generate_jwt

JS = """
() => {
  const cs = el => el ? getComputedStyle(el).fontSize : 'n/a'
  const pick = sel => document.querySelector(sel)
  const byText = (tag, txt) => [...document.querySelectorAll(tag)].find(e => e.textContent.trim().startsWith(txt))
  return {
    h1: cs(pick('h1')),
    pageSub: cs(document.querySelector('[class*=pageSub]')),
    btn: cs(byText('button', '刷新')),
    kpiNum: cs(document.querySelector('[class*=kpiNum]')),
    kpiLabel: cs(document.querySelector('[class*=kpiLabel]')),
    panelTitle: cs(document.querySelector('[class*=panelTitle]')),
    itemName: cs(document.querySelector('[class*=queueName], tbody tr.ant-table-row td')),
    auxText: cs(document.querySelector('[class*=queueMeta], [class*=bizDesc], [class*=kpiSub], [class*=toolbarHint]')),
    tag: cs(document.querySelector('span[class*=tag]')),
    th: cs(document.querySelector('thead th')),
    td: cs(document.querySelector('tbody tr.ant-table-row td')),
  }
}
"""


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
        for name, path, wait in [
            ("概览页", "/registration", "[class*=queueRow]"),
            ("申报进度页", "/registration/review", "tbody tr.ant-table-row td"),
        ]:
            await page.goto("http://localhost:3000" + path, wait_until="domcontentloaded")
            await page.wait_for_selector(wait, timeout=90000)
            await page.wait_for_timeout(2000)
            r = await page.evaluate(JS)
            print(name, r)
        await browser.close()


asyncio.run(main())
