import { test, expect } from '@playwright/test'

const LOGIN_URL = /\/login(?:\?.*)?$/

test('missing token redirects to /login?error=callback_failed', async ({ page, request }) => {
  const res = await request.get('/auth/callback', { maxRedirects: 0 })
  expect(res.status()).toBe(307)
  expect(res.headers()['location']).toContain('/login?error=callback_failed')

  await page.goto(res.headers()['location'] || '/login?error=callback_failed')
  await expect(page).toHaveURL(LOGIN_URL)
  await expect(page.getByRole('heading', { name: '工厂管理平台' })).toBeVisible()
})

test('empty token redirects to /login?error=callback_failed', async ({ page, request }) => {
  const res = await request.get('/auth/callback', { maxRedirects: 0, params: { token: '' } })
  expect(res.status()).toBe(307)
  expect(res.headers()['location']).toContain('/login?error=callback_failed')

  await page.goto(res.headers()['location'] || '/login?error=callback_failed')
  await expect(page).toHaveURL(LOGIN_URL)
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
