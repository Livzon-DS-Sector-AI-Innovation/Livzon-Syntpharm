# Livzon Syntpharm ERP System

原料药厂 ERP 管理系统。

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

## 系统模块

| 模块 | 功能 |
|---|---|
| **生产管理** | 批次、工序、产量、生产过程记录等生产侧数据入口 |
| **设备管理** | 设备台账、保养、维修、巡检和备件关联数据入口 |
| **安全管理** | 隐患、作业票、风险点、培训和安全检查数据入口 |
| **环保管理** | 三废、监测、排放、环保设施运行和台账数据入口 |
| **能源管理** | 水、电、汽、冷量、能耗统计和能源指标数据入口 |
| **仓储管理** | 原辅料、包材、中间体、成品库存和出入库数据入口 |
| **采购管理** | 采购需求、供应商、询价、订单和到货协同数据入口 |
| **行政管理** | 行政事务、资产、后勤和公共服务事项数据入口 |
| **人事管理** | 人员、岗位、培训等人事业务数据入口 |
| **研发管理** | 研发项目、试验批、处方工艺和研发记录数据入口 |
| **注册管理** | 注册资料、申报进度、变更事项和法规跟踪数据入口 |
| **质量管理** | 偏差、CAPA、检验、放行、变更和质量体系数据入口 |

## 环境要求

- Ubuntu 22.04+（或其他支持 Docker 的 Linux 发行版）
- Docker + Docker Compose
- Git

## 部署

### 第一步：准备 Ubuntu 系统

1. 准备一台服务器或虚拟机，安装 Ubuntu 22.04 LTS 或更高版本
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

```bash
# 后端开发服务器
cd backend && uv run uvicorn app.main:app --reload

# 前端开发服务器
cd frontend && pnpm dev
```

更多开发信息（测试、迁移、API 类型生成等）请参考 [backend/docs/development-guide.md](backend/docs/development-guide.md)。
