import { test, expect } from '@playwright/test'

const LOGIN_URL = /\/login(?:\?.*)?$/

test.beforeAll(async ({ browser }) => {
  const page = await browser.newPage()
  // Warm up both regular pages and the auth callback route handler
  const urls = ['/login', '/auth/callback',]
  for (const url of urls) {
    for (let i = 0; i < 5; i++) {
      try {
        await page.goto(url, { timeout: 10_000 })
        break
      } catch {
        await new Promise(r => setTimeout(r, 2_000))
      }
    }
  }
  await page.close()
})

async function gotoWithRetry(page: import('@playwright/test').Page, url: string) {
  for (let i = 0; i < 3; i++) {
    try {
      await page.goto(url)
      return
    } catch {
      await new Promise(r => setTimeout(r, 2_000))
    }
  }
  await page.goto(url)
}

test('missing token redirects to /login?error=callback_failed', async ({ page }) => {
  await gotoWithRetry(page, '/auth/callback')
  await expect(page).toHaveURL(/\/login\?error=callback_failed/)
  await expect(page.getByRole('heading', { name: '工厂管理平台' })).toBeVisible()
})

test('empty token redirects to /login?error=callback_failed', async ({ page }) => {
  await gotoWithRetry(page, '/auth/callback?token=')
  await expect(page).toHaveURL(/\/login\?error=callback_failed/)
  await expect(page.getByRole('heading', { name: '工厂管理平台' })).toBeVisible()
})

test('garbage token set as cookie → dashboard rejects → redirects to /login', async ({ page }) => {
  await page.context().addCookies([
    { name: 'auth_token', value: 'not-a-valid-jwt', path: '/', domain: '127.0.0.1' },
  ])
  await page.goto('/production')
  await expect(page).toHaveURL(LOGIN_URL)
})

test('tampered JWT set as cookie → dashboard rejects → redirects to /login', async ({ page }) => {
  await page.context().addCookies([
    { name: 'auth_token', value: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYWtlIiwibmFtZSI6IkphbmUgRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.tampered_signature_here', path: '/', domain: '127.0.0.1' },
  ])
  await page.goto('/production')
  await expect(page).toHaveURL(LOGIN_URL)
})
