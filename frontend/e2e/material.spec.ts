import { test, expect } from '@playwright/test'

test.describe('物料管理', () => {
  test('原料仓储页面加载', async ({ page }) => {
    const res = await page.goto('/warehouse/raw-material')
    expect(res?.status()).toBe(200)
    await page.waitForLoadState('networkidle')
  })

  test('包材仓储页面加载', async ({ page }) => {
    const res = await page.goto('/warehouse/packaging')
    expect(res?.status()).toBe(200)
    await page.waitForLoadState('networkidle')
  })
})