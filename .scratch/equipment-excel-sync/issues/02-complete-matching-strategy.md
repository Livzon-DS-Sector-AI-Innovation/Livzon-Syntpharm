# 02 — 补全匹配策略 (Complete Matching Strategy)

**What to build:** 
完善 Service 层的复杂匹配逻辑，实现真正的智能同步：
1. **资产迁移 (Migrate)**：当 `asset_no` 存在但位置/部门变动时，更新旧记录。
2. **新增 (Insert)**：Excel 中有但数据库中完全没有的记录。
3. **软删除 (Soft Delete)**：数据库活跃但 Excel 中消失的记录，标记为 `is_deleted=true`。
4. **事务原子性**：确保所有操作在一个事务中完成，失败则整体回滚。
5. **性能优化**：使用批量 UPDATE 语句处理近 3000 条记录。

**Blocked by:** 01 — 端到端最小闭环

**Status:** ready-for-agent

- [ ] 实现基于 `asset_no` 的 fallback 匹配逻辑。
- [ ] 实现软删除逻辑，并增加缺行阈值熔断保护（如缺行 > 5% 拒绝执行）。
- [ ] 增加 Excel 内部重复 `asset_no` 的校验，冲突则整批报错。
- [ ] 编写单元测试覆盖四类场景（更新、迁移、新增、停用）。
- [ ] 验证中途失败时的数据库回滚机制。
