# 01 — 空状态引导与新建按钮可见性增强

**What to build:** 当分类树或位置树为空时，显示带说明文字和 CTA 按钮的引导式空状态；同时增强"新建分类/位置"按钮的视觉权重。

**Blocked by:** None — can start immediately

**Blocking:** 02, 03, 04, 05 (所有后续优化依赖基础交互完善)

**Status:** ready-for-agent

## Acceptance Criteria

- [ ] `CategoryTree` 组件在 `categories.length === 0` 时显示空状态卡片
- [ ] 空状态卡片包含：
  - 标题："暂无设备分类"
  - 说明文字："分类用于设备类型管理和统计分析。请先创建分类体系，以便对设备进行标准化管理。"
  - CTA 按钮："创建第一个分类"（点击打开 CategoryEditor）
- [ ] `LocationTree` 组件在 `locations.length === 0` 时显示类似空状态
- [ ] "新建分类"按钮从原来的小号虚线按钮升级为 primary 类型的小号按钮
- [ ] 按钮旁边添加 InfoCircle 图标，hover 时显示工具提示解释业务价值
- [ ] 工具提示内容："分类用于设备类型管理和统计分析。例如：生产设备、辅助设备。"

## Implementation Notes

- 复用 Ant Design 的 `<Empty>` 组件，自定义 `description` 属性
- 使用 `<Tooltip>` 包裹 InfoCircle 图标
- 保持现有 `CategoryEditor` 逻辑不变，仅调整触发按钮样式
- 文件修改：
  - `frontend/src/components/equipment/CategoryTree.tsx`
  - `frontend/src/components/equipment/LocationTree.tsx`

## Testing

- [ ] 手动测试：清空分类数据，验证空状态显示
- [ ] 手动测试：点击"创建第一个分类"，验证 CategoryEditor 打开
- [ ] 手动测试：hover InfoCircle 图标，验证工具提示显示
