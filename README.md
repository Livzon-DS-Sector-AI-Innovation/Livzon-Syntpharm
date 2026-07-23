# Livzon Syntpharm ERP System

原料药厂 ERP 管理系统，包含后端（Python/FastAPI）、前端（Next.js）和基础设施配置。

面向丽珠合成制药厂，覆盖生产、质量、安全、人事等核心业务模块。



## Business Modules

| Module | Backend | Frontend |
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


## Tech Stack

### Backend
- **Python 3.12+** + FastAPI
- **PostgreSQL 17** + Redis + MinIO (S3 兼容对象存储)
- **SQLAlchemy 2.0** (async) + Alembic (migrations)
- **Pydantic v2** for validation
- **uv** for package management
- PaddleOCR for document parsing

### Frontend
- **Next.js 16** + React 19 + TypeScript
- **Ant Design V6** 组件库
- **Tailwind CSS** 工具样式
- **Zustand** 客户端状态管理
- **React Query** 服务端数据请求
- **pnpm** for package management


## Repository Structure

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


## Deployment

All services run via Docker Compose.

### Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with real values

# 2. Production
docker compose up -d --build

# 3. Development (hot-reload)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

### Access Points

- **Frontend**: http://your-server-ip (Nginx port 80)
- **Backend API**: http://your-server-ip/api/v1/
- **API Docs**: http://your-server-ip/docs
- **MinIO Console**: http://your-server-ip:9001

### Services

| Service | Container | Port | Description |
|---|---|---|---|
| postgres | erp-postgres | 5432 | PostgreSQL 17 |
| redis | erp-redis | 6379 | Redis cache |
| minio | erp-minio | 9000, 9001 | S3-compatible object storage |
| migrate | erp-migrate | - | Runs DB migrations on startup |
| backend | erp-backend | 8000 | FastAPI backend |
| edbo-service | erp-edbo-service | 8001 | EDBO optimization service |
| frontend | erp-frontend | 3000 | Next.js frontend |
| nginx | erp-nginx | 80 | Reverse proxy |

### Troubleshooting

```bash
docker compose ps                  # container status
docker logs erp-backend            # backend logs
docker logs erp-frontend           # frontend logs
docker compose restart backend     # restart service
docker stats                       # resource usage
```

## Backend Development

### Prerequisites

- Python >= 3.12
- Docker + Docker Compose (recommended)
- Or local: PostgreSQL 17, Redis, [uv](https://docs.astral.sh/uv/)

### Local Setup

```bash
cd backend
uv sync
cp ../.env.example .env  # or set env vars directly

# Database migration
uv run alembic upgrade head

# Start dev server
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing & Linting

```bash
uv run pytest                                    # all tests
uv run pytest tests/modules/<module>/            # single module
uv run pytest tests/modules/<module>/ -k "name"  # single test

uv run ruff check .        # lint
uv run ruff format .       # format
uv run mypy app/           # type check
```

### Database Migrations

```bash
# Create migration after model changes
uv run alembic revision --autogenerate -m "description"

# Apply
uv run alembic upgrade head

# Rollback
uv run alembic downgrade -1
```

## Frontend Development

### Prerequisites

- Node.js >= 22
- pnpm (specified in package.json)

### Local Setup

```bash
cd frontend
pnpm install
pnpm dev --port 3000
```

The dev server proxies `/api/v1/*` to the backend at `http://localhost:8000`.

### Testing & Linting

```bash
pnpm typecheck    # TypeScript type check
pnpm lint         # ESLint
pnpm test:e2e     # Playwright E2E tests
```

### API Types

Frontend API types are generated from the backend OpenAPI spec:

```bash
# In backend/:
uv run python scripts/ci/export_openapi.py

# In frontend/:
cp ../backend/openapi.json src/types/generated/openapi.json
pnpm generate:api
```

Generated types are committed to the repo and checked in CI.

## Data Persistence

The following directories are created at runtime (not in Git):

- `postgres-data/` — PostgreSQL data
- `redis-data/` — Redis data
- `minio-data/` — MinIO object storage
- `uploads/` — User uploads
- `storage/` — Application storage
- `logs/` — Log files
- `backups/` — Database backups

## Notes

- All containers run in detached mode (`-d`)
- Database migrations run automatically on backend startup
- Nginx proxies frontend and backend requests, avoiding CORS issues
- `.env` contains sensitive information — never commit to Git
- AI coding standards: see [AGENTS.md](AGENTS.md)
