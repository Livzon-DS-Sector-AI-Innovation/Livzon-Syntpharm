import { test, expect } from '@playwright/test'

test.describe('能源单耗智能分析功能', () => {
  test.beforeEach(async ({ page }) => {
    // 登录（假设已有认证机制）
    await page.goto('/auth/login')
    // TODO: 添加实际登录逻辑
    await page.goto('/energy/ai-analysis')
  })

  test('TC1: 设定目标 → 输入产量 → 查看分析结果', async ({ page }) => {
    // 1. 选择车间
    await page.getByPlaceholder('选择车间').click()
    await page.getByRole('option').first().click()

    // 2. 选择月份
    await page.getByPlaceholder('选择月份').click()
    await page.getByRole('cell', { name: '2026年8月' }).click()

    // 3. 设定目标
    await page.getByRole('button', { name: '➕ 设定目标' }).click()
    await page.getByPlaceholder('请输入目标单耗').fill('2.30')
    await page.getByRole('button', { name: '确认设定' }).click()

    // 4. 验证目标显示
    await expect(page.getByText('2.3000 kWh/kg')).toBeVisible()

    // 5. 输入产量
    await page.getByPlaceholder('当月产量（kg）').fill('12000')

    // 6. 开始分析
    await page.getByRole('button', { name: '🤖 开始智能分析' }).click()

    // 7. 等待分析结果
    await expect(page.getByText('📊 单耗分析结果')).toBeVisible({ timeout: 10000 })

    // 8. 验证单耗数据
    await expect(page.getByText(/实际单耗/)).toBeVisible()
    await expect(page.getByText(/目标单耗/)).toBeVisible()
    await expect(page.getByText(/偏差率/)).toBeVisible()
  })

  test('TC2: 无目标时的提示', async ({ page }) => {
    // 选择车间和月份，但不设定目标
    await page.getByPlaceholder('选择车间').click()
    await page.getByRole('option').first().click()

    await page.getByPlaceholder('选择月份').click()
    await page.getByRole('cell', { name: '2026年8月' }).click()

    // 验证显示"未设定"
    await expect(page.getByText('未设定')).toBeVisible()
    await expect(page.getByRole('button', { name: '➕ 设定目标' })).toBeVisible()

    // 输入产量并分析
    await page.getByPlaceholder('当月产量（kg）').fill('12000')
    await page.getByRole('button', { name: '🤖 开始智能分析' }).click()

    // 等待结果
    await expect(page.getByText('📊 单耗分析结果')).toBeVisible({ timeout: 10000 })

    // 验证状态为"未知"
    await expect(page.getByText(/未知/)).toBeVisible()
  })

  test('TC3: 偏差率不同状态的 UI 显示', async ({ page }) => {
    // 先设定一个较低的目标以触发 warning 或 critical
    await page.getByPlaceholder('选择车间').click()
    await page.getByRole('option').first().click()

    await page.getByPlaceholder('选择月份').click()
    await page.getByRole('cell', { name: '2026年8月' }).click()

    // 设定低目标
    await page.getByRole('button', { name: '➕ 设定目标' }).click()
    await page.getByPlaceholder('请输入目标单耗').fill('1.00')
    await page.getByRole('button', { name: '确认设定' }).click()

    // 输入产量
    await page.getByPlaceholder('当月产量（kg）').fill('12000')

    // 分析
    await page.getByRole('button', { name: '🤖 开始智能分析' }).click()

    // 等待结果
    await expect(page.getByText('📊 单耗分析结果')).toBeVisible({ timeout: 10000 })

    // 验证警告状态（实际单耗会远高于目标）
    const alertBox = page.getByRole('alert')
    await expect(alertBox).toBeVisible()
    
    // 应该包含警告或严重超标的文本
    const alertText = await alertBox.textContent()
    expect(alertText).toMatch(/警告|严重超标/)
  })

  test('TC4: 产量输入验证', async ({ page }) => {
    await page.getByPlaceholder('选择车间').click()
    await page.getByRole('option').first().click()

    await page.getByPlaceholder('选择月份').click()
    await page.getByRole('cell', { name: '2026年8月' }).click()

    const analyzeButton = page.getByRole('button', { name: '🤖 开始智能分析' })

    // 测试空值 - 按钮应禁用
    await expect(analyzeButton).toBeDisabled()

    // 测试负数
    await page.getByPlaceholder('当月产量（kg）').fill('-100')
    // InputNumber 组件通常会自动阻止负数输入，或者显示错误

    // 测试零值
    await page.getByPlaceholder('当月产量（kg）').fill('0')
    await expect(analyzeButton).toBeDisabled()

    // 测试有效值
    await page.getByPlaceholder('当月产量（kg）').fill('12000')
    await expect(analyzeButton).toBeEnabled()
  })

  test('TC5: 目标修改功能', async ({ page }) => {
    // 先设定一个目标
    await page.getByPlaceholder('选择车间').click()
    await page.getByRole('option').first().click()

    await page.getByPlaceholder('选择月份').click()
    await page.getByRole('cell', { name: '2026年8月' }).click()

    await page.getByRole('button', { name: '➕ 设定目标' }).click()
    await page.getByPlaceholder('请输入目标单耗').fill('2.30')
    await page.getByRole('button', { name: '确认设定' }).click()

    // 验证目标已显示
    await expect(page.getByText('2.3000 kWh/kg')).toBeVisible()

    // 点击修改按钮
    await page.getByRole('button', { name: '✏️ 修改目标' }).click()

    // 修改目标值
    await page.getByPlaceholder('请输入目标单耗').fill('2.50')
    await page.getByRole('button', { name: '确认设定' }).click()

    // 验证目标已更新
    await expect(page.getByText('2.5000 kWh/kg')).toBeVisible()
  })
})
