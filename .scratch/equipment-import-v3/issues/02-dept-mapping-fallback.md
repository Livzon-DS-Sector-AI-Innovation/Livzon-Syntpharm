# 02 — 部门映射增强与降级逻辑实现

**What to build:** 扩展部门映射表并实现“匹配失败不跳过”的降级策略，解决数据丢失痛点。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] `DEPT_MAPPING_V3` 包含溶剂回收车间等新增部门
- [ ] `map_department_name_v3` 在查不到 ID 时返回 NULL 而非报错
- [ ] 预览接口能正确返回部门未匹配的 `warnings`
