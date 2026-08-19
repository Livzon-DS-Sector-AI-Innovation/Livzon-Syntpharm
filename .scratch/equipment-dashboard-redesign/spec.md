# 设备台账页面视觉与交互优化 Spec

## Problem Statement

当前设备台账页面存在以下问题，影响用户体验和操作效率：

1. **视觉语言缺乏特色**：使用标准的 Ant Design 默认样式，与"工业设备管理"主题脱节，给人"通用后台模板"的印象
2. **信息架构拥挤**：20列表格横向滚动体验差，统计卡片与表格的视觉层级不清晰
3. **关键功能入口隐蔽**："新增分类/位置"按钮隐藏在树形组件内部，新用户不清楚为什么要先建分类/位置
4. **空状态无引导**：当分类/位置为空时，只显示空白，没有解释业务逻辑或提供操作引导
5. **状态展示单调**：仅用彩色文字标签表示设备状态，缺乏视觉冲击力和快速识别性

用户（设备管理员、巡检人员）需要一个更直观、更有工业感的控制台界面，能够快速掌握设备全局状态并高效执行日常管理操作。

## Solution

将设备台账页面从"数据库 CRUD 视图"重构为"工业数字孪生控制台"，通过以下改进提升可用性和视觉辨识度：

1. **引入工业 HMI 设计语言**：采用深蓝灰主色调 + 机械蓝强调色 + 安全橙警示色的色彩系统，搭配 JetBrains Mono 等宽字体显示资产编号和数据
2. **重构布局为三栏式仪表盘**：顶部统计概览 → 左侧筛选器 → 右侧设备列表，减少视觉跳跃
3. **增强"新建分类/位置"的可见性和引导性**：在树形组件顶部添加明显的行动召唤按钮和工具提示，解释业务价值
4. **实现空状态引导**：当分类/位置为空时，显示带说明文字和 CTA 按钮的空状态卡片
5. **优化表格体验**：默认隐藏次要列，提供"列配置"功能让用户自定义显示字段
6. **增强状态可视化**：使用带图标的彩色徽章替代纯文字标签

## User Stories

### 核心流程

1. As a 设备管理员, I want to see 设备总数和各类状态分布 at a glance, so that I can quickly assess the overall equipment health
2. As a 设备管理员, I want to filter equipment by category/location/department/status, so that I can focus on specific subsets of assets
3. As a 设备管理员, I want to create a new equipment category with a clear explanation of why it's needed, so that I understand the business value of categorization
4. As a 设备管理员, I want to create a new location with hierarchical structure (厂→车间→区域), so that I can organize equipment by physical coordinates
5. As a 新入职管理员, I want to see guided empty states when categories/locations are missing, so that I know what to do first

### 数据浏览

6. As a 巡检人员, I want to see equipment status as colorful badges with icons, so that I can identify issues at a glance from a distance
7. As a 设备管理员, I want to customize which columns are visible in the table, so that I can reduce horizontal scrolling and focus on relevant fields
8. As a 设备管理员, I want to search equipment by asset number or name, so that I can quickly find specific assets
9. As a 设备管理员, I want to see pagination with total count, so that I know how many records exist
10. As a 设备管理员, I want to hover over equipment names to see a quick preview card, so that I can get key info without opening the detail drawer

### 批量操作

11. As a 设备管理员, I want to import equipment data from Excel, so that I can bulk-create assets during initial setup
12. As a 设备管理员, I want to export the current filtered view to Excel, so that I can share reports with management

### 设备管理

13. As a 设备管理员, I want to edit equipment details inline or via drawer, so that I can update information efficiently
14. As a 维修协调员, I want to submit a repair request directly from the table, so that I can log issues without navigating away
15. As a 设备管理员, I want to delete equipment with confirmation, so that I prevent accidental data loss

### 响应式与可访问性

16. As a mobile user, I want the layout to adapt to smaller screens, so that I can check equipment status on my phone during field inspections
17. As a keyboard-only user, I want all interactive elements to be accessible via Tab navigation, so that I can operate the interface without a mouse
18. As a user with reduced motion preference, I want animations to respect my system settings, so that the interface doesn't cause discomfort

## Implementation Decisions

### 模块修改

- **前端组件**：
  - `EquipmentPage.tsx`：重构布局结构，将 StatsCards 移到顶部
  - `EquipmentTable.tsx`：添加列配置功能，优化状态渲染
  - `CategoryTree.tsx`：增强"新建分类"按钮可见性，添加工具提示
  - `LocationTree.tsx`：同上
  - 新增 `EmptyStateGuide.tsx`：空状态引导组件
  - 新增 `ColumnConfigModal.tsx`：列配置弹窗组件
  - 新增 `StatusBadge.tsx`：状态徽章组件

- **Store 扩展**：
  - `useEquipmentStore`：添加 `visibleColumns` 状态，用于列配置持久化

### 接口变更

- **新增 API**（可选，如果后端支持）：
  - `GET /api/v1/equipment/columns/config`：获取用户的列配置偏好
  - `POST /api/v1/equipment/columns/config`：保存列配置偏好

- **现有 API 无需变更**：所有优化均为前端层面，不依赖后端改动

### 设计系统扩展

- **色彩令牌**（添加到 `antd-theme.ts`）：
  ```typescript
  const industrialPalette = {
    deepSteel: '#1e293b',
    machineBlue: '#0ea5e9',
    safetyOrange: '#f97316',
    signalGreen: '#10b981',
    panelBase: '#f8fafc',
    surface: '#ffffff',
    border: '#e2e8f0',
  }
  ```

- **状态徽章映射**：
  ```typescript
  const statusBadgeMap = {
    '在用':   { icon: '🟢', color: '#10b981', label: '运行中' },
    '备用':   { icon: '🔵', color: '#6366f1', label: '待命' },
    '维修中': { icon: '🟠', color: '#f97316', label: '维护' },
    '停用':   { icon: '⚪', color: '#94a3b8', label: '离线' },
    '报废':   { icon: '🔴', color: '#ef4444', label: '已报废' },
  }
  ```

### 交互细节

- **列配置持久化**：使用 `localStorage` 存储用户的列显示偏好，键名为 `equipment_visible_columns`
- **空状态触发条件**：当 `categories.length === 0` 或 `locations.length === 0` 时显示对应引导
- **工具提示内容**：
  - 分类："分类用于设备类型管理和统计分析。例如：生产设备、辅助设备。"
  - 位置："位置用于记录设备的物理坐标，便于巡检和应急响应。例如：A栋-1F-发酵区。"

## Testing Decisions

### 测试策略

- **单元测试**：测试新组件的渲染逻辑和状态管理
  - `StatusBadge`：验证不同状态的颜色和图标映射
  - `EmptyStateGuide`：验证空状态文案和 CTA 按钮渲染
  - `ColumnConfigModal`：验证列选择器的勾选状态同步

- **集成测试**：测试组件间的交互
  - 列配置保存后刷新页面，验证偏好是否恢复
  - 点击"新建分类"按钮，验证 CategoryEditor 抽屉是否正确打开

- **E2E 测试**：测试完整用户流程
  - 新用户首次访问，看到空状态引导 → 点击"创建第一个分类" → 成功创建后引导消失
  - 管理员自定义列配置 → 刷新页面 → 配置保持

### 测试优先级

1. **P0**：空状态引导流程（确保新用户不被卡住）
2. **P1**：列配置持久化（核心功能）
3. **P2**：状态徽章渲染（视觉增强）

### 参考现有测试

- 参考 `.scratch/equipment-import-v3/issues/04-frontend-quantity-column.md` 中的前端测试模式
- 使用 Playwright 进行 E2E 测试，参考 `frontend/tests/` 目录下的现有用例

## Out of Scope

以下内容不在本次优化范围内：

1. **后端 API 重构**：本次优化仅限前端层面，不涉及后端数据结构或 API 变更
2. **edbo-service 集成**：贝叶斯优化服务与本页面无关
3. **设备图片/附件管理**：需要单独的文件上传模块
4. **批量操作（多选删除/编辑）**：需要额外的复选框逻辑和批量 API
5. **高级搜索（多条件组合）**：当前仅支持关键词搜索，复杂搜索需后续迭代
6. **移动端原生 App**：本次仅保证响应式 Web 布局，不开发原生应用
7. **实时数据推送（WebSocket）**：当前使用轮询或手动刷新，实时推送需后端支持

## Further Notes

### 设计原则

- **工业感 ≠ 复杂**：借鉴 HMI 系统的清晰度和功能性，但避免过度装饰
- **一致性优先**：所有新增组件遵循现有的 Ant Design 设计规范，仅在色彩和排版上做差异化
- **渐进式披露**：复杂功能（如列配置）默认隐藏，按需展开

### 性能考虑

- **列配置持久化**：使用 `localStorage` 而非后端 API，减少网络请求
- **虚拟滚动**：如果设备数量超过 1000 条，考虑引入 `react-window` 进行虚拟滚动优化

### 未来扩展方向

- **设备地图视图**：基于位置树生成厂区平面图，点击区域显示该区域设备
- **维保日历集成**：在统计卡片中显示即将到期的保养任务
- **二维码扫描**：移动端支持扫描设备二维码快速查看详情

### 风险与缓解

- **风险**：老用户可能不适应新的布局和交互
  - **缓解**：提供"切换回旧版"的临时选项，收集反馈后再决定是否保留

- **风险**：列配置过多导致 localStorage 膨胀
  - **缓解**：限制最多保存 5 套配置方案，超出时提示用户清理
