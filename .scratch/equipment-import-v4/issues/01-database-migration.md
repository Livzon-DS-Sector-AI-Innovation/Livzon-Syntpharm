# 01 — 数据库架构迁移与模型同步

**What to build:** 完成设备批量导入 v4 所需的数据库结构变更，包括新增固定资产标记字段、设备位号唯一约束以及审计日志表，并同步更新后端的 SQLAlchemy 模型。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] 在 `equipment.equipments` 表中添加 `is_fixed_asset` 布尔字段（默认 true）
- [ ] 为现有 `asset_no IS NULL` 的记录批量设置 `is_fixed_asset = false`
- [ ] 为 `equipment_tag` 创建部分唯一索引 `uq_equipments_equipment_tag`
- [ ] 创建 `equipment.import_audit_logs` 表及其索引
- [ ] 更新 `models/equipment.py` 添加 `is_fixed_asset` 映射
- [ ] 创建 `models/import_audit.py` 定义审计日志模型
