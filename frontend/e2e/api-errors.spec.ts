import { test, expect } from '@playwright/test'

const PAGES = [
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
  '/environment',
]

test.describe('API 错误监控', () => {
  test('所有页面无意外 API 500 错误', async ({ page }) => {
    test.setTimeout(120000)
    const errors: string[] = []

    page.on('response', (response) => {
      const url = response.url()
      const status = response.status()
      if (!url.includes('/api/')) return
      if (status < 400) return
      // Skip expected: 401 (unauth), 403 (no permission), 404 (missing resource)
      if ([401, 403, 404].includes(status)) return
      errors.push(`[${status}] ${url}`)
    })

    for (const path of PAGES) {
      await page.goto(path, { timeout: 30000, waitUntil: 'domcontentloaded' })
      await page.waitForTimeout(1000)
    }

    expect(errors, `Unexpected API 500 errors across all pages:\n${errors.join('\n')}`).toEqual([])
  })
})