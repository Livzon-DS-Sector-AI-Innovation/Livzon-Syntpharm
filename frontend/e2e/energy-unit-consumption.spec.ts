import { test, expect } from '@playwright/test'
import path from 'path'

const AUTH_FILE = path.join(__dirname, '.auth', 'storageState.json')

test.use({ storageState: AUTH_FILE })

test.describe('能源单耗智能分析功能', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/energy/ai-analysis')
    await expect(page.getByRole('heading', { name: 'AI 能耗智能分析' })).toBeVisible({ timeout: 10000 })
    await page.waitForLoadState('networkidle')
  })

  test('TC1: 设定目标 → 录入多产品 → 查看分析结果', async ({ page }) => {
    // 1. 选择车间 - 使用更稳健的选择器
    const workshopSelect = page.locator('.ant-select').filter({ hasText: '选择车间' })
    await workshopSelect.click()
    
    // 等待下拉选项出现（Ant Design 5.x 使用 rc-virtual-list）
    await page.waitForSelector('.ant-select-item-option', { state: 'visible', timeout: 5000 })
    
    // 点击第一个选项
    await page.locator('.ant-select-item-option').first().click()
    
    // 验证选择生效
    await expect(workshopSelect).not.toHaveText(/选择车间/, { timeout: 5000 })

    // 2. 选择月份
    await page.locator('.ant-picker-input > input').first().click()
    await page.waitForTimeout(500)
    await page.getByRole('cell', { name: /\d+/ }).first().click()

    // 3. 设定目标
    await page.getByRole('button', { name: /设定目标/ }).click()
    await page.getByPlaceholder('请输入目标单耗').fill('2.30')
    await page.getByRole('button', { name: '确认设定' }).click()

    // 4. 验证目标显示
    await expect(page.getByText('2.3000')).toBeVisible({ timeout: 5000 })

    // 5. 录入多产品
    await page.getByRole('button', { name: /添加产品/ }).click()
    await page.getByPlaceholder('产品名称').fill('布南色林')
    await page.getByPlaceholder('产量').fill('12000')

    // 6. 开始分析
    await page.getByRole('button', { name: /开始智能分析/ }).click()

    // 7. 验证结果
    await expect(page.getByText(/实际单耗/)).toBeVisible({ timeout: 15000 })
  })
})
