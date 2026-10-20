# 02 — [Backend] 完善导入引擎的边界处理逻辑

**What to build:** 针对已落地的核心逻辑进行补强，处理位号冲突、批量提交和空值转换。

**Blocked by:** 01 — [DB] 升级设备表唯一约束为四元组（含软删除）

**Status:** ready-for-agent

- [ ] 实现位号冲突检测（Tag Conflict）并返回 ERROR
- [ ] 实现每 100 条自动 Commit 的性能优化
- [ ] 实现 Excel 空字符串自动转换为 NULL 的逻辑
