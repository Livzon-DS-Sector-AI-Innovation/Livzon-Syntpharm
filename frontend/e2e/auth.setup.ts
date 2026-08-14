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

  console.log('🔐 Starting E2E authentication setup...')
  console.log(`   Base URL: ${baseURL}`)
  console.log(`   API URL: ${apiURL}`)

  const browser = await chromium.launch()
  const context = await browser.newContext()
  const page = await context.newPage()

  // Step 1: Get test token from API
  console.log('📡 Requesting test login token...')
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

  console.log('✅ Token received')

  // Step 2: Validate token by calling getCurrentUser API
  console.log('🔍 Validating token...')
  const userResponse = await context.request.get(`${apiURL}/api/v1/identity/me`, {
    headers: { 'Authorization': `Bearer ${token}` },
  })

  if (!userResponse.ok()) {
    console.warn('⚠️  Token validation via API failed, proceeding with callback anyway')
  } else {
    console.log('✅ Token validated successfully')
  }

  // Step 3: Set cookie directly (more reliable than callback route)
  console.log('🍪 Setting auth cookie...')
  await context.addCookies([{
    name: 'auth_token',
    value: token,
    domain: new URL(baseURL).hostname,
    path: '/',
    httpOnly: true,
    secure: baseURL.startsWith('https:'),
    sameSite: 'Lax',
  }])

  // Verify cookie was set
  const cookies = await context.cookies()
  const authCookie = cookies.find(c => c.name === 'auth_token')
  
  if (!authCookie) {
    throw new Error('Failed to set auth_token cookie')
  }
  
  console.log('✅ Auth cookie set successfully')

  // Step 4: Create test workshop data for energy tests
  console.log('🏭 Creating test workshop data...')
  let workshopId: string | null = null
  try {
    const workshopResponse = await context.request.post(
      `${apiURL}/api/v1/energy/workshops`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        data: {
          code: 'E2E-TEST-WORKSHOP',
          name: 'E2E测试车间',
          category: 'workshop',
          sort_order: 0,
          is_active: true,
        },
      },
    )

    if (workshopResponse.ok()) {
      const workshopData = await workshopResponse.json() as any
      workshopId = workshopData.data?.id
      console.log('✅ Test workshop created successfully')
    } else {
      // Workshop might already exist (idempotent), check if it's a duplicate error
      const responseText = await workshopResponse.text()
      if (responseText.includes('duplicate') || responseText.includes('已存在')) {
        console.log('ℹ️  Test workshop already exists (skipping creation)')
        // Try to get the workshop ID by listing workshops
        const listResponse = await context.request.get(
          `${apiURL}/api/v1/energy/workshops?category=workshop`,
          {
            headers: { 'Authorization': `Bearer ${token}` },
          },
        )
        if (listResponse.ok()) {
          const listData = await listResponse.json() as any
          const workshop = listData.data?.items?.find((w: any) => w.name === 'E2E测试车间')
          if (workshop) {
            workshopId = workshop.id
          }
        }
      } else {
        console.warn(`⚠️  Workshop creation failed: ${workshopResponse.status()} ${responseText}`)
      }
    }
  } catch (error) {
    console.warn('⚠️  Failed to create test workshop:', error)
  }

  // Step 4.5: Create test energy data for the workshop
  if (workshopId) {
    console.log('⚡ Creating test energy data...')
    try {
      // Create monthly energy records for 2026-01 (the month the test will use)
      const energyDataResponse = await context.request.post(
        `${apiURL}/api/v1/energy/monthly/batch`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          data: {
            records: [
              {
                workshop_id: workshopId,
                energy_type: 'electricity',
                record_date: '2026-01-15',
                value: 50000,
                unit: 'kWh',
                source: 'manual',
                remark: 'E2E test data',
              },
            ],
          },
        },
      )

      if (energyDataResponse.ok()) {
        console.log('✅ Test energy data created successfully')
      } else {
        const responseText = await energyDataResponse.text()
        if (responseText.includes('duplicate') || responseText.includes('已存在')) {
          console.log('ℹ️  Test energy data already exists (skipping creation)')
        } else {
          console.warn(`⚠️  Energy data creation failed: ${energyDataResponse.status()} ${responseText}`)
        }
      }
    } catch (error) {
      console.warn('⚠️  Failed to create test energy data:', error)
    }
  }

  // Step 5: Navigate to production page and verify
  console.log('🚀 Navigating to production page...')
  await page.goto(`${baseURL}/production`, {
    waitUntil: 'networkidle',
    timeout: 30_000,
  })

  // Wait a bit for any client-side redirects
  await page.waitForTimeout(2000)

  console.log(`📍 Current URL: ${page.url()}`)

  await expect(page).toHaveURL(/\/production(?:\?.*)?$/, { timeout: 10_000 })

  await expect(
    page.getByRole('heading', { name: '生产管理概览' }).first(),
  ).toBeVisible({ timeout: 15_000 })

  console.log('✅ Authentication setup completed successfully')

  await context.storageState({ path: AUTH_FILE })
  await browser.close()
}
