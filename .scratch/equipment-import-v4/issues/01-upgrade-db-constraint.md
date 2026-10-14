# 01 — [DB] 升级设备表唯一约束为四元组（含软删除）

**What to build:** 数据库层面的基础保障。将唯一索引升级为 (asset_no, department_id, location_text, is_deleted)，确保软删除记录不占用业务唯一性。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] 迁移脚本执行成功，约束包含 is_deleted 字段
- [ ] 验证软删除后的资产编号可以重新录入新位置
