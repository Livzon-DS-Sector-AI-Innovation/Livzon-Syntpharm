import { test, expect, Locator, Page } from '@playwright/test'

type RouteKind = 'normal' | 'redirect' | 'external-iframe'

type RouteCase = {
  path: string
  module: string
  kind: RouteKind
  expectedPath?: string
  expected: (page: Page) => Locator
  /**
   * 跳过内容断言，只校验跳转目标。
   *
   * 用于「跳转目标页在同一份清单里已单独断言过」的场景：服务端 `redirect()` 触发的是
   * 客户端 RSC 导航，目标页内容偶尔赶不上 15s 断言窗口，重复断言只会制造 flaky。
   */
  skipContentCheck?: boolean
  heading?: string
  /**
   * Text of the page's top-level heading, when it has one worth pinning.
   *
   * `expected` uses `getByRole('heading')`, which matches **any** level — so it
   * cannot tell an `h1` from an `h2`. This asserts `level: 1` specifically, which
   * is what stops a page quietly regressing to no top-level heading (#102).
   */
  topLevelHeading?: string
  /**
   * 数据断言：打开页面后必须出现数据元素或空态文案之一。
   *
   * 用于「页面打开了但列表永远空白」这类回归（#169）：迁移前这些页面只在事件回调里取数，
   * 打开后一个请求都不发，表格照样渲染成一张空表 —— 只断言 heading 完全发现不了。
   */
  expectData?: {
    /** 有数据时必然出现的元素（表格行 / 列表项） */
    rows: (page: Page) => Locator
    /**
     * 没有数据时的空态：正则匹配文案，或直接给定位器。
     *
     * 用定位器的场景：antd 表格各页空态文案是自定义的（「暂无数据」「暂无注册项目」
     * 「暂无校准记录」…），枚举不完，改由 `antdEmpty` 按结构判定。
     */
    empty: RegExp | ((page: Page) => Locator)
  }
  /**
   * 打开页面必须真实发出取数请求。
   *
   * `'server-action'` 表示取数走 Server Action（浏览器侧表现为对当前路由的 POST），
   * 字符串表示客户端 fetch 的 URL 片段。DOM 断言无法区分「取数返回空」与「根本没取数」，
   * 这一项补上那个缺口。
   */
  expectFetch?: 'server-action' | string
}

const escapeRegex = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

/** 被测前端源：与 playwright.config.ts 的 baseURL 同源，本地跑 dev 栈时用 E2E_FRONTEND_URL 覆盖 */
const APP_ORIGIN = (process.env.E2E_FRONTEND_URL ?? 'http://127.0.0.1:13000').replace(/\/+$/, '')

/**
 * 取数断言的等待预算。
 *
 * CI runner 上 Next 生产构建 + 后端 + PostgreSQL 同机，一次 Server Action 取数实测
 * 25~60s（/quality/fqc 30.6s、/quality/instrument/records 57.4s），所以不能按本地
 * 毫秒级速度定预算。但也不能无上限：失败路由实测是「等满仍无行无空态」，
 * 给到 90s 只是把 CI 从 15 分钟拖到 35 分钟而不改变结论。
 * 45s 覆盖了正常慢请求，同时让失败快速暴露。需要更严/更松时用 E2E_DATA_TIMEOUT_MS 覆盖。
 */
const DATA_TIMEOUT_MS = Number(process.env.E2E_DATA_TIMEOUT_MS ?? 45_000)

function summarizeErrors(errors: string[], label: string): string {
  if (errors.length <= 3) return errors.join('\n')
  // Group by URL prefix (domain + first 2 path segments + method + status)
  const groups = new Map<string, string[]>()
  for (const e of errors) {
    const m = e.match(/\[(\d+)\] (\w+) (.+)$/)
    const key = m ? `[${m[1]}] ${m[2]} ${m[3].replace(/^(https?:\/\/[^/]+)(\/[^/]+\/[^/]+).*/, '$1$2/*')}` : e
    const list = groups.get(key) ?? []
    list.push(e)
    groups.set(key, list)
  }
  const lines: string[] = []
  for (const [key, group] of groups) {
    lines.push(group.length === 1 ? group[0]! : `${group.length} × ${key}`)
  }
  return `${errors.length} ${label} errors:\n${lines.join('\n')}`
}

/**
 * Console errors that are known noise and would otherwise fail every sweep.
 * Keep this list short and justified — everything else is a real finding.
 */
const IGNORED_CONSOLE_ERRORS = [
  // React DevTools advertises itself on dev builds; harmless.
  'Download the React DevTools',
]

async function checkRoute(page: Page, route: RouteCase) {
  const httpErrors: string[] = []
  const networkFailures: string[] = []
  const consoleErrors: string[] = []
  const seenRequests: { method: string; url: string }[] = []

  const isApplicationUrl = (url: string) =>
    (url.startsWith(APP_ORIGIN) ||
    url.includes('/api/')) &&
    !url.includes('?_rsc=') // exclude Next.js RSC prefetch requests that are legitimately aborted on navigation

  const onResponse = (response: { url(): string; status(): number; request(): { method(): string; url(): string } }) => {
    if (isApplicationUrl(response.url()) && response.status() >= 400) {
      const req = response.request()
      httpErrors.push(`[${response.status()}] ${req.method()} ${req.url()}`)
    }
  }

  const onRequestFailed = (request: { failure(): { errorText: string } | null; url(): string }) => {
    // net::ERR_ABORTED occurs when navigating away — pending requests from the
    // previous route are legitimately cancelled. Only flag real failures.
    const errorText = request.failure()?.errorText ?? ''
    if (isApplicationUrl(request.url()) && errorText !== 'net::ERR_ABORTED') {
      networkFailures.push(
        `${request.method()} ${request.url()}: ${errorText}`,
      )
    }
  }

  // Console errors are invisible to the status/DOM assertions below, and every
  // bug reported against these pages so far arrived as one: a styled-jsx hydration
  // mismatch, an antd deprecation, and antd's useForm "not connected" warning.
  // A page can render perfectly and still log an error, so nothing else catches it.
  const onConsole = (msg: { type(): string; text(): string }) => {
    if (msg.type() !== 'error') return
    const text = msg.text()
    if (IGNORED_CONSOLE_ERRORS.some((ignored) => text.includes(ignored))) return
    consoleErrors.push(text.split('\n')[0] ?? text)
  }

  // 记录应用内请求，供 expectFetch 判断「页面到底有没有取数」
  const onRequest = (request: { method(): string; url(): string }) => {
    if (isApplicationUrl(request.url())) {
      seenRequests.push({ method: request.method(), url: request.url() })
    }
  }

  page.on('response', onResponse)
  page.on('requestfailed', onRequestFailed)
  page.on('console', onConsole)
  page.on('request', onRequest)

  try {
    const response = await page.goto(route.path, {
      waitUntil: 'domcontentloaded',
      timeout: 30_000,
    })

    // Clear any errors from late responses of the previous page
    httpErrors.length = 0
    networkFailures.length = 0
    consoleErrors.length = 0

    if (route.kind === 'redirect') {
      expect(response).not.toBeNull()
      expect(response!.status()).toBeLessThan(400)
      const dest = route.expectedPath!
      await expect(page).toHaveURL(
        new RegExp(`${escapeRegex(dest)}(?:\\?.*)?$`),
        { timeout: 10_000 },
      )
      if (!route.skipContentCheck) {
        await expect(route.expected(page)).toBeVisible({ timeout: 15_000 })
      }
    } else if (route.kind === 'external-iframe') {
      expect(response).not.toBeNull()
      expect(response!.status()).toBeLessThan(400)
      await expect(route.expected(page)).toBeVisible({ timeout: 10_000 })
      if (route.heading) {
        await expect(page.getByRole('heading', { name: route.heading }).first()).toBeVisible({ timeout: 10_000 })
      }
    } else {
      expect(response).not.toBeNull()
      expect(response!.status()).toBeLessThan(400)
      await expect(route.expected(page)).toBeVisible({ timeout: 10_000 })
    }

    if (route.topLevelHeading) {
      await expect(
        page.getByRole('heading', { level: 1, name: route.topLevelHeading }).first(),
        `${route.path} has no level-1 heading`,
      ).toBeVisible({ timeout: 10_000 })
    }

    await expect(page.getByText('页面加载出错')).not.toBeVisible()
    await expect(page.getByText('应用加载出错')).not.toBeVisible()

    // 数据断言：有行，或者有「没有数据」的空态文案。两者都没有 = 列表压根没渲染出内容。
    if (route.expectData) {
      const { rows, empty } = route.expectData
      // 正则那支要 filter 可见：antd Empty 的图标 `<svg><title>` 也含同一文案，但它按文档顺序在前、
      // 且没有布局盒，isVisible() 恒为 false，`.first()` 会一直等不到可见元素。
      const emptyLocator =
        typeof empty === 'function' ? empty(page) : page.getByText(empty).filter({ visible: true }).first()
      await expect
        .poll(
          async () => (await rows(page).count()) > 0 || (await emptyLocator.isVisible()),
          {
            timeout: DATA_TIMEOUT_MS,
            message: `${route.path} 既没有数据行也没有空态文案：页面可能根本没有发起取数`,
          },
        )
        .toBe(true)
    }

    // 取数断言：DOM 断言分不清「返回空」和「没请求」，这里直接看请求有没有发出去。
    if (route.expectFetch) {
      const spec = route.expectFetch
      await expect
        .poll(
          () =>
            seenRequests.some((request) => {
              if (spec === 'server-action') {
                return (
                  request.method === 'POST' &&
                  new URL(request.url).pathname === (route.expectedPath ?? route.path)
                )
              }
              return request.url.includes(spec)
            }),
          {
            timeout: DATA_TIMEOUT_MS,
            message: `${route.path} 没有发出取数请求（${spec}）：查询可能没有接线`,
          },
        )
        .toBe(true)
    }

    expect(httpErrors.length, summarizeErrors(httpErrors, 'HTTP')).toBe(0)
    expect(networkFailures.length, summarizeErrors(networkFailures, 'network')).toBe(0)
    expect(
      consoleErrors.length,
      `${consoleErrors.length} console error(s) on ${route.path}:\n${consoleErrors.join('\n')}`,
    ).toBe(0)
  } finally {
    page.off('response', onResponse)
    page.off('requestfailed', onRequestFailed)
    page.off('console', onConsole)
    page.off('request', onRequest)
  }
}

const heading =
  (name: string) =>
  (page: Page): Locator =>
    page.getByRole('heading', { name }).first()

const text = (t: string) => (page: Page): Locator => page.getByText(t).first()

/** antd 表格的数据行（空表时只剩 `.ant-table-placeholder`，匹配不到） */
const antdRows = (page: Page): Locator => page.locator('.ant-table-tbody tr.ant-table-row')

/**
 * antd 表格的空表占位。
 *
 * 按结构判定而不是按文案：各页空态写法不统一——`<Empty description="暂无注册项目" />`、
 * `<Empty description="暂无校准记录" />`、`locale={{ emptyText: '暂无查重问题' }}`（纯字符串，不生成
 * `.ant-empty-description`），文案枚举不完。
 *
 * 唯一要排除的是取数失败的降级态：表格里嵌的是 `DataUnavailable compact`，它是一段普通 div
 * （没有 `.ant-result`），只能按文案「数据暂时不可用」识别（见 components/common/DataUnavailable.tsx）。
 */
const antdEmpty = (page: Page): Locator =>
  page.locator('.ant-table-placeholder').filter({ hasNotText: '数据暂时不可用' })

/** antd 表格「打开即取数」的断言包：有行，或表格渲染出了空态 */
const antdTableData = { rows: antdRows, empty: antdEmpty } as const


// ═══════════════════════════════════════════════════════════════
// Route definitions
// ═══════════════════════════════════════════════════════════════

const productionRoutes: RouteCase[] = [
  { path: '/production', module: 'production', kind: 'normal', expected: heading('生产管理概览') },
  { path: '/production/batches', module: 'production', kind: 'normal', expected: text('批次管理') },
  { path: '/production/product-output', module: 'production', kind: 'normal', expected: heading('产品管理') },
  { path: '/production/product-output/all-products', module: 'production', kind: 'normal', expected: heading('全部产品') },
  { path: '/production/label-verification', module: 'production', kind: 'normal', expected: heading('标签复核') },
  { path: '/production/pressure', module: 'production', kind: 'normal', expected: heading('压差统计') },
  { path: '/production/pressure/audit', module: 'production', kind: 'normal', expected: heading('审核管理') },
  { path: '/production/pressure/manual-input', module: 'production', kind: 'normal', expected: heading('手动录入') },
  { path: '/production/pressure/ocr-input', module: 'production', kind: 'normal', expected: heading('OCR 识别录入') },
  { path: '/production/pressure/point-management', module: 'production', kind: 'normal', expected: heading('位点管理') },
  { path: '/production/pressure/records', module: 'production', kind: 'normal', expected: heading('数据记录') },
  // Disabled/unfinished routes — excluded from E2E
  // /production/plan — 生产计划（开发中）
  // /production/process — 工艺规程（开发中）
  // /production/records — 生产记录（开发中）
  // /production/balance — 物料平衡（开发中）
]

const equipmentRoutes: RouteCase[] = [
  { path: '/equipment', module: 'equipment', kind: 'redirect', expectedPath: '/equipment/stats', expected: heading('设备仪表盘') },
  { path: '/equipment/stats', module: 'equipment', kind: 'normal', expected: heading('设备仪表盘') },
  { path: '/equipment/assets', module: 'equipment', kind: 'normal', expected: heading('设备台账') },
  { path: '/equipment/maintenance', module: 'equipment', kind: 'normal', expected: heading('维护保养') },
  { path: '/equipment/inspection', module: 'equipment', kind: 'normal', expected: heading('设备巡检') },
  { path: '/equipment/spare-parts', module: 'equipment', kind: 'normal', expected: heading('备件管理') },
  // Disabled: backend-e2e hostname leaks into browser via RSC, DNS fails (ERR_NAME_NOT_RESOLVED)
  // { path: '/equipment/personnel', module: 'equipment', kind: 'normal', expected: heading('人员配置') },
  // Disabled: backend-e2e hostname leaks into browser via RSC, DNS fails (ERR_NAME_NOT_RESOLVED)
  // { path: '/equipment/settings', module: 'equipment', kind: 'normal', expected: heading('设备管理配置') },
]

const energyRoutes: RouteCase[] = [
  { path: '/energy', module: 'energy', kind: 'normal', expected: heading('能源总览') },
  { path: '/energy/devices', module: 'energy', kind: 'normal', expected: heading('数据源配置') },
  { path: '/energy/alerts', module: 'energy', kind: 'normal', expected: heading('预警管理') },
  { path: '/energy/collect-logs', module: 'energy', kind: 'normal', expected: heading('采集日志') },
  { path: '/energy/settings', module: 'energy', kind: 'normal', expected: heading('能源管理配置') },
]

const administrationRoutes: RouteCase[] = [
  { path: '/administration', module: 'administration', kind: 'normal', expected: heading('行政管理') },
  // Disabled: redirects to /ledger which calls gift-inventories API (returns 404)
  // { path: '/administration/meeting', module: 'administration', kind: 'redirect', expectedPath: '/administration/meeting/ledger', expected: heading('物品台账') },
  // Disabled: backend gift-inventories endpoint not yet implemented (returns 404)
  // { path: '/administration/meeting/ledger', module: 'administration', kind: 'normal', expected: heading('物品台账') },
  // Disabled: calls /api/v1/administration/gift-inventories (returns 404)
  // { path: '/administration/meeting/requests', module: 'administration', kind: 'normal', expected: heading('领用记录') },
  // Disabled: calls /api/v1/administration/gift-requisitions (returns 404)
  // { path: '/administration/meeting/requisitions', module: 'administration', kind: 'normal', expected: heading('领用记录') },
  { path: '/administration/approval', module: 'administration', kind: 'normal', expected: heading('文件审批') },
  { path: '/administration/it-tickets', module: 'administration', kind: 'external-iframe', expected: text('报修温馨提示'), heading: 'IT工单' },
  { path: '/administration/login-logs', module: 'administration', kind: 'normal', expected: heading('登录记录') },
  // Disabled: calls /api/v1/administration/regulations (returns 404)
  // { path: '/administration/notice', module: 'administration', kind: 'normal', expected: heading('公告通知') },
  // Disabled: calls /api/v1/administration/regulations (returns 404)
  // { path: '/administration/vehicle-requests', module: 'administration', kind: 'normal', expected: heading('用车数据') },
  // Disabled: vehicle router not wired into app (returns 404)
  // { path: '/administration/vehicles', module: 'administration', kind: 'normal', expected: heading('车辆信息') },
]

const environmentRoutes: RouteCase[] = [
  { path: '/environment', module: 'environment', kind: 'normal', expected: heading('环保管理') },
]

const warehouseRoutes: RouteCase[] = [
  { path: '/warehouse', module: 'warehouse', kind: 'redirect', expectedPath: '/warehouse/raw-material', expected: heading('成品') },
  { path: '/warehouse/raw-material', module: 'warehouse', kind: 'normal', expected: heading('成品') },
  { path: '/warehouse/product', module: 'warehouse', kind: 'normal', expected: heading('五金') },
  { path: '/warehouse/packaging', module: 'warehouse', kind: 'normal', expected: heading('原辅料及包材') },
  { path: '/warehouse/feishu-config', module: 'warehouse', kind: 'normal', expected: heading('飞书配置') },
]

const settingsRoutes: RouteCase[] = [
  { path: '/settings', module: 'settings', kind: 'normal', expected: heading('系统管理') },
]

const hrRoutes: RouteCase[] = [
  { path: '/hr', module: 'hr', kind: 'normal', expected: heading('人事管理') },
  { path: '/hr/attendance', module: 'hr', kind: 'normal', expected: text('考勤管理') },
  { path: '/hr/departments', module: 'hr', kind: 'normal', expected: heading('部门管理') },
  { path: '/hr/departure', module: 'hr', kind: 'normal', expected: heading('老厂离职台账') },
  { path: '/hr/offboarding', module: 'hr', kind: 'normal', expected: heading('离职管理') },
  { path: '/hr/onboarding', module: 'hr', kind: 'normal', expected: heading('老厂入职台账') },
  { path: '/hr/profile', module: 'hr', kind: 'normal', expected: heading('员工档案') },
  { path: '/hr/recruitment', module: 'hr', kind: 'normal', expected: heading('候选人筛选') },
  { path: '/hr/roster', module: 'hr', kind: 'normal', expected: heading('员工花名册') },
  { path: '/hr/settings', module: 'hr', kind: 'normal', expected: heading('人事管理配置') },
  { path: '/hr/training', module: 'hr', kind: 'normal', expected: heading('培训管理') },
  { path: '/hr/training/ai-exam', module: 'hr', kind: 'normal', expected: heading('AI 出题') },
  { path: '/hr/training/annual-plan', module: 'hr', kind: 'normal', expected: heading('年度培训计划') },
  { path: '/hr/training/evaluation-form', module: 'hr', kind: 'normal', expected: heading('培训效果评估表') },
  { path: '/hr/training/ledger', module: 'hr', kind: 'normal', expected: heading('培训台账') },
  { path: '/hr/training/notification', module: 'hr', kind: 'normal', expected: heading('培训通知') },
  // Disabled: calls /api/v1/hr/sop-catalog (returns 404)
  // { path: '/hr/training/onboarding', module: 'hr', kind: 'normal', expected: heading('入职培训') },
  // Disabled: calls /api/v1/hr/sop-catalog and /api/v1/hr/trainers (returns 404)
  // { path: '/hr/training/records', module: 'hr', kind: 'normal', expected: heading('培训列表') },
  // Disabled: calls /api/v1/hr/trainers (returns 404)
  // { path: '/hr/training/sign-in', module: 'hr', kind: 'normal', expected: heading('培训签到') },
  // Disabled: calls /api/v1/hr/sop-catalog (returns 404)
  // { path: '/hr/training/sop-catalog', module: 'hr', kind: 'normal', expected: heading('SOP 目录') },
  // Disabled: calls /api/v1/hr/sop-catalog (returns 404)
  // { path: '/hr/training/specialists', module: 'hr', kind: 'normal', expected: heading('培训专员管理') },
  // Disabled: calls /api/v1/hr/sop-catalog and /api/v1/hr/trainers (returns 404)
  // { path: '/hr/training/trainers', module: 'hr', kind: 'normal', expected: heading('内训师台账') },
  // Excluded (form/create pages requiring data fixtures):
  // /hr/training/annual-plan/new
  // /hr/training/ledger/new
  // /hr/training/select-tasks
  // /hr/new/* — duplicate aliases
  // /hr/system/settings — duplicate alias
]

const procurementRoutes: RouteCase[] = [
  { path: '/procurement', module: 'procurement', kind: 'normal', expected: heading('采购管理工作台') },
  { path: '/procurement/supplier', module: 'procurement', kind: 'normal', expected: heading('供应商管理') },
  { path: '/procurement/order', module: 'procurement', kind: 'normal', expected: heading('采购订单月度汇总') },
  { path: '/procurement/contract-summary', module: 'procurement', kind: 'normal', expected: heading('合同汇总') },
  { path: '/procurement/invoice-recognition', module: 'procurement', kind: 'normal', expected: heading('发票识别') },
]

const qualityRoutes: RouteCase[] = [
  { path: '/quality', module: 'quality', kind: 'normal', expected: heading('质量管理中心') },
  { path: '/quality/deviation', module: 'quality', kind: 'normal', expected: text('AI智能偏差管理系统') },
  { path: '/quality/deviation/report', module: 'quality', kind: 'normal', expected: text('偏差报告编辑器') },
  // Disabled: /api/v1/quality/deviation-flow endpoint returns 404/500
  // { path: '/quality/deviation-flow/settings', module: 'quality', kind: 'normal', expected: heading('偏差提醒设置') },
  // { path: '/quality/deviation-flow/query', module: 'quality', kind: 'normal', expected: heading('偏差任务查询') },
  // { path: '/quality/deviation-flow/progress', module: 'quality', kind: 'normal', expected: heading('偏差详情') },
  // Disabled: calls /api/v1/quality/deviation-automation/templates (returns 404)
  // { path: '/quality/deviation-automation/templates', module: 'quality', kind: 'normal', expected: text('报告模板管理') },
  // Disabled: calls /api/v1/quality/deviation-automation/templates (returns 404)
  // { path: '/quality/deviation-automation/history', module: 'quality', kind: 'normal', expected: text('历史任务查询') },
  // Disabled: calls /api/v1/quality/deviation-automation/templates (returns 404)
  // { path: '/quality/deviation-automation/sop', module: 'quality', kind: 'normal', expected: text('SOP规则管理') },
  { path: '/quality/calculator', module: 'quality', kind: 'normal', expected: heading('计算器') },
  { path: '/quality/cpv', module: 'quality', kind: 'normal', expected: heading('CPV') },
  // Disabled: endpoint /api/v1/quality/department-contacts not implemented (returns 404)
  // { path: '/quality/department-contacts', module: 'quality', kind: 'normal', expected: heading('部门联系人配置') },
  { path: '/quality/doc-check', module: 'quality', kind: 'normal', expected: heading('审核管理') },
  { path: '/quality/fqc', module: 'quality', kind: 'normal', expected: heading('FQC'), expectData: antdTableData, expectFetch: 'server-action' },
  {
    path: '/quality/inspection',
    module: 'quality',
    kind: 'redirect',
    expectedPath: '/quality/inspection/standards',
    expected: text('检验标准维护'),
    // 目标页内容由下一行单独断言；这里只校验跳转，避免客户端导航下的重复 flaky
    skipContentCheck: true,
  },
  { path: '/quality/inspection/standards', module: 'quality', kind: 'normal', expected: text('检验标准维护') },
  { path: '/quality/inspection-table', module: 'quality', kind: 'normal', expected: text('原料检验数据表') },
  { path: '/quality/instrument', module: 'quality', kind: 'normal', expected: heading('仪器校准管理') },
  { path: '/quality/instrument/list', module: 'quality', kind: 'normal', expected: heading('仪器设备台账') },
  { path: '/quality/instrument/records', module: 'quality', kind: 'normal', expected: heading('校准记录') },
  { path: '/quality/instrument/settings', module: 'quality', kind: 'normal', expected: heading('提醒设置') },
  { path: '/quality/ipqc', module: 'quality', kind: 'normal', expected: heading('IPQC'), expectData: antdTableData, expectFetch: 'server-action' },
  { path: '/quality/iqc', module: 'quality', kind: 'normal', expected: heading('IQC'), expectData: antdTableData, expectFetch: 'server-action' },
  { path: '/quality/material-report', module: 'quality', kind: 'normal', expected: text('原料报告单管理') },
  { path: '/quality/material-report/template', module: 'quality', kind: 'normal', expected: text('Word模板管理') },
  { path: '/quality/reagent', module: 'quality', kind: 'normal', expected: heading('试剂管理') },
  { path: '/quality/reagent/reminder', module: 'quality', kind: 'normal', expected: heading('试剂库存提醒') },
  { path: '/quality/retention', module: 'quality', kind: 'normal', expected: heading('留样管理') },
  { path: '/quality/sampling', module: 'quality', kind: 'normal', expected: heading('取样管理'), expectData: antdTableData, expectFetch: 'server-action' },
  { path: '/quality/sop-ai/records', module: 'quality', kind: 'normal', expected: heading('校验记录台账') },
  { path: '/quality/stability', module: 'quality', kind: 'normal', expected: heading('稳定性'), expectData: antdTableData, expectFetch: 'server-action' },
  { path: '/quality/stability/plan', module: 'quality', kind: 'normal', expected: heading('稳定性实验管理 - 方案录入') },
  { path: '/quality/stability/result', module: 'quality', kind: 'normal', expected: heading('稳定性实验管理 - 检测结果') },
  { path: '/quality/static-data', module: 'quality', kind: 'normal', expected: heading('业务静态数据'), topLevelHeading: '业务静态数据' },
  // Removed: the page was deleted (commit d1a9d2db) — it called
  // /api/v1/quality/static-data/audit{,/modules}, which the backend never implemented,
  // so it returned 500 on every load.
  // { path: '/quality/static-data/audit', module: 'quality', kind: 'normal', expected: text('变更审计日志') },
  // Disabled: endpoint /api/v1/ai/config not implemented (returns 404)
  // { path: '/quality/ai-config', module: 'quality', kind: 'normal', expected: text('AI 配置设置') },
  { path: '/quality/ai-log', module: 'quality', kind: 'normal', expected: heading('AI交互日志') },
  // Excluded (form/create pages):
  // /quality/deviation-automation/create
  // /quality/deviation-flow/create
  // /quality/material-report/create
  // /quality/doc-check/new
  // /quality/instrument/list/create
  // /quality/instrument/list/edit
  // /quality/sop-ai/batch
  // /quality/sop-ai/preview
]

const registrationRoutes: RouteCase[] = [
  { path: '/registration', module: 'registration', kind: 'normal', expected: heading('注册管理') },
  {
    path: '/registration/ledger',
    module: 'registration',
    kind: 'normal',
    expected: heading('注册台账'),
    expectData: antdTableData,
    expectFetch: '/api/v1/registration/ledger',
  },
  {
    path: '/registration/projects',
    module: 'registration',
    kind: 'normal',
    expected: heading('项目管理'),
    expectData: antdTableData,
    // 取数走 Server Action（集合端点尾斜杠会被 Next 归一化，浏览器直连不通）
    expectFetch: 'server-action',
  },
  { path: '/registration/regulation', module: 'registration', kind: 'normal', expected: heading('法规看板') },
  {
    path: '/registration/regulation/list',
    module: 'registration',
    kind: 'normal',
    expected: heading('法规工作台'),
    // 法规列表不是 antd Table，是自绘列表：每行都有「查看详情」，空态文案按分类不同
    expectData: { rows: (page) => page.getByText('查看详情'), empty: /暂无法规数据/ },
    expectFetch: '/api/v1/registration/regulatory-documents',
  },
  {
    path: '/registration/authorization-letter',
    module: 'registration',
    kind: 'normal',
    expected: heading('授权书'),
    // 首屏首页由服务端直出，浏览器侧不另发请求；翻页才会取数
    expectData: antdTableData,
  },
  { path: '/registration/dossier-writer', module: 'registration', kind: 'normal', expected: heading('申报资料撰写') },
  {
    path: '/registration/reference-standard',
    module: 'registration',
    kind: 'normal',
    expected: heading('对照物质说明表管理'),
    // 首屏首页由服务端直出，浏览器侧不另发请求；翻页才会取数
    expectData: antdTableData,
  },
  { path: '/registration/review', module: 'registration', kind: 'normal', expected: heading('申报进度查询') },
  {
    path: '/registration/supplementary-reply',
    module: 'registration',
    kind: 'normal',
    expected: heading('发补回复'),
    // 首屏首页由服务端直出，浏览器侧不另发请求；翻页才会取数
    expectData: antdTableData,
  },
  { path: '/registration/validation-audit', module: 'registration', kind: 'normal', expected: heading('验证文件审核') },
  // Excluded: /registration/validation-audit/new — form page
]

const researchRoutes: RouteCase[] = [
  { path: '/research', module: 'research', kind: 'normal', expected: heading('研发管理') },
  { path: '/research/projects', module: 'research', kind: 'normal', expected: heading('研发项目') },
  { path: '/research/initiations', module: 'research', kind: 'normal', expected: heading('立项管理') },
  { path: '/research/research-tracks', module: 'research', kind: 'normal', expected: heading('研究项管理') },
  { path: '/research/reports', module: 'research', kind: 'normal', expected: heading('研发报告') },
  { path: '/research/deliverable-templates', module: 'research', kind: 'normal', expected: heading('交付物模板管理') },
  { path: '/research/process-optimization', module: 'research', kind: 'normal', expected: heading('工艺优化') },
  { path: '/research/process-validation', module: 'research', kind: 'normal', expected: heading('工艺验证') },
  { path: '/research/route-development', module: 'research', kind: 'normal', expected: heading('打通路线') },
  { path: '/research/registration-filing', module: 'research', kind: 'normal', expected: heading('申报资料') },
  { path: '/research/bayesian', module: 'research', kind: 'normal', expected: heading('EDBO+ 贝叶斯优化') },
  { path: '/research/ich-analysis', module: 'research', kind: 'normal', expected: heading('ICH Q3C/Q3D 杂质识别') },
  { path: '/research/pilot-workflow', module: 'research', kind: 'normal', expected: heading('中试研究') },
]

const safetyRoutes: RouteCase[] = [
  { path: '/safety', module: 'safety', kind: 'normal', expected: heading('安全管理总览') },
  { path: '/safety/hazard', module: 'safety', kind: 'normal', expected: heading('隐患登记') },
  { path: '/safety/hazard-identification', module: 'safety', kind: 'normal', expected: heading('危险源辨识工作流') },
  { path: '/safety/hazard-identification/ledger', module: 'safety', kind: 'normal', expected: heading('危险源辨识台账') },
  { path: '/safety/hazard-ledger', module: 'safety', kind: 'normal', expected: heading('隐患台账') },
  { path: '/safety/accident', module: 'safety', kind: 'normal', expected: text('事故管理') },
  { path: '/safety/check', module: 'safety', kind: 'normal', expected: text('安全检查') },
  { path: '/safety/contractor', module: 'safety', kind: 'normal', expected: text('承包商管理') },
  { path: '/safety/ehs-change', module: 'safety', kind: 'normal', expected: heading('变更管理'), topLevelHeading: 'EHS变更管理' },
  { path: '/safety/knowledge-base', module: 'safety', kind: 'normal', expected: heading('文档处理中枢') },
  { path: '/safety/knowledge-base/graph', module: 'safety', kind: 'normal', expected: heading('知识图谱') },
  { path: '/safety/occupational-health', module: 'safety', kind: 'normal', expected: heading('职业健康') },
  { path: '/safety/regulation', module: 'safety', kind: 'normal', expected: heading('安全操规管理'), topLevelHeading: '安全操规管理' },
  { path: '/safety/regulation/generator', module: 'safety', kind: 'normal', expected: heading('操规标准化生成') },
  { path: '/safety/risk-reporting', module: 'safety', kind: 'normal', expected: heading('关键风险作业报备'), topLevelHeading: '关键风险作业报备' },
  { path: '/safety/settings', module: 'safety', kind: 'normal', expected: heading('安全管理配置') },
  { path: '/safety/special-ops', module: 'safety', kind: 'normal', expected: heading('特殊作业') },
  { path: '/safety/special-ops/personnel', module: 'safety', kind: 'normal', expected: heading('作业人员') },
  { path: '/safety/training', module: 'safety', kind: 'normal', expected: heading('安全培训') },
  // Excluded: /safety/hazard-identification/new — form page
]

const allModuleRouteSets: { name: string; routes: RouteCase[] }[] = [
  { name: 'production', routes: productionRoutes },
  { name: 'equipment', routes: equipmentRoutes },
  { name: 'energy', routes: energyRoutes },
  { name: 'administration', routes: administrationRoutes },
  { name: 'environment', routes: environmentRoutes },
  { name: 'warehouse', routes: warehouseRoutes },
  { name: 'settings', routes: settingsRoutes },
  { name: 'hr', routes: hrRoutes },
  { name: 'procurement', routes: procurementRoutes },
  { name: 'quality', routes: qualityRoutes },
  { name: 'registration', routes: registrationRoutes },
  { name: 'research', routes: researchRoutes },
  { name: 'safety', routes: safetyRoutes },
]

// ═══════════════════════════════════════════════════════════════
// Tests
// ═══════════════════════════════════════════════════════════════

test('root redirects to /home', async ({ page }) => {
  // 登录后统一落地首页工作台（原先是生产管理页）
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expect(page).toHaveURL(/\/home(?:\?.*)?$/)
})

test('regulation detail renders after opening from the list (#169)', async ({ page }) => {
  await page.goto('/registration/regulation/list', { waitUntil: 'domcontentloaded' })

  const rowLinks = page.getByText('查看详情')
  const emptyState = page.getByText(/暂无法规数据/).first()

  // 先等列表取数结束：有行，或明确的空态（不是「既没行也没空态」的假空表）
  await expect
    .poll(
      async () => (await rowLinks.count()) > 0 || (await emptyState.isVisible()),
      { timeout: 15_000, message: '法规列表既没有数据行也没有空态文案：列表可能没有发起取数' },
    )
    .toBe(true)

  test.skip((await rowLinks.count()) === 0, '法规列表为空，无法从列表进入详情页')

  // 列表行是 onClick 触发的客户端跳转，水合完成前点击无效：用轮询重试吞掉这段窗口期
  await expect(async () => {
    await rowLinks.first().click()
    await expect(page).toHaveURL(/\/registration\/regulation\/[^/]+$/, { timeout: 5_000 })
  }).toPass({ timeout: 30_000 })

  // 详情加载完成：Spin 消失、标题可见；失败会渲染降级区块，不应被当成加载成功
  await expect(page.locator('.ant-spin-spinning')).toHaveCount(0, { timeout: 15_000 })
  await expect(page.getByText('数据暂时不可用')).toHaveCount(0)
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible({ timeout: 15_000 })
})

for (const { name, routes } of allModuleRouteSets) {
  test(`${name} routes load`, async ({ page }) => {
    // 60s base + 15s/路由，再留一个 DATA_TIMEOUT_MS 的余量：慢环境下单个页面可能把取数预算用满
    test.setTimeout(Math.max(60_000, routes.length * 15_000) + DATA_TIMEOUT_MS)
    const failures: { path: string; error: string }[] = []

    for (const route of routes) {
      await test.step(route.path, async () => {
        try {
          await checkRoute(page, route)
        } catch (error) {
          failures.push({
            path: route.path,
            error: error instanceof Error ? error.message : String(error),
          })
        }
      })
    }

    expect(
      failures.length,
      `${name} route failures:\n${failures.map(f => `  ${f.path}: ${f.error}`).join('\n')}`,
    ).toBe(0)
  })
}
