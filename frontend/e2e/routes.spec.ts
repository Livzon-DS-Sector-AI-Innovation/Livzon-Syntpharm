import { test, expect, Page } from '@playwright/test'

const MODULES: { path: string; expected: (page: Page) => ReturnType<Page['getByRole']> }[] = [
  { path: '/production', expected: (page) => page.getByRole('heading', { name: '生产管理' }) },
  { path: '/quality', expected: (page) => page.getByRole('heading', { name: '质量管理' }) },
  { path: '/equipment', expected: (page) => page.getByRole('heading', { name: '设备管理' }) },
  { path: '/energy/devices', expected: (page) => page.locator('h1, h2, h3, h4').first() },
  { path: '/safety', expected: (page) => page.getByRole('heading', { name: '安全管理' }) },
  { path: '/hr', expected: (page) => page.getByRole('heading', { name: '人事管理' }) },
  { path: '/procurement', expected: (page) => page.getByRole('heading', { name: '采购管理' }) },
  { path: '/registration', expected: (page) => page.getByRole('heading', { name: '注册管理' }) },
  { path: '/settings', expected: (page) => page.getByRole('heading', { name: '系统设置' }) },
]

test.describe('路由冒烟测试', () => {
  for (const { path, expected } of MODULES) {
    test(`${path} 页面加载`, async ({ page }) => {
      const httpErrors: string[] = []
      const failedRequests: string[] = []

      page.on('response', (response) => {
        if (response.url().includes('/api/') && response.status() >= 400) {
          httpErrors.push(
            `[${response.status()}] ${response.request().method()} ${response.url()}`,
          )
        }
      })

      page.on('requestfailed', (request) => {
        const url = request.url()
        if (url.includes('/api/')) {
          failedRequests.push(
            `${request.method()} ${url}: ${request.failure()?.errorText ?? 'unknown error'}`,
          )
        }
      })

      const response = await page.goto(path)
      expect(response?.status()).toBe(200)

      await expect(expected(page).first()).toBeVisible()

      await expect(page.getByText('页面加载出错')).not.toBeVisible()
      await expect(page.getByText('应用加载出错')).not.toBeVisible()

      expect(httpErrors, `Unexpected API errors on ${path}:\n${httpErrors.join('\n')}`).toEqual([])
      expect(failedRequests, `Failed requests on ${path}:\n${failedRequests.join('\n')}`).toEqual([])
    })
  }
})
