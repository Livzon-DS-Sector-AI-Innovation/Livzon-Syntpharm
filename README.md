# Livzon Syntpharm ERP System

原料药厂 ERP 管理系统，包含后端（Python/FastAPI）、前端（Next.js）和基础设施配置。

## 仓库结构

```
Livzon-Syntpharm/
├── backend/              # Python FastAPI 后端
├── frontend/             # Next.js 前端
├── nginx/
│   └── default.conf      # Nginx 反向代理配置
├── docker-compose.yml    # Docker 编排配置
├── .env.example          # 环境变量模板（复制为 .env 并填写真实值）
└── .gitignore
```

## 子项目说明

### Backend (`backend/`)

- **技术栈**：Python 3.12+、FastAPI、SQLAlchemy 2.0 async、PostgreSQL 17、Redis、Alembic、MinIO
- **架构**：模块化单体架构
- **编程规范**：见 `backend/AGENTS.md`

### Frontend (`frontend/`)

- **技术栈**：Next.js 16、React 19、TypeScript、Tailwind CSS、Ant Design V6
- **状态管理**：Zustand（客户端）、React Query（服务端数据）
- **编程规范**：见 `frontend/AGENTS.md`

## 部署

所有服务通过 Docker Compose 运行。

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填写真实的数据库密码、API Key、飞书应用凭证等
```

### 2. 构建镜像

```bash
docker compose build
```

### 3. 启动服务

```bash
docker compose up -d
```

服务启动后：
- **前端**：http://your-server-ip（Nginx 端口 80）
- **后端 API**：http://your-server-ip/api/v1/
- **FastAPI 文档**：http://your-server-ip/docs
- **MinIO 控制台**：http://your-server-ip:9001

### 4. 查看状态

```bash
docker compose ps
docker compose logs -f
```

### 5. 停止服务

```bash
docker compose down
```

## 服务说明

| 服务 | 容器名 | 端口 | 说明 |
|------|--------|------|------|
| postgres | erp-postgres | 5432 | PostgreSQL 17 数据库 |
| redis | erp-redis | 6379 | Redis 缓存 |
| minio | erp-minio | 9000, 9001 | 对象存储（S3 兼容） |
| migrate | erp-migrate | - | 数据库迁移（启动时运行） |
| backend | erp-backend | 8000 | FastAPI 后端 |
| edbo-service | erp-edbo-service | 8001 | EDBO 服务 |
| frontend | erp-frontend | 3000 | Next.js 前端 |
| nginx | erp-nginx | 80 | 反向代理 |

## 数据持久化

以下目录在运行时创建，不在 Git 仓库中：

- `postgres-data/` — PostgreSQL 数据
- `redis-data/` — Redis 数据
- `minio-data/` — MinIO 对象存储数据
- `uploads/` — 用户上传文件
- `storage/` — 应用存储
- `logs/` — 日志文件
- `backups/` — 数据库备份

## 故障排查

```bash
# 查看容器状态
docker compose ps

# 查看特定服务日志
docker logs erp-backend
docker logs erp-frontend

# 重启单个服务
docker compose restart backend

# 查看资源使用
docker stats
```

## 开发

### Backend 开发

```bash
cd backend
# 参考 backend/AGENTS.md 和 backend/docs/development-guide.md
```

### Frontend 开发

```bash
cd frontend
# 参考 frontend/AGENTS.md
# 开发环境使用 docker-compose.dev.yml
docker compose -f docker-compose.dev.yml up -d --build
```

## 注意事项

- 所有容器以 detached 模式运行（`-d`），SSH 断开后继续运行
- 数据库迁移在启动时自动运行
- Nginx 代理前端和后端请求，避免 CORS 问题
- `.env` 文件包含敏感信息，**不要提交到 Git**
