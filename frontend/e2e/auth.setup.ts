import { chromium, expect, FullConfig } from '@playwright/test'
import path from 'path'

const AUTH_FILE = path.join(__dirname, '.auth', 'storageState.json')

export default async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0]?.use?.baseURL || 'http://127.0.0.1:13000'
  const apiURL = process.env.E2E_BACKEND_URL || 'http://127.0.0.1:18000'
  const secret = process.env.E2E_AUTH_SECRET

  if (!secret) {
    throw new Error('E2E_AUTH_SECRET environment variable is required for test login')
  }

  const browser = await chromium.launch()
  const context = await browser.newContext()
  const page = await context.newPage()

  const loginResponse = await context.request.post(
    `${apiURL}/api/v1/identity/auth/test-login`,
    {
      headers: { 'X-E2E-Secret': secret },
    },
  )

  if (!loginResponse.ok()) {
    throw new Error(
      `E2E test-login failed: ${loginResponse.status()} ${await loginResponse.text()}`,
    )
  }

  const body: unknown = await loginResponse.json()

  if (
    typeof body !== 'object' ||
    body === null ||
    !('token' in body) ||
    typeof (body as Record<string, unknown>).token !== 'string'
  ) {
    throw new Error('E2E test-login returned no valid token')
  }

  const { token } = body as { token: string }

  if (token.length === 0) {
    throw new Error('E2E test-login returned empty token')
  }

  await page.goto(`${baseURL}/auth/callback?token=${encodeURIComponent(token)}`, {
    waitUntil: 'domcontentloaded',
    timeout: 30_000,
  })

  const cookies = await context.cookies()
  const authCookie = cookies.find(c => c.name === 'auth_token')

  if (!authCookie) {
    throw new Error('Authentication callback did not create auth_token cookie')
  }

  await page.goto(`${baseURL}/production`, {
    waitUntil: 'domcontentloaded',
    timeout: 30_000,
  })

  await expect(page).toHaveURL(/\/production(?:\?.*)?$/)

  await expect(
    page.getByRole('heading', { name: '生产管理' }).first(),
  ).toBeVisible({ timeout: 15_000 })

  await context.storageState({ path: AUTH_FILE })
  await browser.close()
}
