import { test, expect, Locator, Page } from '@playwright/test'

type RouteKind = 'normal' | 'redirect' | 'external-iframe'

type RouteCase = {
  path: string
  module: string
  kind: RouteKind
  expectedPath?: string
  expected: (page: Page) => Locator
  heading?: string
}

const escapeRegex = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

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

async function checkRoute(page: Page, route: RouteCase) {
  const httpErrors: string[] = []
  const networkFailures: string[] = []

  const isApplicationUrl = (url: string) =>
    (url.startsWith('http://127.0.0.1:13000') ||
    url.includes('/api/')) &&
    !url.includes('?_rsc=') // exclude Next.js RSC prefetch requests that are legitimately aborted on navigation

  const onResponse = (response: any) => {
    if (isApplicationUrl(response.url()) && response.status() >= 400) {
      const req = response.request()
      httpErrors.push(`[${response.status()}] ${req.method()} ${req.url()}`)
    }
  }

  const onRequestFailed = (request: any) => {
    // net::ERR_ABORTED occurs when navigating away — pending requests from the
    // previous route are legitimately cancelled. Only flag real failures.
    const errorText = request.failure()?.errorText ?? ''
    if (isApplicationUrl(request.url()) && errorText !== 'net::ERR_ABORTED') {
      networkFailures.push(
        `${request.method()} ${request.url()}: ${errorText}`,
      )
    }
  }

  page.on('response', onResponse)
  page.on('requestfailed', onRequestFailed)

  try {
    const response = await page.goto(route.path, {
      waitUntil: 'domcontentloaded',
      timeout: 30_000,
    })

    if (route.kind === 'redirect') {
      expect(response).not.toBeNull()
      expect(response!.status()).toBeLessThan(400)
      const dest = route.expectedPath!
      await expect(page).toHaveURL(
        new RegExp(`${escapeRegex(dest)}(?:\\?.*)?$`),
        { timeout: 10_000 },
      )
      await expect(route.expected(page)).toBeVisible({ timeout: 15_000 })
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

    await expect(page.getByText('页面加载出错')).not.toBeVisible()
    await expect(page.getByText('应用加载出错')).not.toBeVisible()

    expect(httpErrors.length, summarizeErrors(httpErrors, 'HTTP')).toBe(0)
    expect(networkFailures.length, summarizeErrors(networkFailures, 'network')).toBe(0)
  } finally {
    page.off('response', onResponse)
    page.off('requestfailed', onRequestFailed)
  }
}

const heading =
  (name: string) =>
  (page: Page): Locator =>
    page.getByRole('heading', { name }).first()

const text = (t: string) => (page: Page): Locator => page.getByText(t).first()

const iframe = (title: string) => (page: Page): Locator =>
  page.locator(`iframe[title="${title}"]`)

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
  { path: '/equipment/personnel', module: 'equipment', kind: 'normal', expected: heading('人员配置') },
  { path: '/equipment/settings', module: 'equipment', kind: 'normal', expected: heading('设备管理配置') },
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
  { path: '/administration/meeting', module: 'administration', kind: 'redirect', expectedPath: '/administration/meeting/ledger', expected: heading('物品台账') },
  // Disabled: backend gift-inventories endpoint not yet implemented (returns 404)
  // { path: '/administration/meeting/ledger', module: 'administration', kind: 'normal', expected: heading('物品台账') },
  // Disabled: calls /api/v1/administration/gift-inventories (returns 404)
  // { path: '/administration/meeting/requests', module: 'administration', kind: 'normal', expected: heading('领用记录') },
  { path: '/administration/meeting/requisitions', module: 'administration', kind: 'normal', expected: heading('领用记录') },
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
  { path: '/settings', module: 'settings', kind: 'normal', expected: heading('系统设置') },
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
  { path: '/hr/training/onboarding', module: 'hr', kind: 'normal', expected: heading('入职培训') },
  // Disabled: calls /api/v1/hr/sop-catalog and /api/v1/hr/trainers (returns 404)
  // { path: '/hr/training/records', module: 'hr', kind: 'normal', expected: heading('培训列表') },
  { path: '/hr/training/sign-in', module: 'hr', kind: 'normal', expected: heading('培训签到') },
  // Disabled: calls /api/v1/hr/sop-catalog (returns 404)
  // { path: '/hr/training/sop-catalog', module: 'hr', kind: 'normal', expected: heading('SOP 目录') },
  // Disabled: calls /api/v1/hr/sop-catalog (returns 404)
  // { path: '/hr/training/specialists', module: 'hr', kind: 'normal', expected: heading('培训专员管理') },
  { path: '/hr/training/trainers', module: 'hr', kind: 'normal', expected: heading('内训师台账') },
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
  { path: '/quality/deviation-flow/settings', module: 'quality', kind: 'normal', expected: heading('偏差提醒设置') },
  { path: '/quality/deviation-flow/query', module: 'quality', kind: 'normal', expected: heading('偏差任务查询') },
  { path: '/quality/deviation-flow/progress', module: 'quality', kind: 'normal', expected: heading('偏差详情') },
  { path: '/quality/deviation-automation/templates', module: 'quality', kind: 'normal', expected: text('报告模板管理') },
  // Disabled: calls /api/v1/quality/deviation-automation/templates (returns 404)
  // { path: '/quality/deviation-automation/history', module: 'quality', kind: 'normal', expected: text('历史任务查询') },
  { path: '/quality/deviation-automation/sop', module: 'quality', kind: 'normal', expected: text('SOP规则管理') },
  { path: '/quality/calculator', module: 'quality', kind: 'normal', expected: heading('计算器') },
  { path: '/quality/cpv', module: 'quality', kind: 'normal', expected: heading('CPV') },
  // Disabled: endpoint /api/v1/quality/department-contacts not implemented (returns 404)
  // { path: '/quality/department-contacts', module: 'quality', kind: 'normal', expected: heading('部门联系人配置') },
  { path: '/quality/doc-check', module: 'quality', kind: 'normal', expected: heading('审核管理') },
  { path: '/quality/fqc', module: 'quality', kind: 'normal', expected: heading('FQC') },
  { path: '/quality/inspection', module: 'quality', kind: 'redirect', expectedPath: '/quality/inspection/standards', expected: text('检验标准维护') },
  { path: '/quality/inspection/standards', module: 'quality', kind: 'normal', expected: text('检验标准维护') },
  { path: '/quality/inspection-table', module: 'quality', kind: 'normal', expected: text('原料检验数据表') },
  { path: '/quality/instrument', module: 'quality', kind: 'normal', expected: heading('仪器校准管理') },
  { path: '/quality/instrument/list', module: 'quality', kind: 'normal', expected: heading('仪器设备台账') },
  { path: '/quality/instrument/records', module: 'quality', kind: 'normal', expected: heading('校准记录') },
  { path: '/quality/instrument/settings', module: 'quality', kind: 'normal', expected: heading('提醒设置') },
  { path: '/quality/ipqc', module: 'quality', kind: 'normal', expected: heading('IPQC') },
  { path: '/quality/iqc', module: 'quality', kind: 'normal', expected: heading('IQC') },
  { path: '/quality/material-report', module: 'quality', kind: 'normal', expected: text('原料报告单管理') },
  { path: '/quality/material-report/template', module: 'quality', kind: 'normal', expected: text('Word模板管理') },
  { path: '/quality/reagent', module: 'quality', kind: 'normal', expected: heading('试剂管理') },
  { path: '/quality/reagent/reminder', module: 'quality', kind: 'normal', expected: heading('试剂库存提醒') },
  { path: '/quality/retention', module: 'quality', kind: 'normal', expected: heading('留样管理') },
  { path: '/quality/sampling', module: 'quality', kind: 'normal', expected: heading('取样管理') },
  { path: '/quality/sop-ai/records', module: 'quality', kind: 'normal', expected: heading('校验记录台账') },
  { path: '/quality/stability', module: 'quality', kind: 'normal', expected: heading('稳定性') },
  { path: '/quality/stability/plan', module: 'quality', kind: 'normal', expected: heading('稳定性实验管理 - 方案录入') },
  { path: '/quality/stability/result', module: 'quality', kind: 'normal', expected: heading('稳定性实验管理 - 检测结果') },
  { path: '/quality/static-data', module: 'quality', kind: 'normal', expected: heading('业务静态数据') },
  { path: '/quality/static-data/audit', module: 'quality', kind: 'normal', expected: text('变更审计日志') },
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
  { path: '/registration/ledger', module: 'registration', kind: 'normal', expected: heading('注册台账') },
  { path: '/registration/projects', module: 'registration', kind: 'normal', expected: heading('项目管理') },
  { path: '/registration/regulation', module: 'registration', kind: 'normal', expected: heading('法规看板') },
  { path: '/registration/regulation/list', module: 'registration', kind: 'normal', expected: heading('法规工作台') },
  { path: '/registration/authorization-letter', module: 'registration', kind: 'normal', expected: heading('授权书') },
  { path: '/registration/dossier-writer', module: 'registration', kind: 'normal', expected: heading('申报资料撰写') },
  { path: '/registration/reference-standard', module: 'registration', kind: 'normal', expected: heading('对照物质说明表管理') },
  { path: '/registration/review', module: 'registration', kind: 'normal', expected: heading('申报进度查询') },
  { path: '/registration/supplementary-reply', module: 'registration', kind: 'normal', expected: heading('发补回复') },
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
  { path: '/safety/ehs-change', module: 'safety', kind: 'normal', expected: heading('变更管理') },
  { path: '/safety/knowledge-base', module: 'safety', kind: 'normal', expected: heading('文档处理中枢') },
  { path: '/safety/knowledge-base/graph', module: 'safety', kind: 'normal', expected: heading('知识图谱') },
  { path: '/safety/occupational-health', module: 'safety', kind: 'normal', expected: heading('职业健康') },
  { path: '/safety/regulation', module: 'safety', kind: 'normal', expected: heading('安全操规管理') },
  { path: '/safety/regulation/generator', module: 'safety', kind: 'normal', expected: heading('操规标准化生成') },
  { path: '/safety/risk-reporting', module: 'safety', kind: 'normal', expected: heading('关键风险作业报备') },
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

test('root redirects to /production', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expect(page).toHaveURL(/\/production(?:\?.*)?$/)
})

for (const { name, routes } of allModuleRouteSets) {
  test(`${name} routes load`, async ({ page }) => {
    test.setTimeout(Math.max(60_000, routes.length * 15_000)) // 60s base + 15s per route
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
