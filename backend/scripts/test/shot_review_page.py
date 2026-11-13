"""临时验收脚本：用容器内 Playwright 截图申报进度查询页（列表 + 抽屉）。

用法：
    docker exec -w /app erp-backend /app/.venv/bin/python scripts/shot_review_page.py
输出：/tmp/review-list.png、/tmp/review-drawer.png
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.core.database import async_session_factory
from app.platform.identity.models import User
from app.platform.identity.service import generate_jwt

# 通过 host-resolver-rules 把 localhost 解析到 frontend 容器：
# dev 服务器的跨站资源白名单（ALLOWED_DEV_ORIGINS）默认只放行 localhost，
# 直接用 http://frontend:3000 会被拦，导致客户端 JS 不加载。
FRONTEND = "http://localhost:3000"


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
        await ctx.add_cookies([{"name": "auth_token", "value": token, "url": FRONTEND}])
        page = await ctx.new_page()

        errors: list[str] = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        async def log_api(resp) -> None:
            if "/api/v1/registration" in resp.url:
                body = (await resp.text())[:200]
                print(f"API {resp.status} {resp.url.split('3000')[-1]} -> {body}")

        page.on("response", lambda resp: asyncio.ensure_future(log_api(resp)))

        await page.goto(f"{FRONTEND}/registration/review", wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
        print("URL:", page.url)
        body_text = await page.inner_text("body")
        print("BODY:", body_text[:300].replace("\n", " | "))
        await page.screenshot(path="/tmp/debug.png")
        await page.wait_for_selector("table tbody tr", timeout=60000)
        await page.wait_for_timeout(3000)
        await page.screenshot(path="/tmp/review-list.png")

        await page.click("tr.ant-table-row >> nth=0")
        await page.wait_for_selector(".ant-drawer-content-wrapper", timeout=15000)
        await page.wait_for_timeout(3000)
        await page.screenshot(path="/tmp/review-drawer.png")

        print("CONSOLE_ERRORS:", errors if errors else "none")
        await browser.close()


asyncio.run(main())
