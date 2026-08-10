# E2E 测试实施计划

## ✅ 已完成

- P0 严重问题已全部修复
- 后端容器已重新构建并启动
- 代码通过 lint 检查

## 📋 待完成事项

### 1. 实现自动登录（优先级：高）

**当前问题**：E2E 测试中的登录步骤是 TODO

**解决方案**：

```typescript
// frontend/e2e/helpers/auth.ts
import { Page } from '@playwright/test'

export async function login(page: Page, username = 'admin@livzon.cn', password = 'Admin123456') {
  await page.goto('/auth/login')
  await page.getByPlaceholder('邮箱').fill(username)
  await page.getByPlaceholder('密码').fill(password)
  await page.getByRole('button', { name: '登录' }).click()
  
  // 等待登录成功（跳转到首页）
  await page.waitForURL('**/production', { timeout: 10000 })
}
```

在测试中使用：

```typescript
test.beforeEach(async ({ page }) => {
  await login(page)
  await page.goto('/energy/ai-analysis')
})
```

### 2. 修复 E2E 测试用例

**需要修改的文件**：`frontend/e2e/energy-unit-consumption.spec.ts`

**修改点**：
- [ ] 所有 "件" 改为 "kg"
- [ ] 添加登录步骤
- [ ] 优化选择器（使用 data-testid 或更稳定的 role）
- [ ] 增加超时时间（AI 分析可能需要更长时间）

### 3. 运行 E2E 测试

```bash
cd frontend
npx playwright test e2e/energy-unit-consumption.spec.ts --headed
```

### 4. 验证测试结果

**预期通过的测试**：
- TC1: 完整流程（设定目标 → 输入产量 → 查看分析）
- TC2: 无目标时的提示
- TC3: 偏差率不同状态的 UI 显示

**可能失败的场景**：
- TC4: 错误场景（需要 mock 网络错误）
- TC5: 目标修改后的实时更新（需要验证缓存同步）

## 🎯 下一步行动

1. **立即执行**：实现自动登录辅助函数
2. **然后**：修复 E2E 测试用例中的单位和选择器
3. **最后**：运行测试并根据结果迭代修复

## 💡 注意事项

- 确保数据库中有测试数据（101 车间 2026-04 月能耗数据）
- 确保 DeepSeek API Key 已配置
- 前端页面需要强制刷新（Ctrl+Shift+R）以清除缓存
