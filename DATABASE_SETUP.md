# 数据库环境搭建指南

本项目使用 **PostgreSQL** 作为数据库，**Redis** 作为缓存。以下说明帮助新成员快速搭建本地开发环境。

---

## 前置条件

- [Docker Desktop](https://www.docker.com/products/docker-desktop)（推荐，一键启动）
- 或自行安装 [PostgreSQL 17](https://www.postgresql.org/download/) + [Redis](https://redis.io/downloads/)

---

## 方式一：Docker 一键启动（推荐）

项目已提供 `docker-compose.yml`，包含 PostgreSQL 和 Redis 服务。

### 1. 启动数据库服务

```bash
cd dazah-backend
docker compose up db redis -d
```

> `-d` 表示后台运行。首次启动会自动拉取镜像并创建数据库。

### 2. 检查服务是否就绪

```bash
docker compose ps
```

看到 `db` 和 `redis` 状态为 `healthy` 即可继续。

### 3. 安装 Python 依赖

```bash
uv sync
```

### 4. 运行数据库迁移（创建表结构）

```bash
uv run alembic upgrade head
```

### 5. 导入种子数据（部门、班组等基础数据）

```bash
uv run python scripts/seed.py
```

### 6. 启动后端服务

```bash
uv run uvicorn app.main:app --reload
```

访问 http://localhost:8000/docs 查看 API 文档。

---

## 方式二：手动安装 PostgreSQL + Redis

如果不使用 Docker，请按以下步骤操作。

### 1. 安装 PostgreSQL 17

#### macOS
```bash
brew install postgresql@17
brew services start postgresql@17
```

#### Ubuntu / Debian
```bash
sudo apt update
sudo apt install postgresql-17
sudo systemctl start postgresql
```

#### Windows
下载安装包：https://www.postgresql.org/download/windows/

### 2. 创建数据库

```bash
# 以 postgres 用户登录
sudo -u postgres psql

# 在 psql 中执行
CREATE DATABASE dazah;
CREATE USER dazahuser WITH PASSWORD 'dazahpass';
GRANT ALL PRIVILEGES ON DATABASE dazah TO dazahuser;
\q
```

### 3. 安装 Redis

#### macOS
```bash
brew install redis
brew services start redis
```

#### Ubuntu / Debian
```bash
sudo apt install redis-server
sudo systemctl start redis-server
```

#### Windows
下载：https://github.com/microsoftarchive/redis/releases

### 4. 配置环境变量

在项目根目录创建 `.env` 文件：

```bash
cd dazah-backend
cp .env.example .env
```

编辑 `.env`，确保数据库连接地址正确：

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/dazah
REDIS_URL=redis://localhost:6379/0
```

如果使用上一步创建的用户名/密码，请相应修改：

```env
DATABASE_URL=postgresql+asyncpg://dazahuser:dazahpass@localhost:5432/dazah
```

### 5. 安装依赖并运行迁移

```bash
uv sync
uv run alembic upgrade head
```

### 6. 导入种子数据

```bash
uv run python scripts/seed.py
```

### 7. 启动服务

```bash
uv run uvicorn app.main:app --reload
```

---

## 关于员工数据

员工数据（`employees` 表）目前通过**飞书多维表格同步**拉取，需要配置以下环境变量：

```env
FEISHU_APP_ID=你的飞书应用ID
FEISHU_APP_SECRET=你的飞书应用密钥
FEISHU_BITABLE_APP_TOKEN=多维表格应用Token
FEISHU_BITABLE_EMPLOYEE_TABLE_ID=员工表ID
FEISHU_BITABLE_DEPARTMENT_TABLE_ID=部门表ID
```

配置完成后，调用同步接口即可导入员工数据。

如果没有飞书权限，员工表将保持为空，但部门和班组数据已通过种子脚本导入。

---

## 常用命令

| 命令 | 说明 |
|------|------|
| `uv run alembic upgrade head` | 执行所有迁移，更新到最新表结构 |
| `uv run alembic downgrade -1` | 回退一次迁移 |
| `uv run alembic revision --autogenerate -m "描述"` | 自动生成迁移脚本 |
| `uv run python scripts/seed.py` | 导入部门/班组种子数据 |
| `docker compose down` | 停止并删除 Docker 容器 |
| `docker compose down -v` | 停止并删除容器 + 数据卷（**会清空数据**） |

---

## 常见问题

### Q1: `alembic upgrade head` 报错 `database "dazah" does not exist`

**原因**：PostgreSQL 中没有创建 `dazah` 数据库。  
**解决**：手动创建数据库，或确保 Docker 的 `POSTGRES_DB` 环境变量正确。

### Q2: `seed.py` 报错 `relation "departments" does not exist`

**原因**：还没有运行 Alembic 迁移，表不存在。  
**解决**：先执行 `uv run alembic upgrade head`，再运行种子脚本。

### Q3: Docker 启动后数据丢失了

**原因**：使用了 `docker compose down -v`，删除了数据卷。  
**解决**：正常停止用 `docker compose down`（不加 `-v`）。数据保存在 Docker 卷 `pgdata` 中，不会丢失。

### Q4: 提示 `password authentication failed`

**原因**：`.env` 中的数据库用户名/密码与 PostgreSQL 中配置的不一致。  
**解决**：检查 `.env` 的 `DATABASE_URL`，确保用户名、密码、数据库名正确。

---

## 数据库架构说明

| Schema | 说明 |
|--------|------|
| `hr` | 人事模块（部门、班组、员工、离职记录） |
| `equipment` | 设备模块（设备台账、校准、工单、故障代码） |
| `identity` | 身份认证（用户、角色） |
| `audit` | 审计日志 |

每个业务模块使用独立的 PostgreSQL Schema 做边界隔离。
