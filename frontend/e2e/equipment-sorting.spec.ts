import { expect, test, type Page } from '@playwright/test'
import { readFileSync } from 'fs'
import path from 'path'
import { EQUIPMENT_SORT_FIELDS } from '@/lib/api/equipment-query'

const AUTH_FILE = path.join(__dirname, '.auth', 'storageState.json')
const SPEC_FILE = path.join(__dirname, '..', '..', 'backend', 'openapi.json')
const PAGE_URL = '/equipment/assets'

test.use({ storageState: AUTH_FILE })

// 窄视口下表格横向滚动，固定在右侧的「操作」列会压住表头，点击落到相邻 th 上
test.use({ viewport: { width: 1680, height: 950 } })

const isListRequest = (req: { url: () => string }) => req.url().includes('/api/v1/equipment/equipments?')

/**
 * 台账首屏由 SSR 渲染，客户端 hydration 后会再发一次列表请求。
 * 不先等这一次落地，交互断言就会捕到 hydration 请求而不是点击触发的那一次。
 */
async function gotoLedger(page: Page, query = '') {
  await page.goto(`${PAGE_URL}${query}`)
  await expect(page.getByRole('heading', { name: '设备台账' })).toBeVisible({ timeout: 15000 })
  await page.waitForLoadState('networkidle')
  await page.waitForResponse((res) => isListRequest(res.request()), { timeout: 15000 })
}

/** 执行 action 并返回它触发的列表请求参数 */
async function listRequestOf(page: Page, action: () => Promise<void>) {
  const [request] = await Promise.all([
    page.waitForRequest(isListRequest, { timeout: 15000 }),
    action(),
  ])
  return new URL(request.url()).searchParams
}

const header = (page: Page, title: string) => page.locator('th', { hasText: title }).first()

test.describe('设备台账动态排序', () => {
  test('点击表头：URL、请求参数与 aria-sort 三者一致', async ({ page }) => {
    await gotoLedger(page)
    const asc = await listRequestOf(page, () => header(page, '设备名称').click())
    expect(asc.get('sort_by')).toBe('name')
    expect(asc.get('sort_order')).toBe('asc')
    await expect(page).toHaveURL(/sort_by=name/)
    await expect(header(page, '设备名称')).toHaveAttribute('aria-sort', 'ascending')

    const desc = await listRequestOf(page, () => header(page, '设备名称').click())
    expect(desc.get('sort_order')).toBe('desc')
    await expect(page).toHaveURL(/sort_order=desc/)
    await expect(header(page, '设备名称')).toHaveAttribute('aria-sort', 'descending')
  })

  test('第三次点击取消排序，回落默认 asset_no 升序且清空查询串', async ({ page }) => {
    await gotoLedger(page)
    const name = header(page, '设备名称')
    await name.click()
    await expect(name).toHaveAttribute('aria-sort', 'ascending')
    await name.click()
    await expect(name).toHaveAttribute('aria-sort', 'descending')
    const params = await listRequestOf(page, () => name.click())
    expect(params.get('sort_by')).toBe('asset_no')
    expect(params.get('sort_order')).toBe('asc')
    await expect(page).toHaveURL((url) => !url.search.includes('sort_'))
    await expect(header(page, '资产编号')).toHaveAttribute('aria-sort', 'ascending')
  })

  test('刷新与分享：带排序参数的 URL 首屏即落在该排序视角', async ({ page }) => {
    await gotoLedger(page, '?sort_by=book_value&sort_order=desc')
    const params = await listRequestOf(page, () => page.reload())
    expect(params.get('sort_by')).toBe('book_value')
    expect(params.get('sort_order')).toBe('desc')
    // R5：排序列被列配置隐藏时表头无指示器，排序状态仍由筛选摘要承载
    await expect(page.locator('span', { hasText: '排序: 账面净值 ↓' })).toBeVisible()
  })

  test('排序切换重置到第 1 页，且不重置 page_size', async ({ page }) => {
    await gotoLedger(page, '?page=3&page_size=50')
    await expect(page).toHaveURL(/page=3/)
    const params = await listRequestOf(page, () => header(page, '投用日期').click())
    expect(params.get('page')).toBe('1')
    expect(params.get('page_size')).toBe('50')
    expect(params.get('sort_by')).toBe('commissioning_date')
    await expect(page).toHaveURL(/page_size=50/)
    await expect(page).toHaveURL((url) => !url.searchParams.has('page'))
  })

  test('「恢复默认」清除排序查询串并回到资产编号升序', async ({ page }) => {
    await gotoLedger(page, '?sort_by=status&sort_order=desc')
    const reset = page.getByRole('button', { name: '恢复默认' })
    await expect(reset).toBeVisible()
    const params = await listRequestOf(page, () => reset.click())
    expect(params.get('sort_by')).toBe('asset_no')
    expect(params.get('sort_order')).toBe('asc')
    await expect(page).toHaveURL((url) => !url.search.includes('sort_'))
    await expect(page.getByRole('button', { name: '恢复默认' })).toHaveCount(0)
  })

  test('负例：未知 sort_by 不发脏请求并给出可读提示', async ({ page }) => {
    let sentSortBy: string | null = null
    page.on('request', (req) => {
      if (isListRequest(req)) sentSortBy = new URL(req.url()).searchParams.get('sort_by')
    })
    await gotoLedger(page, '?sort_by=drop_table&sort_order=sideways')
    await expect.poll(() => sentSortBy, { timeout: 15000 }).toBe('asset_no')
    const tip = page.locator('span', { hasText: '排序参数无效' })
    await expect(tip).toBeVisible()
    await expect(tip).toContainText('sort_by=drop_table')
    await expect(tip).toContainText('sort_order=sideways')
    expect(sentSortBy).not.toBe('drop_table')
  })

  test('契约无漂移：前端可排序列集合与后端 OpenAPI enum 逐项相等', async () => {
    const spec = JSON.parse(readFileSync(SPEC_FILE, 'utf-8'))
    const params = spec.paths['/api/v1/equipment/equipments'].get.parameters
    const enumValues = params.find((p: { name: string }) => p.name === 'sort_by').schema.enum as string[]
    expect([...enumValues].sort()).toEqual([...EQUIPMENT_SORT_FIELDS].sort())
  })

  test('白名单 8 列全部可排序，非白名单列不渲染排序 affordance', async ({ page }) => {
    await gotoLedger(page)
    // 当前成本 / 账面净值 / 创建时间 默认隐藏，先在列配置里打开
    await page.getByRole('button', { name: '列配置' }).click()
    const modal = page.locator('.ant-modal')
    for (const title of ['当前成本', '账面净值', '创建时间']) {
      await modal.locator(`label.ant-checkbox-wrapper:has-text("${title}")`).first().click()
    }
    await modal.locator('.ant-modal-footer button').last().click()
    await expect(header(page, '创建时间')).toBeVisible({ timeout: 10000 })
    await page.waitForLoadState('networkidle')

    const whitelist: Array<[string, string]> = [
      ['资产编号', 'asset_no'],
      ['设备名称', 'name'],
      ['投用日期', 'commissioning_date'],
      ['当前成本', 'current_cost'],
      ['账面净值', 'book_value'],
      ['归属部门', 'department_name'],
      ['设备状态', 'status'],
      ['创建时间', 'created_at'],
    ]
    for (const [title, sortBy] of whitelist) {
      const th = header(page, title)
      await expect(th.locator('.ant-table-column-sorter')).toBeVisible()
      const params = await listRequestOf(page, () => th.click())
      expect(params.get('sort_by')).toBe(sortBy)
      await page.waitForLoadState('networkidle')
    }

    for (const title of ['设备位置', '负责人']) {
      await expect(header(page, title).locator('.ant-table-column-sorter')).toHaveCount(0)
    }
  })

  test('筛选与排序共存：筛选不丢排序、并把页码重置为 1', async ({ page }) => {
    await gotoLedger(page, '?sort_by=name&sort_order=desc&page=2')
    const params = await listRequestOf(page, async () => {
      const keyword = page.getByPlaceholder('搜索设备编号或名称')
      await keyword.fill('泵')
      await keyword.press('Enter')
    })
    expect(params.get('keyword')).toBe('泵')
    expect(params.get('sort_by')).toBe('name')
    expect(params.get('sort_order')).toBe('desc')
    expect(params.get('page')).toBe('1')
    await expect(page).toHaveURL(/sort_by=name&sort_order=desc/)
  })

  test('键盘可操作：表头聚焦后回车切换排序', async ({ page }) => {
    await gotoLedger(page)
    const th = header(page, '投用日期')
    await th.focus()
    const params = await listRequestOf(page, () => page.keyboard.press('Enter'))
    expect(params.get('sort_by')).toBe('commissioning_date')
    await expect(th).toHaveAttribute('aria-sort', 'ascending')
  })
})
