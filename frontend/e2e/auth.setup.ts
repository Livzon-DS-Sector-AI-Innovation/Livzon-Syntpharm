import { chromium } from '@playwright/test'
import path from 'path'

const AUTH_FILE = path.join(__dirname, '.auth', 'storageState.json')

export default async function globalSetup() {
  const browser = await chromium.launch()
  const context = await browser.newContext()
  const page = await context.newPage()

  const res = await context.request.post('http://127.0.0.1:8000/api/v1/identity/auth/test-login', {
    headers: { 'X-E2E-Secret': 'dazah-e2e-secret-2024' },
  })
  const { token } = await res.json()

  await page.goto(`http://127.0.0.1:3000/auth/callback?token=${token}`)
  await page.waitForTimeout(3000)

  await context.storageState({ path: AUTH_FILE })
  await browser.close()
}