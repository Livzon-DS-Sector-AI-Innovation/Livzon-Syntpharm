import { chromium, expect } from '@playwright/test'
import path from 'path'
import fs from 'fs'

const authFile = path.join(__dirname, '.auth', 'storageState.json')

async function globalSetup(config: any) {
  const baseURL = config.projects?.[0]?.use?.baseURL || 'http://localhost:3000'
  const apiURL = process.env.E2E_BACKEND_URL || 'http://localhost:18000'
  const e2eSecret = process.env.E2E_AUTH_SECRET || 'e2e-test-secret'
  
  const browser = await chromium.launch()
  const context = await browser.newContext()
  const page = await context.newPage()
  
  try {
    // 使用 test-login 端点获取 token
    const loginResponse = await page.request.post(`${apiURL}/api/v1/identity/auth/test-login`, {
      headers: {
        'X-E2E-Secret': e2eSecret
      }
    })
    
    if (!loginResponse.ok()) {
      const errorText = await loginResponse.text()
      console.error(`Login failed: ${loginResponse.status()} ${loginResponse.statusText()}`)
      console.error(`Response body: ${errorText}`)
      throw new Error(`Login failed with status ${loginResponse.status()}`)
    }
    
    const { token } = await loginResponse.json()
    expect(token).toBeTruthy()
    
    // 设置认证状态
    await context.addCookies([{
      name: 'auth_token',
      value: token,
      domain: new URL(baseURL).hostname,
      path: '/'
    }])
    
    // 创建测试车间
    const workshopResponse = await page.request.post(`${apiURL}/api/v1/energy/workshops`, {
      headers: {
        'Authorization': `Bearer ${token}`
      },
      data: {
        name: 'E2E测试车间',
        code: 'E2E-001',
        location: '测试地点',
        is_active: true,
        category: 'workshop'
      }
    })
    
    // 严格验证车间创建成功
    if (!workshopResponse.ok()) {
      const errorText = await workshopResponse.text()
      throw new Error(`Failed to create workshop: ${workshopResponse.status()} ${errorText}`)
    }
    
    const workshop = await workshopResponse.json()
    expect(workshop.code).toBe(200)
    expect(workshop.data?.id).toBeTruthy()
    
    // 验证车间可以被查询到
    const listResponse = await page.request.get(`${apiURL}/api/v1/energy/workshops?category=workshop`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    
    if (!listResponse.ok()) {
      const errorText = await listResponse.text()
      console.error(`List workshops failed: ${listResponse.status()} ${listResponse.statusText()}`)
      console.error(`Response body: ${errorText}`)
      throw new Error(`List workshops failed with status ${listResponse.status()}`)
    }
    
    const listData = await listResponse.json()
    console.log('Workshop list response:', JSON.stringify(listData, null, 2))
    expect(listData.code).toBe(200)
    
    // Check if items exist and have length
    const items = listData.data?.items || listData.items || listData.data || []
    expect(Array.isArray(items)).toBe(true)
    expect(items.length).toBeGreaterThan(0)
    
    // 创建测试能耗数据（用于能源单耗分析测试）
    const energyDataResponse = await page.request.post(`${apiURL}/api/v1/energy/monthly/batch`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: {
        records: [
          {
            workshop_id: workshop.data.id,
            energy_type: 'electricity',
            record_date: '2026-01-15',
            value: 50000,
            unit: 'kWh',
            source: 'manual',
            remark: 'E2E test data'
          }
        ]
      }
    })
    
    if (!energyDataResponse.ok()) {
      const errorText = await energyDataResponse.text()
      console.error(`Failed to create energy data: ${energyDataResponse.status()} ${errorText}`)
      throw new Error(`Failed to create energy data: ${energyDataResponse.status()}`)
    }
    
    console.log('Energy data created successfully')

    // 保存认证状态
    // Ensure directory exists
    const dir = path.dirname(authFile)
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true })
    }
    await context.storageState({ path: authFile })
  } finally {
    await browser.close()
  }
}

export default globalSetup
