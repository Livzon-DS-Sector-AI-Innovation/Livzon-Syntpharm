import { test, expect } from '@playwright/test'

test.describe('行政首页', () => {
  test('未登录时重定向到登录页', async ({ page }) => {
    await page.goto('/administration')
    await page.waitForTimeout(2000)
    await expect(page.locator('h3').filter({ hasText: '工厂管理平台' })).toBeVisible()
  })
})