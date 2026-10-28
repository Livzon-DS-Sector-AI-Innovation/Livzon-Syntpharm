# 04 — [Frontend] 接入 ForceOverrideToggle 并修正安全默认值

**What to build:** 将组件集成到 UI，并修复后端默认值过高的安全隐患。

**Blocked by:** 00 — [Env] 修复前端构建环境并安装 pnpm

**Status:** ready-for-agent

- [ ] 用户在预览界面能看到开关，且默认为未勾选状态
- [ ] 修正后端 /batch 与 /preview 的 force_override 默认值为 false
- [ ] 开关状态能正确传递给后端接口
