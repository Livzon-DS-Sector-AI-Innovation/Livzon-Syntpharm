import { test, expect } from '@playwright/test'

const MODULES = [
  '/production',
  '/quality',
  '/warehouse/raw-material',
  '/warehouse/packaging',
  '/warehouse/product',
  '/equipment',
  '/energy/devices',
  '/safety',
  '/hr',
  '/procurement',
  '/registration',
  '/settings',
]

test.describe('路由冒烟测试', () => {
  for (const path of MODULES) {
    test(`${path} 页面加载`, async ({ page }) => {
      const response = await page.goto(path)
      expect(response?.status()).toBe(200)
      await expect(page).not.toHaveTitle(/404/)
      await expect(page).not.toHaveTitle(/500/)
    })
  }
})
