import { test, expect } from '@playwright/test'

const PROTECTED_ROUTES = [
  { path: '/administration', name: '行政管理' },
  { path: '/procurement/contract-summary', name: '采购合同汇总' },
  { path: '/hr', name: '人事管理' },
  { path: '/procurement/invoice-recognition', name: '采购发票识别' },
  { path: '/hr/training', name: '培训管理' },
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
