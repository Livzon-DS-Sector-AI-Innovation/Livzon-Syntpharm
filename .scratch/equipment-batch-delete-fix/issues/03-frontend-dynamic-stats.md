# 03 — 前端统计卡片动态反映筛选条件

**What to build:** 使顶部统计卡片（总数、在用、维修中等）能够根据当前筛选条件动态更新。当用户切换筛选条件或删除设备后，统计卡片立即显示筛选后的准确数据。

**Blocked by:** 01 — 修复单个删除后筛选失效问题, 02 — 后端统计 API 支持筛选参数

**Status:** ready-for-agent

- [ ] 修改 `fetchEquipmentStatisticsClient` 函数，接受筛选参数并传递给后端 API
- [ ] 修改 `EquipmentPage` 中的 `refreshStatistics` 函数，传递当前筛选条件（departmentFilter, selectedCategory, selectedLocation, statusFilter）
- [ ] 在筛选条件变化时自动调用 `refreshStatistics`
- [ ] 在删除操作（单个或批量）成功后调用 `refreshStatistics`
- [ ] 验证：按部门筛选后，统计卡片显示该部门的设备统计
- [ ] 验证：删除设备后，统计卡片立即更新
- [ ] 验证：切换筛选条件时，统计卡片平滑过渡到新值
