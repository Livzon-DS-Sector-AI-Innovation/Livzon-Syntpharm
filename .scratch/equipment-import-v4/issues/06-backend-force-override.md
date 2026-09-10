# 06 — 后端 API 与核心逻辑支持

**What to build:** 扩展批量导入 API，使其支持“强制覆盖业务字段”模式。当用户勾选该选项时，系统应忽略保护性更新逻辑，直接以 Excel 数据覆盖数据库中的部门和位置信息。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] 在 `POST /api/v1/equipment/import/batch` 请求体中增加 `force_override_business_fields` 布尔字段
- [ ] 修改 `apply_incremental_update` 函数，增加 `force_override` 参数分支
- [ ] 确保在强制模式下，B类字段（`department_id`, `location_text`）即使已有值也会被更新
- [ ] 编写单元测试验证两种模式下的更新行为差异
