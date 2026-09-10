# 03 — 状态徽章可视化增强

**What to build:** 将设备状态从纯文字标签升级为带图标的彩色徽章，提升快速识别性。

**Blocked by:** 01 (需要先完成基础交互优化)

**Blocking:** None

**Status:** ready-for-agent

## Acceptance Criteria

- [ ] 创建 `StatusBadge` 组件，接收 `status: EquipmentStatus` 属性
- [ ] 根据状态映射显示不同的图标和颜色：
  - 在用：🟢 + 绿色背景 (#10b981) + 文字"运行中"
  - 备用：🔵 + 靛蓝背景 (#6366f1) + 文字"待命"
  - 维修中：🟠 + 橙色背景 (#f97316) + 文字"维护"
  - 停用：⚪ + 灰色背景 (#94a3b8) + 文字"离线"
  - 报废：🔴 + 红色背景 (#ef4444) + 文字"已报废"
- [ ] 徽章样式：圆角 pill 形状，内边距 4px 8px，字体大小 12px
- [ ] 替换 `EquipmentTable` 中的状态列渲染逻辑，使用新的 `StatusBadge` 组件

## Implementation Notes

- 定义 `statusBadgeMap` 常量对象，包含所有状态的配置
- 使用 inline style 或 CSS-in-JS 设置背景色和文字颜色
- 保持现有的 `statusPill` 函数作为 fallback，如果新组件未加载
- 文件修改：
  - 新增 `frontend/src/components/equipment/StatusBadge.tsx`
  - `frontend/src/components/equipment/EquipmentTable.tsx`

## Testing

- [ ] 手动测试：遍历所有状态，验证徽章颜色和图标正确
- [ ] 手动测试：验证徽章在不同背景下的可读性
