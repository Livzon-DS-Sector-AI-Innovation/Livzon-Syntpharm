import { defineConfig, devices } from '@playwright/test'

/**
 * E2E 的默认源：只在本文件（CI 配置）里出现一次，用例与 setup 统一从这里取，
 * 避免在 .spec.ts 里重复硬编码地址。
 */
export const FRONTEND_ORIGIN = (process.env.E2E_FRONTEND_URL ?? 'http://127.0.0.1:13000').replace(/\/+$/, '')
export const BACKEND_ORIGIN = (process.env.E2E_BACKEND_URL ?? 'http://localhost:18000').replace(/\/+$/, '')

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/auth.setup.ts',
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI
    ? [['line'], ['html', { open: 'never' }]]
    : [['html', { open: 'never' }]],
  use: {
    baseURL: FRONTEND_ORIGIN,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'e2e/.auth/storageState.json',
      },
      testIgnore: /auth\/.*\.spec\.ts/,
    },
    {
      name: 'chromium-no-auth',
      use: { ...devices['Desktop Chrome'] },
      testMatch: /auth\/.*\.spec\.ts/,
    },
  ],
})