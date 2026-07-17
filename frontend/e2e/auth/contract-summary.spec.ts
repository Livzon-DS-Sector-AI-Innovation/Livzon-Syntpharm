import { test, expect } from '@playwright/test'

test.describe('采购合同汇总', () => {
  test('未登录时重定向到登录页', async ({ page }) => {
    await page.goto('/procurement/contract-summary')
    await page.waitForTimeout(2000)
    await expect(page.locator('h3').filter({ hasText: '工厂管理平台' })).toBeVisible()
  })
})
