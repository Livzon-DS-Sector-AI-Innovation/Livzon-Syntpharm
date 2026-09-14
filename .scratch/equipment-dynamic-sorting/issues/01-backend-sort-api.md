# 01 — [Backend] 列表 API 动态排序

**What to build:** 后端接口接收 `sort_by` 和 `order` 参数，通过白名单映射生成安全的 SQL 排序子句，并默认执行 `asset_no ASC NULLS LAST`。

**Blocked by:** None (API Contract is frozen in spec)

**Status:** ready-for-agent

- [ ] 修改 `repository/equipment.py`，增加参数校验与白名单映射逻辑
- [ ] 实现 SQL 层面的 `NULLS LAST` 处理
- [ ] 编写 Repo 层单元测试，验证不同排序组合下的 SQL 生成正确性
