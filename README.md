# Livzon Syntpharm ERP System

原料药厂 ERP 管理系统。

## 系统模块

生产管理、设备管理、安全管理、环保管理、能源管理、仓储管理、采购管理、行政管理、人事管理、研发管理、注册管理、质量管理。

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

## 环境要求

- Ubuntu 20+（或其他支持 Docker 的 Linux 发行版）
- Docker + Docker Compose
- Git

## 部署

### 第一步：准备 Ubuntu 系统

1. 准备一台服务器或虚拟机，安装 Ubuntu 20 LTS 或更高版本
2. 确保系统已更新：
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

### 第二步：安装 Docker

1. 安装 Docker：
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   ```

2. 将当前用户添加到 docker 组（避免每次都要 sudo）：
   ```bash
   sudo usermod -aG docker $USER
   ```

3. 重新登录或执行 `newgrp docker` 使组权限生效

4. 验证 Docker 安装：
   ```bash
   docker --version
   docker compose version
   ```

### 第三步：获取代码仓库

1. 安装 Git（如果未安装）：
   ```bash
   sudo apt install git -y
   ```

2. 克隆项目代码：
   ```bash
   git clone https://github.com/Livzon-DS-Sector-AI-Innovation/Livzon-Syntpharm.git
   cd Livzon-Syntpharm
   ```

### 第四步：配置环境变量

1. 复制环境变量模板：
   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env` 文件，填入实际配置值：
   ```bash
   nano .env
   ```
   
   需要配置的关键项：
   - 数据库密码（POSTGRES_PASSWORD）
   - MinIO 访问密钥（MINIO_ROOT_USER、MINIO_ROOT_PASSWORD）
   - 其他服务配置

### 第五步：构建并启动容器

1. 构建并启动所有服务（首次运行会下载镜像，可能需要几分钟）：
   ```bash
   docker compose up -d --build
   ```

2. 查看容器状态：
   ```bash
   docker compose ps
   ```
   
   所有服务应显示 "Up" 状态。

3. 查看日志（可选）：
   ```bash
   docker compose logs -f
   ```
   
   按 `Ctrl+C` 退出日志查看。

### 第六步：访问系统

等待所有服务启动完成后（通常需要 1-2 分钟），通过浏览器访问：

- **前端界面**: http://服务器IP地址
- **后端 API**: http://服务器IP地址/api/v1/
- **API 文档**: http://服务器IP地址/docs
- **MinIO 控制台**: http://服务器IP地址:9001

如果是本地部署，使用 `http://localhost` 或 `http://127.0.0.1`。

## 开发

### 个人开发启动模式

本地启动完整环境（基础设施 + 前后端），使用 `docker-compose.yml` + `docker-compose.dev.yml`（源码挂载 + 前后端热重载），数据与 UAT 完全隔离。

```bash
# 1. 从 main 拉分支
git checkout main && git pull origin main
git checkout -b feature/你的功能名

# 2. 配置本地环境
cp .env.dev.example .env
# 编辑 .env，按需填写:
#   - 飞书应用凭证（FEISHU__*__APP_ID / APP_SECRET，不用飞书功能可留空）
#   - AI API Keys（如需要）
#   - BOOTSTRAP_ADMIN_USERNAME/PASSWORD（首次创建管理员账号）

# 3. 一键启动（自动执行迁移 + 首次写入种子数据）
bash scripts/dev.sh

# 4. 访问
# 前端: http://localhost:3000
# 后端: http://localhost:8000/docs
# MinIO 控制台: http://localhost:9001
```

**与 UAT 完全隔离**：PostgreSQL/Redis/MinIO/EDBO 均在本地容器运行，数据落在 `./postgres-data`、`./redis-data`、`./minio-data`，做 migration、灌测试数据都不影响 UAT 和其他开发者。

**重置本地数据**（清空数据库/缓存/对象存储，恢复初始状态；数据为挂载目录，需手动删除）：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
rm -rf postgres-data redis-data minio-data
```

**首次初始化**（`bash scripts/dev.sh` 已自动完成，手动步骤如下）：

```bash
# 1. 数据库迁移（up 时自动执行；手动则用下面的命令）
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm migrate

# 2. 模块设置种子数据（新库为空，不执行则各模块功能开关/模型配置为空）
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend \
  uv run python scripts/seed/seed_module_settings.py

# 3. 管理员账号: .env 填写 BOOTSTRAP_ADMIN_USERNAME/PASSWORD 后重启 backend
docker compose -f docker-compose.yml -f docker-compose.dev.yml restart backend
```

**配置文件**：`.env.dev.example`（本地开发模板；生产环境用 `.env.example`）

**注意**：
- 飞书多维表格同步、飞书 WS、LLM/OCR 等外部服务仍连接真实服务；本地默认已关闭 WS 与自动同步（`*_WS_ENABLED=false`、`ENERGY_AUTO_COLLECT_ENABLED=false`、`MAINTENANCE_PLAN_AUTO_ENABLED=false`），避免本地操作产生外部副作用
- 如宿主机 80 端口被占用，可跳过 nginx：`bash scripts/dev.sh` 命令加 `--scale nginx=0`（或手动 `up -d --scale nginx=0`）

### UAT 启动模式

在 UAT 服务器上部署完整环境（包含所有基础设施）。

```bash
# 1. 配置 UAT 环境
cp .env.uat.example .env.uat
# 编辑 .env.uat，填写所有 <从团队获取> 的占位符

# 2. 启动完整环境（基础设施 + 应用服务）
docker compose --env-file .env.uat -f docker-compose.uat-infra.yml -f docker-compose.uat.yml up -d --build

# 3. 执行数据库迁移（首次启动或 model 变更后）
docker compose --env-file .env.uat -f docker-compose.uat-infra.yml -f docker-compose.uat.yml run --rm migrate

# 4. 访问
# 前端: http://<服务器IP或域名>
# 后端: http://<服务器IP或域名>/api/v1/
```

**配置文件**：`.env.uat.example`（UAT 服务器专用）

**说明**：
- `docker-compose.uat-infra.yml` - 基础设施层（PostgreSQL/Redis/MinIO）
- `docker-compose.uat.yml` - 应用层（backend/frontend/migrate/nginx）
- 两个文件必须一起使用，应用层依赖基础设施层的健康检查

### 开发流程

```
main 拉 feature → 修改 → 合并 uat → 测试 → 创建 PR → 合并 main → 新版本生成
```

1. 从 `main` 拉分支开发
2. 完成后合并到 `uat` 测试
3. UAT 验证通过后，创建 PR 合并到 `main`

### 本地直接启动（不用 Docker）

如果已在本地安装好 Python 和 Node.js 环境，也可以直接启动：

```bash
# 后端开发服务器
cd backend && uv run uvicorn app.main:app --reload

# 前端开发服务器
cd frontend && pnpm dev
```

更多开发信息（测试、迁移、API 类型生成等）请参考 [backend/docs/development-guide.md](backend/docs/development-guide.md)。
