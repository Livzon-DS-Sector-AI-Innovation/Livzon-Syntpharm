# 03 — 导入 API 端点整合 (/preview & /batch)

**What to build:** 将核心逻辑引擎暴露给前端，提供预览和执行两个入口。API 需返回详细的匹配策略、验证警告及批次 ID，支持前端进行交互式确认。

**Blocked by:** 02 — 导入核心逻辑引擎 (Service Layer)

**Status:** ready-for-agent

- [ ] 重构 `/preview` 端点，返回包含匹配策略和重复标记的推断结果
- [ ] 重构 `/batch` 端点，接收完整数据数组并执行批量导入
- [ ] 实现每 100 条记录 commit 一次的性能优化逻辑
- [ ] 确保 API 响应中包含唯一的 `batch_id` 用于后续追踪
- [ ] 编写集成测试，验证从 API 请求到数据库状态变化的完整链路
