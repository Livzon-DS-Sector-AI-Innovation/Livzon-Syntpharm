import { test, expect } from '@playwright/test'

const PROTECTED_ROUTES = [
  { path: '/production', name: '生产管理' },
  { path: '/equipment/stats', name: '设备仪表盘' },
  { path: '/energy', name: '能源总览' },
  { path: '/administration', name: '行政管理' },
  { path: '/environment', name: '环保管理' },
  { path: '/warehouse', name: '库房管理' },
  { path: '/settings', name: '后台管理' },
  { path: '/hr', name: '人力资源' },
  { path: '/procurement', name: '采购管理' },
  { path: '/quality', name: '质量管理' },
  { path: '/registration', name: '注册申报' },
  { path: '/research', name: '研发管理' },
  { path: '/safety', name: '安全生产' },
]

for (const { path, name } of PROTECTED_ROUTES) {
  test(`${name} 未登录时重定向到登录页 (${path})`, async ({ page }) => {
    await page.goto(path)
    await expect(page).toHaveURL(/\/login/)
    await expect(
      page.getByRole('heading', { name: '工厂管理平台' }),
    ).toBeVisible()
  })
}
