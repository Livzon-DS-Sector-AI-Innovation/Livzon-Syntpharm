import { chromium, FullConfig } from '@playwright/test'
import path from 'path'

const AUTH_FILE = path.join(__dirname, '.auth', 'storageState.json')

export default async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0]?.use?.baseURL || 'http://localhost:3000'
  const apiURL = process.env.E2E_BACKEND_URL || 'http://127.0.0.1:18000'
  const secret = process.env.E2E_AUTH_SECRET

  if (!secret) {
    throw new Error('E2E_AUTH_SECRET environment variable is required for test login')
  }

  const browser = await chromium.launch()
  const context = await browser.newContext()
  const page = await context.newPage()

  const response = await context.request.post(`${apiURL}/api/v1/identity/auth/test-login`, {
    headers: { 'X-E2E-Secret': secret },
  })

  if (!response.ok()) {
    throw new Error(
      `E2E login failed: ${response.status()} ${await response.text()}`,
    )
  }

  const body: unknown = await response.json()

  if (
    typeof body !== 'object' ||
    body === null ||
    !('token' in body) ||
    typeof (body as Record<string, unknown>).token !== 'string'
  ) {
    throw new Error('E2E login returned no token')
  }

  const { token } = body as { token: string }

  await page.goto(`${baseURL}/auth/callback?token=${token}`, { waitUntil: 'commit', timeout: 60000 })

  await context.storageState({ path: AUTH_FILE })
  await browser.close()
}
