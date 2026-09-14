# 04 — [QA] 回归与无障碍验收

**What to build:** 作为最终的验收清单，确保空值处理、分页稳定性及屏幕阅读器兼容性。

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] 验证 NULL 值是否稳定排在列表末尾
- [ ] 检查表头的 `aria-sort` 属性是否随交互动态更新
- [ ] 确认 Offset 分页下的已知限制（数据变动导致的跨页抖动）已在文档中说明
