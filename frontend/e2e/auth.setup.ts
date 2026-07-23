import { chromium, FullConfig } from '@playwright/test'
import path from 'path'

const AUTH_FILE = path.join(__dirname, '.auth', 'storageState.json')

export default async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0]?.use?.baseURL || 'http://localhost:3000'
  const apiURL = process.env.API_BASE_URL || 'http://127.0.0.1:8000'

  const browser = await chromium.launch()
  const context = await browser.newContext()
  const page = await context.newPage()

  const res = await context.request.post(`${apiURL}/api/v1/identity/auth/test-login`, {
    headers: { 'X-E2E-Secret': 'dazah-e2e-secret-2024' },
  })
  const { token } = await res.json()

  await page.goto(`${baseURL}/auth/callback?token=${token}`, { waitUntil: 'commit' })

  await context.storageState({ path: AUTH_FILE })
  await browser.close()
}