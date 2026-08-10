# 能源单耗智能分析功能 (V1) - TDD 记录

## Phase 1: RED (编写失败的测试)
- [x] 创建 Playwright 测试脚本 `frontend/tests/ai-analysis.spec.ts`
- [x] 定义验收标准：用户输入产量后，页面应显示实际单耗及 AI 建议。

## Phase 2: GREEN (实现功能使测试通过)
- [ ] 后端：实现 `POST /api/v1/energy/targets` 接口。
- [ ] 后端：修改 `POST /api/v1/energy/ai-analysis` 以支持 `manual_production` 参数。
- [ ] 前端：在 AI 分析页面增加“本期总产量”输入框。
- [ ] 前端：增加“设定单耗目标” Modal 弹窗。

## Phase 3: REFACTOR (优化与清理)
- [ ] 优化 AI Prompt，确保返回结构化 JSON。
- [ ] 清理前端冗余代码，统一 UI 样式。

## 验证状态
- [ ] DB→API→UI 全链路已通过 CI 验证。
- [ ] Playwright 浏览器自动化测试已通过。
