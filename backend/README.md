# Dazah Backend

原料药事业部工厂数字化基座后端服务。

## 技术栈

- **Python 3.12+** + FastAPI
- **PostgreSQL 17** + Redis + MinIO
- **SQLAlchemy 2.0** (async) + Alembic (migrations)
- **Pydantic v2** for validation
- **uv** for package management

## 快速开始

### 环境要求

- Python >= 3.12
- Docker + Docker Compose（推荐）
- 或本地安装：PostgreSQL 17、Redis、[uv](https://docs.astral.sh/uv/)

### Docker 部署（推荐）

```bash
# 启动基础设施（数据库、Redis、MinIO）
docker compose up -d

# 启动后端应用
docker compose --profile app up -d

# 查看日志
docker compose logs -f app
```

访问 API 文档：http://localhost:8000/docs

### 本地开发

```bash
# 1. 安装依赖
uv sync

# 2. 安装 Playwright（法规追踪爬虫需要）
playwright install chromium

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入数据库和 Redis 连接信息

# 4. 数据库迁移
alembic upgrade head

# 5. 初始化数据（法规追踪模块）
python scripts/seed_regulatory_tracker.py
python scripts/seed_regulatory_documents.py

# 6. 启动服务
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 架构概览

模块化单体架构，各业务模块独立演进，共享平台基础设施：

```
app/
├── core/              # 基础设施（配置、数据库、Redis、异常、响应）
├── shared/            # 跨模块契约（ORM 基类、模块注册表）
├── platform/          # 平台能力（审计、身份、外部集成）
├── modules/           # 业务模块
│   ├── production/    # 生产管理
│   ├── equipment/     # 设备管理
│   ├── safety/        # 安全管理
│   ├── energy/        # 能源管理
│   ├── quality/       # 质量管理
│   ├── hr/            # 人事管理
│   ├── registration/  # 注册管理
│   ├── research/      # 研发管理
│   └── ...
└── api/router.py      # 全局路由
```

每个模块维护自己的 API 路由、Schema、Service、Repository 和 Model。

## 业务模块

| 模块 | 说明 |
|------|------|
| **Production** | 批次管理、工序记录、物料平衡 |
| **Equipment** | 设备台账、保养维修、巡检、备件 |
| **Safety** | 隐患辨识、风险管控、特种作业 |
| **Energy** | 设备监控、告警、采集日志 |
| **Quality** | 偏差管理、CAPA、工艺验证 |
| **HR** | 员工档案、入职培训、考勤 |
| **Registration** |  dossier 编写、法规追踪、补充答复 |
| **Research** | 实验管理、贝叶斯优化、ICH 分析 |

## 开发指南

```bash
# 运行测试
uv run pytest

# 代码检查
uv run ruff check .
uv run mypy app/

# 代码格式化
uv run ruff format .
```

### 数据库迁移

```bash
# 创建迁移（修改模型后）
alembic revision --autogenerate -m "description"

# 应用迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

## 前端集成

前端（`dazah-frontend/`）是 Next.js 应用，通过反向代理连接后端：

- **开发环境**：Next.js 代理转发 `/api/v1/*` 到后端
- **生产环境**：nginx 反向代理处理路由
- **API 路径**：所有端点在 `/api/v1/<module>/<resource>` 下

## 健康检查

```bash
curl http://localhost:8000/health
```

## 编码规范

详见 [AGENTS.md](AGENTS.md) — AI 编码助手必须遵守的规则。
