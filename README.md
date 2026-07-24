# Livzon Syntpharm ERP System

原料药厂 ERP 管理系统，包含后端（Python/FastAPI）、前端（Next.js）和基础设施配置。

面向丽珠合成制药厂，覆盖生产、质量、安全、人事等核心业务模块。


## 业务模块

| 模块 | 后端 | 前端 |
|---|---|---|
| **Production** | 批次管理、工序记录、物料平衡 | 批次管理、工序记录、物料平衡 |
| **Equipment** | 设备台账、保养维修、巡检、备件 | 设备台账、保养维修、巡检、备件 |
| **Safety** | 隐患辨识、风险管控、特种作业 | 隐患辨识、风险管控、特种作业 |
| **Energy** | 设备监控、告警、采集日志 | 设备监控、告警、采集日志 |
| **Quality** | 偏差管理、CAPA、工艺验证 | 偏差管理、CAPA、工艺验证 |
| **HR** | 员工档案、入职培训、考勤 | 员工档案、入职培训、考勤 |
| **Registration** | Dossier 编写、法规追踪、补充答复 | Dossier 编写、法规追踪、补充答复 |
| **Research** | 实验管理、贝叶斯优化、ICH 分析 | 实验管理、贝叶斯优化、ICH 分析 |
| **Administration** | 系统设置、车辆管理 | 系统设置、车辆管理 |
| **Procurement** | 采购管理、合同生成 | 采购管理 |
| **Environment** | 环境监测 | 环境监测 |
| **Warehouse** | 仓库管理、库存 | 仓库管理 |


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


## 仓库结构

```
Livzon-Syntpharm/
├── backend/              # Python FastAPI 后端
│   ├── app/
│   │   ├── core/         # 基础设施（配置、数据库、Redis、异常、响应）
│   │   ├── shared/       # 跨模块契约（ORM 基类、模块注册表）
│   │   ├── platform/     # 平台能力（审计、身份、外部集成）
│   │   ├── modules/      # 业务模块
│   │   └── api/router.py # 全局路由
│   ├── alembic/          # 数据库迁移
│   ├── tests/            # 测试
│   └── scripts/          # 工具脚本
├── frontend/             # Next.js 前端
│   └── src/
│       ├── app/          # 路由页面
│       ├── components/   # UI 组件
│       ├── actions/      # Server Actions
│       ├── stores/       # Zustand 状态管理
│       ├── lib/          # 工具函数和 API 封装
│       └── types/        # TypeScript 类型
├── nginx/
│   └── default.conf      # Nginx 反向代理配置
├── docker-compose.yml    # 生产环境编排
├── docker-compose.dev.yml # 开发环境覆盖
├── .env.example          # 环境变量模板
└── AGENTS.md             # AI 编码规范
```


## 部署

所有服务通过 Docker Compose 运行。

### 快速开始

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入实际值

# 2. 生产环境
docker compose up -d --build

# 3. 开发环境（热更新）
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

### 访问地址

- **前端**: http://your-server-ip (Nginx 80 端口)
- **后端 API**: http://your-server-ip/api/v1/
- **API 文档**: http://your-server-ip/docs
- **MinIO 控制台**: http://your-server-ip:9001

### 服务列表

| 服务 | 容器名 | 端口 | 说明 |
|---|---|---|---|
| postgres | erp-postgres | 5432 | PostgreSQL 17 |
| redis | erp-redis | 6379 | Redis 缓存 |
| minio | erp-minio | 9000, 9001 | S3 兼容对象存储 |
| migrate | erp-migrate | - | 启动时执行数据库迁移 |
| backend | erp-backend | 8000 | FastAPI 后端 |
| edbo-service | erp-edbo-service | 8001 | EDBO 优化服务 |
| frontend | erp-frontend | 3000 | Next.js 前端 |
| nginx | erp-nginx | 80 | 反向代理 |

### 故障排查

```bash
docker compose ps                  # 容器状态
docker logs erp-backend            # 后端日志
docker logs erp-frontend           # 前端日志
docker compose restart backend     # 重启服务
docker stats                       # 资源使用
```


## 后端开发

### 环境要求

- Python >= 3.12
- Docker + Docker Compose（推荐）
- 本地开发可选：PostgreSQL 17、Redis、[uv](https://docs.astral.sh/uv/)

### 本地配置

```bash
cd backend
uv sync
cp ../.env.example .env  # 或直接设置环境变量

# 执行数据库迁移
uv run alembic upgrade head

# 启动开发服务器
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 测试与代码检查

```bash
uv run pytest                                    # 全部测试
uv run pytest tests/modules/<module>/            # 单模块
uv run pytest tests/modules/<module>/ -k "name"  # 单个用例

uv run ruff check .        # 代码检查
uv run ruff format .       # 代码格式化
uv run mypy app/           # 类型检查
```

### 数据库迁移

```bash
# 模型变更后创建迁移
uv run alembic revision --autogenerate -m "描述"

# 应用迁移
uv run alembic upgrade head

# 回滚
uv run alembic downgrade -1
```


## 前端开发

### 环境要求

- Node.js >= 22
- pnpm（见 package.json）

### 本地配置

```bash
cd frontend
pnpm install
pnpm dev --port 3000
```

开发服务器将 `/api/v1/*` 请求代理到后端 `http://localhost:8000`。

### 测试与代码检查

```bash
pnpm typecheck    # TypeScript 类型检查
pnpm lint         # ESLint
pnpm test:e2e     # Playwright E2E 测试
```

### API 类型

前端 API 类型通过后端 OpenAPI 规范自动生成：

```bash
# 在 backend/ 目录导出最新规范
uv run python scripts/ci/export_openapi.py

# 在 frontend/ 目录重新生成类型
cp ../backend/openapi.json src/types/generated/openapi.json
pnpm generate:api
```

生成的类型已提交至仓库，CI 会检查其是否与后端同步。


## 数据持久化

以下目录由运行时创建（未纳入 Git）：

- `postgres-data/` — PostgreSQL 数据
- `redis-data/` — Redis 数据
- `minio-data/` — MinIO 对象存储
- `uploads/` — 用户上传
- `storage/` — 应用存储
- `logs/` — 日志文件
- `backups/` — 数据库备份


## 注意事项

- 所有容器以分离模式运行（`-d`）
- 数据库迁移在后端启动时自动执行
- Nginx 代理前端和后端请求，避免 CORS 问题
- `.env` 包含敏感信息，切勿提交到 Git
- AI 编码规范：参见 [AGENTS.md](AGENTS.md)
