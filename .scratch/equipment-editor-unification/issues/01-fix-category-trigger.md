# 01 — 修复分类新增按钮无反应问题

**What to build:** 重构 `CategoryTree`，将状态管理从 `CategoryEditor` 内部移至父组件，确保点击触发器能正确弹出编辑器。

**Blocked by:** None

**Status:** ready-for-agent

## Acceptance Criteria
- [ ] 移除 `CategoryEditor` 的 `trigger` 属性依赖
- [ ] 在 `CategoryTree` 中使用 `useState` 控制编辑器显隐
- [ ] 点击“新建分类”按钮后，编辑器立即弹出且输入框获得焦点
- [ ] 提交成功后自动关闭编辑器并刷新树形结构
