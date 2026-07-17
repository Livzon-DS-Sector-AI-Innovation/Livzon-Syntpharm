import { test, expect } from '@playwright/test'

test.describe('供应商管理', () => {
  test('供应商列表页面加载', async ({ page }) => {
    const res = await page.goto('/procurement')
    expect(res?.status()).toBe(200)
    await page.waitForLoadState('networkidle')
  })
})