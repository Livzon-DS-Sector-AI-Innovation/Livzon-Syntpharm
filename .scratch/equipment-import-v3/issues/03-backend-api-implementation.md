# 03 — 后端 API 实现 (预览 + 批量导入)

**What to build:** 完成 `/preview` 和 `/batch` 接口的智能推断集成，支持部门 NULL 入库及 `technical_params` 存储。

**Blocked by:** 01, 02

**Status:** ready-for-agent

- [ ] `/preview` 接口响应包含 `equipment_class`, `importance`, `status`
- [ ] 响应中包含从 Excel 提取并存入 `technical_params` 的“数量”字段
- [ ] `/batch` 接口支持 `department_id` 为 NULL 的记录入库
- [ ] 数据库中 `category_description` 和 `technical_params` 字段值正确
- [ ] 导入成功率 > 95%，错误报告清晰
