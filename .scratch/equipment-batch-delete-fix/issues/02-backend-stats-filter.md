# 02 — 后端统计 API 支持筛选参数

**What to build:** 修改设备统计 API，使其能够根据传入的筛选参数（部门、位置、状态等）返回筛选后的统计数据，而不是始终返回全公司数据。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] 修改 `/api/v1/equipment/equipments/statistics` 端点，添加可选的筛选参数（category_id, location_id, department_id, status）
- [ ] 修改 Service 层 `get_equipment_statistics` 函数，接受并传递筛选参数
- [ ] 修改 Repository 层统计查询，根据筛选参数添加 WHERE 条件
- [ ] 验证：带筛选参数调用 API 时，返回的总数和各状态计数正确反映筛选结果
- [ ] 验证：不带筛选参数时，仍返回全局统计数据（向后兼容）
