"""临时验收脚本：DOM 级核对申报进度查询页最终版规格。

用法：docker exec -w /app erp-backend /app/.venv/bin/python scripts/verify_review_page.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.core.database import async_session_factory
from app.platform.identity.models import User
from app.platform.identity.service import generate_jwt

FRONTEND = "http://localhost:3000"

CHECK_JS = """
() => {
  const out = {}
  const cs = el => el ? getComputedStyle(el) : null
  const table = document.querySelector('table')
  const tableW = table?.getBoundingClientRect().width ?? 1
  out.colWidths = [...table.querySelectorAll('thead th')].map(th =>
    Math.round(th.getBoundingClientRect().width / tableW * 100) + '%').join('/')
  out.thAligns = [...table.querySelectorAll('thead th')].map(th => cs(th).textAlign).join('/')
  const row = document.querySelector('tbody tr.ant-table-row')
  out.tdAligns = [...row.querySelectorAll('td')].map(td => cs(td).textAlign).join('/')
  const th = table.querySelector('thead th')
  out.thStyle = `bg=${cs(th).backgroundColor} size=${cs(th).fontSize} color=${cs(th).color}`
  const td = row.querySelector('td')
  out.tdStyle = `size=${cs(td).fontSize} padding=${cs(td).padding}`
  out.rows = [...document.querySelectorAll('tbody tr.ant-table-row')].map(tr =>
    [...tr.querySelectorAll('td')].map(td => td.textContent.trim().replace(/\\s+/g, ' ')).join(' | '))
  // 分段横线
  const segsWrap = row.querySelector('div[class*="segments"]')
  const segs = [...segsWrap.querySelectorAll('i')]
  const segCs = cs(segs[0])
  out.segCount = segs.length
  out.segSpec = `h=${segCs.height} r=${segCs.borderRadius} gap=${cs(segsWrap).gap}`
  out.segFilledCount = segs.filter(s => cs(s).backgroundColor === 'rgb(95, 86, 214)').length
  const hollow = segs.find(s => cs(s).backgroundColor !== 'rgb(95, 86, 214)')
  out.segHollow = hollow ? `border=${cs(hollow).borderColor} ${cs(hollow).borderWidth} bg=${cs(hollow).backgroundColor}` : 'none'
  out.segWrapWidth = `${cs(segsWrap).maxWidth} flexGrow=${cs(segsWrap).flexGrow}`
  const num = row.querySelector('span[class*="segNum"]')
  out.segNum = `${num.textContent} size=${cs(num).fontSize} color=${cs(num).color}`
  const tag = row.querySelectorAll('td')[4]?.querySelector('span')
  out.nodeTag = tag ? `size=${cs(tag).fontSize} bg=${cs(tag).backgroundColor} color=${cs(tag).color}` : 'not-found'
  out.titleSize = cs(document.querySelector('h1'))?.fontSize
  out.kpiNumSize = cs([...document.querySelectorAll('div')].find(d => /^\\d+$/.test(d.textContent) && d.children.length === 0 && cs(d).fontSize === '36px'))?.fontSize || 'not-found'
  const btn = [...document.querySelectorAll('button')].find(b => b.textContent.includes('刷新'))
  out.btnSize = cs(btn)?.fontSize
  const foot = document.querySelector('div[class*="tableFoot"]')
  out.footTotal = foot?.querySelector('span')?.textContent + ' size=' + cs(foot?.querySelector('span'))?.fontSize
  const active = foot?.querySelector('.ant-pagination-item-active')
  out.pageActive = active ? `bg=${cs(active).backgroundColor} text=${cs(active.querySelector('a'))?.color}` : 'not-found'
  // 全页字号扫描：揪出 12/13px 文字
  const bad = []
  document.querySelectorAll('div[class*="regUi"] *').forEach(el => {
    const t = el.textContent?.trim()
    if (t && el.children.length === 0 && el.offsetParent !== null) {
      const s = cs(el).fontSize
      if (s === '12px' || s === '13px') bad.push(`${t.slice(0, 12)}=${s}`)
    }
  })
  out.badFonts = bad.length ? bad.slice(0, 8) : 'none'
  return out
}
"""

DRAWER_JS = """
() => {
  const out = {}
  const cs = el => el ? getComputedStyle(el) : null
  const drawer = document.querySelector('.ant-drawer')
  out.drawerOpen = !!drawer
  const body = drawer?.querySelector('.ant-drawer-content-wrapper')
  out.drawerWidth = cs(body)?.width
  out.drawerNameSize = cs(drawer?.querySelector('div[class*="drawerName"]'))?.fontSize
  out.hasSummary = !!drawer?.querySelector('div[class*="summary"]')
  const items = drawer ? [...drawer.querySelectorAll('div[class*="tlItem"]')] : []
  out.nodeCount = items.filter(el => !el.className.includes('tlTitle')).length
  const expanded = items.filter(el => el.className.includes('Expanded'))
  out.expandedCount = expanded.length
  const dots = [...drawer?.querySelectorAll('div[class*="tlDot"]') ?? []]
  out.firstDots = dots.slice(0, 4).map(d => `${d.textContent.trim()} bg=${cs(d).backgroundColor}`)
  // 抽屉内 12/13px 文字扫描
  const bad = []
  drawer?.querySelectorAll('*').forEach(el => {
    const t = el.textContent?.trim()
    if (t && el.children.length === 0 && el.offsetParent !== null) {
      const s = cs(el).fontSize
      if (s === '12px' || s === '13px') bad.push(`${t.slice(0, 12)}=${s}`)
    }
  })
  out.drawerBadFonts = bad.length ? bad.slice(0, 8) : 'none'
  return out
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
        await ctx.add_cookies([{"name": "auth_token", "value": token, "url": FRONTEND}])
        page = await ctx.new_page()

        errors: list[str] = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        await page.goto(f"{FRONTEND}/registration/review", wait_until="domcontentloaded")
        await page.wait_for_selector("tbody tr.ant-table-row td", timeout=60000)
        await page.wait_for_timeout(2500)

        print("== 列表页 ==")
        for k, v in (await page.evaluate(CHECK_JS)).items():
            print(f"{k}: {v}")

        await page.click("tr.ant-table-row >> nth=0")
        await page.wait_for_selector(".ant-drawer-content-wrapper", timeout=15000)
        await page.wait_for_timeout(3000)

        print("== 抽屉 ==")
        for k, v in (await page.evaluate(DRAWER_JS)).items():
            print(f"{k}: {v}")

        print("CONSOLE_ERRORS:", errors if errors else "none")
        await browser.close()


asyncio.run(main())
