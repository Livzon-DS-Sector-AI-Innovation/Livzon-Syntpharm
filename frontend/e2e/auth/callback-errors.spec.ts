import { test, expect } from '@playwright/test'

const LOGIN_URL = /\/login(?:\?.*)?$/

test('missing token redirects to /login?error=callback_failed', async ({ page }) => {
  await page.goto('/auth/callback')
  await expect(page).toHaveURL(/\/login\?error=callback_failed/)
  await expect(page.getByRole('heading', { name: '工厂管理平台' })).toBeVisible()
})

test('empty token redirects to /login?error=callback_failed', async ({ page }) => {
  await page.goto('/auth/callback?token=')
  await expect(page).toHaveURL(/\/login\?error=callback_failed/)
})

test('garbage token set as cookie → dashboard rejects → redirects to /login', async ({ page }) => {
  await page.evaluate(() => {
    document.cookie = 'auth_token=not-a-valid-jwt; path=/'
  })
  await page.goto('/production')
  await expect(page).toHaveURL(LOGIN_URL)
})

test('tampered JWT set as cookie → dashboard rejects → redirects to /login', async ({ page }) => {
  await page.evaluate(() => {
    document.cookie = 'auth_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYWtlIiwibmFtZSI6IkphbmUgRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.tampered_signature_here; path=/'
  })
  await page.goto('/production')
  await expect(page).toHaveURL(LOGIN_URL)
})
