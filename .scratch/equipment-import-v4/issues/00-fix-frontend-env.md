# 00 — [Env] 修复前端构建环境并安装 pnpm

**What to build:** 解决服务器缺少 pnpm 的问题，确保前端项目能成功安装依赖并启动。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] 通过 corepack enable 或 npm i -g pnpm 安装 pnpm
- [ ] pnpm install 成功执行，node_modules 非空
- [ ] pnpm dev 能无报错启动前端服务
