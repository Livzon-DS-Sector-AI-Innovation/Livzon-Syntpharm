# 04 — 统计卡片移到顶部

**What to build:** 将 StatsCards 从表格上方移到页面顶部，作为第一眼信息展示。

**Blocked by:** 01 (需要先完成基础交互优化)

**Blocking:** None

**Status:** ready-for-agent

## Acceptance Criteria

- [ ] 修改 `EquipmentPage.tsx` 布局结构
- [ ] 将 `<StatsCards>` 组件移到标题下方、主内容区上方
- [ ] 统计卡片横向排列，占据全宽
- [ ] 移除原来在表格上方的折叠按钮旁边的紧凑版统计卡片
- [ ] 保持统计数据实时更新（通过 refreshStatistics 回调）

## Implementation Notes

- 调整 flex 布局：顶部 stats → 下方左右分栏（左侧筛选器 + 右侧表格）
- 确保 StatsCards 响应式：在小屏幕上自动换行
- 保留原有的 `compact` 属性逻辑，但在新位置可能不需要紧凑模式
- 文件修改：
  - `frontend/src/components/equipment/EquipmentPage.tsx`

## Testing

- [ ] 手动测试：验证统计卡片在顶部正确显示
- [ ] 手动测试：缩小浏览器窗口，验证响应式布局
- [ ] 手动测试：验证统计数据随后端更新而变化
