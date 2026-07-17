# Dazah Frontend

原料药厂管理系统前端 — Next.js 16 + TypeScript + Ant Design。

## 技术栈

- **Next.js 16** + React 19 + TypeScript
- **Ant Design V6**（antd）组件库
- **Tailwind CSS** 工具样式
- **Zustand** 客户端状态管理
- **React Query** 服务端数据请求
- **React Hook Form** + **Zod** 表单校验

## 快速开始

### Docker 开发（推荐）

```bash
# 启动开发服务器（热更新）
docker compose -f docker-compose.dev.yml up -d --build
```

访问 http://localhost:3000

### 本地开发

```bash
# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev --port 3000
```

## 架构概览

```
src/
├── app/(dashboard)/     # 路由页面（Server Component）
├── components/          # UI 组件（按模块组织）
├── actions/             # Server Actions（写操作）
├── stores/              # Zustand stores（客户端状态）
├── types/               # TypeScript 类型定义
├── lib/                 # 工具函数和 API 封装
└── proxy.ts             # API 代理到后端
```

核心原则：
- 页面是 Server Component，负责获取数据并传给 Client Component
- 写操作（POST/PUT/DELETE）使用 Server Actions
- 每个模块有独立的目录边界，通过 `index.ts` 导出
- 需要交互的组件加 `'use client'` 指令

## 业务模块

| 模块 | 说明 |
|------|------|
| **Production** | 批次管理、工序记录、物料平衡 |
| **Equipment** | 设备台账、保养维修、巡检、备件 |
| **Safety** | 隐患辨识、风险管控、特种作业 |
| **Energy** | 设备监控、告警、采集日志 |
| **Quality** | 偏差管理、CAPA、工艺验证 |
| **HR** | 员工档案、入职培训、考勤 |
| **Registration** | Dossier 编写、法规追踪、补充答复 |
| **Research** | 实验管理、贝叶斯优化、ICH 分析 |

## API 集成

前端连接 `dazah-backend`（FastAPI）：

- **客户端代码**：使用相对路径 `/api/v1/...`（自动代理）
- **服务器端代码**：使用 `API_BASE_URL` 环境变量
- **开发环境**：Next.js 代理转发到后端 8000 端口
- **生产环境**：nginx 反向代理处理路由

## 设计系统

UI 组件遵循 [DESIGN.md](DESIGN.md) 中的设计规范 — 包含色彩、字体、间距和基于 Ant Design V6 的组件规格。

## 编码规范

详见 [AGENTS.md](AGENTS.md) — AI 编码助手必须遵守的规则。

## 健康检查

```bash
curl http://localhost:3000
```
