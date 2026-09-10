# 02 — 导入核心逻辑引擎 (Service Layer)

**What to build:** 实现设备导入的“大脑”，包含四级匹配策略、选择性更新逻辑、重复检测及审计记录功能。该模块应独立于 API 层，确保业务逻辑的纯净和可测试性。

**Blocked by:** 01 — 数据库架构迁移与模型同步

**Status:** ready-for-agent

- [ ] 实现 `find_existing_equipment` 函数（复合→位号→模糊→创建）
- [ ] 实现 Excel 内部重复检测逻辑（基于 asset_no + dept + location）
- [ ] 实现增量更新策略：A类字段总是更新，B类字段仅 NULL 时更新
- [ ] 实现位号冲突检测与部分成功处理逻辑
- [ ] 实现 `log_audit` 函数，记录完整的变更详情和警告信息
- [ ] 编写核心逻辑的单元测试，覆盖各种匹配和更新场景
