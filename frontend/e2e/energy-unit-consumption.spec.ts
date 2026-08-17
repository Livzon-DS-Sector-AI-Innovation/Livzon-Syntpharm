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
    // 1. 选择车间 - 等待下拉菜单有数据
    const workshopSelect = page.locator('.ant-select').filter({ hasText: '选择车间' })
    await workshopSelect.click()
    
    // 等待下拉菜单出现
    await page.waitForSelector('.ant-select-dropdown', { state: 'visible', timeout: 10000 })
    
    // 等待选项出现（不是"暂无数据"）
    await page.waitForFunction(() => {
      const options = document.querySelectorAll('.ant-select-item-option-content')
      return options.length > 0 && !options[0].textContent?.includes('暂无数据')
    }, { timeout: 10000 })
    
    // 点击第一个选项
    const firstOption = page.locator('.ant-select-item-option-content').first()
    await firstOption.click()
    
    // 等待下拉菜单关闭
    await page.waitForSelector('.ant-select-dropdown', { state: 'hidden', timeout: 5000 })

    // 2. 选择月份 - Ant Design 6.x MonthPicker 显示英文月份缩写 (Jan, Feb...)
    await page.locator('.ant-picker-input > input').first().click()
    
    // 等待月份面板出现
    await page.waitForSelector('.ant-picker-panel-container', { state: 'visible', timeout: 10000 })
    await page.waitForTimeout(500)
    
    // 点击任意月份单元格（使用英文月份缩写匹配）
    const monthCell = page.locator('.ant-picker-cell-inner').filter({ hasText: /^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$/ }).first()
    await expect(monthCell).toBeVisible({ timeout: 5000 })
    await monthCell.click()
    
    // 等待面板关闭
    await page.waitForSelector('.ant-picker-panel-container', { state: 'hidden', timeout: 5000 })

    // 3. 设定目标 - 等待目标区域加载完成
    await page.waitForTimeout(1000)
    
    // 检查是否已有目标（显示"修改目标"）或需要设定新目标（显示"设定目标"）
    const hasExistingTarget = await page.getByRole('button', { name: /修改目标/ }).isVisible({ timeout: 3000 }).catch(() => false)
    
    if (hasExistingTarget) {
      // 已有目标，点击修改
      await page.getByRole('button', { name: /修改目标/ }).click()
    } else {
      // 没有目标，点击设定
      await page.getByRole('button', { name: /设定目标/ }).click()
    }
    
    // 填写目标值
    await page.getByPlaceholder('请输入目标单耗').fill('2.30')
    await page.getByRole('button', { name: '确认设定' }).click()

    // 4. 验证目标显示
    await expect(page.getByText('2.3000')).toBeVisible({ timeout: 5000 })

    // 5. 录入多产品
    await page.getByRole('button', { name: /添加产品/ }).click()
    
    // 等待新行添加到表格
    await page.waitForSelector('table tbody tr', { state: 'visible', timeout: 5000 })
    
    // 产品名称字段使用 placeholder="输入名称"
    await page.getByPlaceholder('输入名称').fill('布南色林')
    
    // 产量字段是 InputNumber，使用更通用的选择器
    const quantityInput = page.locator('.ant-input-number').first().locator('input')
    await quantityInput.fill('12000')

    // 6. 开始分析
    await page.getByRole('button', { name: /开始智能分析/ }).click()

    // 7. 验证结果
    await expect(page.getByText(/实际单耗/)).toBeVisible({ timeout: 15000 })
  })
})
