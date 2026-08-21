# 设备删除后筛选状态保持修复 Spec

## Problem Statement

用户在设备台账页面进行筛选（按部门、位置等）后，通过表格行上的"删除"按钮删除单个设备时遇到问题：

1. **筛选失效**：删除后列表显示全厂设备而非筛选后的设备
2. **分页异常**：下一页按钮消失，分页组件认为只有一页
3. **视觉不一致**：筛选栏仍显示原筛选条件，但列表数据不匹配

用户需要刷新页面才能恢复正常的筛选视图，这打断了工作流程。

**注意**：批量删除功能已实现且工作正常，本 spec 仅关注单个删除的筛选保持问题。

## Solution

修复 `EquipmentTable` 组件中 `handleDelete` 函数的闭包陷阱，确保删除操作后使用最新的筛选状态刷新列表。

## User Stories

1. As a 设备管理员, I want the filter conditions (department, location, status) to remain active after deleting a single equipment via the row action button, so that my workflow is not interrupted
2. As a 设备管理员, I want the equipment list to show only filtered items after deletion, not all equipment, so that I can continue working with the filtered view
3. As a 设备管理员, I want the pagination to work correctly after deletion, with "Next Page" button appearing/disappearing based on actual total count, so that I can navigate through filtered results
4. As a 设备管理员, I want the statistics cards to update after deletion while maintaining filters, so that I see accurate counts for the filtered subset

## Implementation Decisions

### 根本原因分析

**问题根因**：`handleDelete` 函数使用了 `useCallback`，其依赖项为 `[modal, message, onPageChange, localPage, localPageSize]`。当筛选状态（如 `departmentFilter`）变化时：
1. `fetchData` 重新创建（因为它的依赖项包括筛选状态）
2. `onPageChange` 指向新的 `(p, ps) => fetchData(p, ps)` 函数
3. 但如果 `handleDelete` 的 `useCallback` 没有正确捕获这个变化，它内部持有的 `onPageChange` 引用可能是旧的

**具体场景**：
- 用户选择部门 → `departmentFilter` 更新
- `fetchData` 重新创建，捕获新的 `departmentFilter`
- `onPageChange` 指向新的函数
- 用户点击某行的"删除"按钮 → `handleDelete(record)` 被调用
- `modal.confirm` 创建，`onOk` 回调捕获当前的 `onPageChange`
- 用户确认删除 → `onOk` 执行，调用 `onPageChange(localPage, localPageSize)`
- **如果此时 `onPageChange` 指向的是旧的 `fetchData`**，它会使用旧的 `departmentFilter`（可能是 `null`），导致请求不带筛选参数

### 修复方案

**方案 A（推荐）**：移除 `handleDelete` 的 `useCallback` 包装

```typescript
// 修改前
const handleDelete = useCallback((record: Equipment) => {
  modal.confirm({
    onOk: async () => {
      await deleteEquipment(record.id)
      onPageChange(localPage, localPageSize)
      onRefreshStatistics?.()
    },
  })
}, [modal, message, onPageChange, localPage, localPageSize])

// 修改后
const handleDelete = (record: Equipment) => {
  modal.confirm({
    onOk: async () => {
      await deleteEquipment(record.id)
      onPageChange(localPage, localPageSize)
      onRefreshStatistics?.()
    },
  })
}
```

**优点**：
- 简单直接，每次渲染都捕获最新的状态
- 不需要修改依赖项或重构代码

**缺点**：
- 每次渲染都创建新函数（但影响微乎其微，因为是事件处理函数）

**方案 B**：完善 `useCallback` 的依赖项

确保所有相关状态都在依赖项中，但这需要仔细审查哪些状态会影响行为，容易遗漏。

**决策**：采用方案 A，因为它更简单且不易出错。

### 前端模块修改

1. **EquipmentTable 组件** (`frontend/src/components/equipment/EquipmentTable.tsx`)
   - 移除 `handleDelete` 的 `useCallback` 包装
   - 保持其他逻辑不变

### 测试策略

2. **手动测试**：
   - 按部门筛选后删除单个设备
   - 验证列表仍显示该部门的设备
   - 验证分页按钮正确显示
   - 验证筛选栏状态保持

3. **E2E 测试**（可选）：
   - 使用 Playwright 模拟完整流程
   - 参考现有测试模式

## Out of Scope

1. **批量删除功能**：已实现，不在本 spec 范围内
2. **统计卡片动态筛选**：作为后续任务（Issue 03），需要后端 API 支持
3. **撤销删除功能**：不包含回收站或撤销机制

## Further Notes

### 技术债务

- **闭包陷阱风险**：React 的 `useCallback` 和闭包可能导致状态不同步，这是一个常见问题。团队应建立代码审查规范，避免在事件处理函数中过度使用 `useCallback`

### 性能考虑

- 移除 `useCallback` 后，每次渲染都会创建新的 `handleDelete` 函数，但对于事件处理函数来说，这种开销可以忽略不计

### 安全考虑

- 删除操作已有二次确认对话框
- 后端权限验证由 `current_user` 依赖注入处理
