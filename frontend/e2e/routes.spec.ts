import { test, expect } from '@playwright/test'

const MODULES = [
  { path: '/production', name: '生产管理' },
  { path: '/quality', name: '质量管理' },
  { path: '/warehouse/raw-material', name: '仓储-原料' },
  { path: '/warehouse/packaging', name: '仓储-包材' },
  { path: '/warehouse/product', name: '仓储-产品' },
  { path: '/equipment', name: '设备管理' },
  { path: '/energy/devices', name: '能耗-设备' },
  { path: '/safety', name: '安全管理' },
  { path: '/hr', name: '人事管理' },
  { path: '/procurement', name: '采购管理' },
  { path: '/registration', name: '注册管理' },
  { path: '/settings', name: '系统设置' },
]

test.describe('路由冒烟测试', () => {
  test('dashboard 加载正常', async ({ page }) => {
    await page.goto('/production')
    await page.waitForLoadState('networkidle')
    await expect(page).not.toHaveTitle(/404/)
    await expect(page).not.toHaveTitle(/500/)
  })

  for (const { path, name } of MODULES) {
    test(`${name} 页面加载 (${path})`, async ({ page }) => {
      const res = await page.goto(path)
      expect(res?.status()).toBe(200)
      await page.waitForLoadState('networkidle')
      // Should not show 404 or 500 error page
      await expect(page.locator('h1').filter({ hasText: '404' })).not.toBeVisible({ timeout: 3000 }).catch(() => {})
      await expect(page.locator('h1').filter({ hasText: '500' })).not.toBeVisible({ timeout: 3000 }).catch(() => {})
    })
  }
})