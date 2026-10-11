# 01 — 端到端最小闭环 (End-to-End Minimum Loop)

**What to build:** 
实现设备同步功能的最小可演示路径：
1. 后端增加 `POST /api/v1/equipment/sync-excel` 接口。
2. Service 层实现基础匹配逻辑：仅处理 `(asset_no, dept_id, loc_id)` 完全匹配的记录，执行全字段强制覆盖（含成本/净值）。
3. 前端在设备台账页增加“同步 Excel”按钮及文件上传组件。
4. 冻结 API 契约：响应体包含 `updated`, `inserted`, `migrated`, `deleted` 四个统计字段。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] 定义并实现 `sync_equipments_from_excel` Service 函数骨架。
- [ ] 实现基础匹配分支（Exact Match），确保关联数据（工单等）不被破坏。
- [ ] 完成 API 接口开发并返回基础统计数据。
- [ ] 前端集成上传组件，调用接口并展示 `updated` 计数。
- [ ] 验证上传真实 Excel 后，数据库财务数据已更新且历史业务记录完好。
