# Livzon Syntpharm ERP System

原料药厂 ERP 管理系统，替代旧系统，为 GMP 合规提供集成数据管理。

## 技术栈

### 后端
- **Python 3.12+** + FastAPI
- **PostgreSQL 17** + Redis + MinIO (S3 兼容对象存储)
- **SQLAlchemy 2.0** (async) + Alembic (数据库迁移)
- **Pydantic v2** 数据校验
- **uv** 包管理
- PaddleOCR 文档解析

### 前端
- **Next.js 16** + React 19 + TypeScript
- **Ant Design V6** 组件库
- **Tailwind CSS** 工具样式
- **Zustand** 客户端状态管理
- **React Query** 服务端数据请求
- **pnpm** 包管理

## Prerequisites

- Ubuntu 22.04+ (or any Linux distribution that supports Docker)
- Docker + Docker Compose
- Git

## 部署

### 快速开始

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入实际值

# 2. 启动所有服务
docker compose up -d --build
```

### 访问地址

- **前端**: http://your-server-ip (Nginx 80 端口)
- **后端 API**: http://your-server-ip/api/v1/
- **API 文档**: http://your-server-ip/docs
- **MinIO 控制台**: http://your-server-ip:9001

## 开发

```bash
# 后端开发服务器
cd backend && uv run uvicorn app.main:app --reload

# 前端开发服务器
cd frontend && pnpm dev
```

更多开发信息（测试、迁移、API 类型生成等）请参考 [backend/docs/development-guide.md](backend/docs/development-guide.md)。
