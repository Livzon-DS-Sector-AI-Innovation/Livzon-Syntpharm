# 01 — 智能推断引擎单元测试

**What to build:** 验证核心业务逻辑（分类、重要性、状态）的推断准确性，确保后续集成的基础稳固。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] `test_infer_equipment_class` 覆盖 A/B/C 三类资产
- [ ] `test_infer_importance` 覆盖高/中/低三档成本分级
- [ ] `test_infer_status` 覆盖“未报废”到“在用”的映射
- [ ] 所有测试通过 `pytest`
