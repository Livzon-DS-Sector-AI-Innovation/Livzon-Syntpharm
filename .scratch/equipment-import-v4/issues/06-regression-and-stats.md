# 06 — [QA] v3 隔离回归与导入结果统计卡片

**What to build:** 确保新功能不破坏旧逻辑，并向用户展示清晰的导入成果（仅计数）。

**Blocked by:** 02b — [Backend] 审计日志接线与 Force 标记, 05 — [Frontend] 重构 ImportCockpit 为全量字段动态表格

**Status:** ready-for-agent

- [ ] 运行 v3 导入流程，确认其行为未受 v4 代码影响
- [ ] 导入完成后显示统计卡片：创建/更新/跳过/错误数 + 批次 ID
