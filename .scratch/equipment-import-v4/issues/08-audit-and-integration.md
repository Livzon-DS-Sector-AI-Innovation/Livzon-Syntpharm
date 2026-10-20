# 08 — 审计日志标记与集成验证

**What to build:** 完善强制覆盖操作的审计追踪，并通过端到端测试确保功能在不同场景下的数据一致性。

**Blocked by:** 06 — 后端 API 与核心逻辑支持, 07 — 前端交互 UI 与警示设计

**Status:** ready-for-agent

- [ ] 在 `import_audit_logs` 的 `changes` 字段中增加 `"override_type": "force"` 标记
- [ ] 编写集成测试：验证保护模式下手动修正的部门不被覆盖
- [ ] 编写集成测试：验证强制模式下所有匹配设备的业务字段均被 Excel 数据替换
- [ ] 验证审计日志中强制覆盖记录的完整性
