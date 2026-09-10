# 01 — 修复单个删除后筛选失效问题

**What to build:** 修复通过表格行"删除"按钮删除设备后，筛选条件丢失导致显示全厂设备的问题。确保删除操作后列表仍保持在当前筛选条件下，分页功能正常工作。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] 移除 `EquipmentTable` 组件中 `handleDelete` 函数的 `useCallback` 包装
- [ ] 验证：在筛选状态下删除单个设备后，列表仍只显示符合筛选条件的设备
- [ ] 验证：删除后分页按钮正确显示/隐藏
- [ ] 验证：筛选栏的选中状态保持不变
