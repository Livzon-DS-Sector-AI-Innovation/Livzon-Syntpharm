import { test, expect } from '@playwright/test'

test.describe('批次管理', () => {
  test('生产管理页面加载', async ({ page }) => {
    const res = await page.goto('/production')
    expect(res?.status()).toBe(200)
    await page.waitForLoadState('networkidle')
  })
})