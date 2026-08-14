import { test as setup, expect } from '@playwright/test'
import path from 'path'

const authFile = path.join(__dirname, '.auth', 'user.json')

setup('authenticate', async ({ page, request }) => {
  // 登录获取 token
  const loginResponse = await request.post('/api/v1/auth/login', {
    data: {
      username: 'admin',
      password: 'admin123'
    }
  })
  
  expect(loginResponse.ok()).toBeTruthy()
  const { token } = await loginResponse.json()
  expect(token).toBeTruthy()
  
  // 设置认证状态
  await page.context().addCookies([{
    name: 'token',
    value: token,
    domain: 'localhost',
    path: '/'
  }])
  
  // 创建测试车间
  const workshopResponse = await request.post('/api/v1/energy/workshops', {
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
  const listResponse = await request.get('/api/v1/energy/workshops?category=workshop', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
  
  expect(listResponse.ok()).toBeTruthy()
  const listData = await listResponse.json()
  expect(listData.code).toBe(200)
  expect(listData.data?.items?.length).toBeGreaterThan(0)
  
  // 保存认证状态
  await page.context().storageState({ path: authFile })
})
