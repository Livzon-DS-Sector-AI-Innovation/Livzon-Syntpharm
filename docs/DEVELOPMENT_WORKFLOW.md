# 开发工作流优化指南

## 🎯 核心原则

**日常开发不要重新构建容器！** 使用热重载实现秒级反馈。

## 📋 工作流程

### 1. 日常开发（推荐）

```bash
# 首次启动（需要构建）
docker compose up -d

# 之后修改代码，自动生效，无需任何操作！
# - 后端：uvicorn --reload 自动检测变化
# - 前端：Next.js dev mode 自动编译
```

### 2. 依赖变化时

```bash
# Python 依赖变化（pyproject.toml 或 uv.lock）
docker compose build backend
docker compose up -d backend

# Node 依赖变化（package.json 或 pnpm-lock.yaml）
docker compose build frontend
docker compose up -d frontend
```

### 3. 数据库迁移时

```bash
# 运行迁移
docker exec erp-backend bash -c "cd /app && .venv/bin/alembic upgrade head"
```

### 4. 准备生产部署时

```bash
# 完整重新构建
docker compose build --no-cache
docker compose up -d
```

## ⚡ 快速命令参考

| 场景 | 命令 | 耗时 |
|------|------|------|
| 修改业务逻辑 | 直接保存文件 | 0s（自动重载） |
| 修改 API 接口 | 直接保存文件 | 0s（自动重载） |
| 添加 Python 依赖 | `docker compose build backend` | 2-5分钟 |
| 添加 Node 依赖 | `docker compose build frontend` | 3-8分钟 |
| 数据库迁移 | `docker exec ... alembic upgrade head` | 10-30秒 |
| 完整重建 | `docker compose build --no-cache` | 15-30分钟 |

## 🔧 常见问题

### Q: 为什么我的代码修改没有生效？

A: 检查以下几点：
1. 确认使用的是开发模式（不是生产构建）
2. 查看容器日志确认重载成功
3. 浏览器可能需要硬刷新（Ctrl+Shift+R）

### Q: 什么时候需要重新构建？

A: 只有在以下情况才需要：
- 添加了新的 Python/Node 依赖包
- 修改了 Dockerfile
- 修改了配置文件（pyproject.toml, package.json）
- 准备部署到生产环境

### Q: 如何加速构建？

A: 
1. 使用国内镜像源（已配置）
2. 利用 Docker 层缓存（不要随意修改 COPY 顺序）
3. 只重建变化的服务（不要执行 `docker compose build`）

## 💡 最佳实践

1. **小步提交**：每次修改后立即测试，避免大量累积
2. **分离关注点**：前端和后端独立开发，减少相互影响
3. **使用类型检查**：在本地运行 `mypy` 和 `tsc`，提前发现问题
4. **编写单元测试**：快速验证逻辑正确性，无需启动完整环境

## 🚀 性能对比

| 操作 | 传统方式 | 优化后 | 提升 |
|------|---------|--------|------|
| 修改代码 | 重新构建 15-20分钟 | 自动重载 0秒 | ∞ |
| 添加依赖 | 重新构建 15-20分钟 | 单独构建 2-5分钟 | 75% |
| 数据库迁移 | 重新构建 15-20分钟 | 直接执行 10-30秒 | 95% |

---

**记住：日常开发 = 修改代码 → 自动生效 → 测试验证**

只有在依赖变化或准备部署时才需要重新构建！
