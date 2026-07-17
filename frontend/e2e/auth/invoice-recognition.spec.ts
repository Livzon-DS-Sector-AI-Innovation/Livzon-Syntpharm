import { test, expect } from '@playwright/test'

test.describe('采购发票识别', () => {
  test('未登录访问时重定向到登录页', async ({ page }) => {
    await page.goto('/procurement/invoice-recognition')
    await page.waitForTimeout(2000)
    await expect(page).toHaveURL(/\/login/)
  })
})
