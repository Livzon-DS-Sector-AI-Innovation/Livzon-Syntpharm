# 02 — 表格列配置功能

**What to build:** 允许用户自定义设备表格中显示的列，持久化偏好到 localStorage。

**Blocked by:** 01 (需要先完成基础交互优化)

**Blocking:** None

**Status:** ready-for-agent

## Acceptance Criteria

- [ ] 在表格右上角添加"⚙️ 列配置"按钮
- [ ] 点击按钮弹出 Modal，显示所有可用列的复选框列表
- [ ] 默认选中核心列：资产编号、设备名称、状态、位置、部门、负责人、投用日期、操作
- [ ] 用户勾选/取消勾选后，点击"保存"按钮
- [ ] 保存后，表格立即更新显示/隐藏对应列
- [ ] 刷新页面后，列配置从 localStorage 恢复
- [ ] localStorage 键名为 `equipment_visible_columns`，值为列 key 数组

## Implementation Notes

- 定义所有列的配置元数据（key, label, defaultVisible）
- 使用 `useState` 管理 visibleColumns 状态
- 使用 `useEffect` 在 mount 时从 localStorage 读取配置
- 使用 `useEffect` 在 visibleColumns 变化时写入 localStorage
- 过滤 `columns` 数组时，只保留 visibleColumns 中包含的列（操作列始终显示）
- 文件修改：
  - `frontend/src/components/equipment/EquipmentTable.tsx`
  - 新增 `frontend/src/components/equipment/ColumnConfigModal.tsx`

## Testing

- [ ] 手动测试：打开列配置，取消勾选某列，验证该列隐藏
- [ ] 手动测试：刷新页面，验证列配置保持
- [ ] 手动测试：重置为默认配置，验证所有核心列恢复显示
