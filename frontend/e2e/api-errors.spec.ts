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
      errors.push(`[${status}] ${response.request().method()} ${url}`)
    })

    for (const path of PAGES) {
      await page.goto(path, { timeout: 60000, waitUntil: 'domcontentloaded' })
    }

    expect(errors, `Unexpected API errors across all pages:\n${errors.join('\n')}`).toEqual([])
  })
})
