import { test, expect } from '@playwright/test'

test.describe('培训管理', () => {
  test('未登录时显示登录页', async ({ page }) => {
    await page.goto('/hr/training')
    await page.waitForTimeout(2000)
    await expect(page.locator('h3').filter({ hasText: '工厂管理平台' })).toBeVisible()
  })
})
