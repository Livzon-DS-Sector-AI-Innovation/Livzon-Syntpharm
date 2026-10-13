#!/bin/bash
# 本地开发一键启动脚本
# 使用 docker-compose.yml + docker-compose.dev.yml（源码挂载 + 前后端热重载）
# 基础设施（PostgreSQL/Redis/MinIO/EDBO）全部本地容器运行，数据与 UAT 隔离
# 用法: bash scripts/dev.sh

set -e

cd "$(dirname "$0")/.."

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.dev.yml"

# 检查配置（不存在则从开发模板复制）
if [ ! -f .env ]; then
    echo "📝 .env 不存在，从 .env.dev.example 复制..."
    cp .env.dev.example .env
    echo "   已创建 .env（如需飞书/AI 功能，请编辑填写）"
fi

# 首次启动（本地数据库数据目录为空）时自动写入种子数据
FIRST_RUN=0
if [ ! -d ./postgres-data ] || [ -z "$(ls -A ./postgres-data 2>/dev/null)" ]; then
    FIRST_RUN=1
fi

echo "🚀 启动本地开发环境（自动执行数据库迁移）..."
docker compose $COMPOSE_FILES up -d --build

if [ "$FIRST_RUN" -eq 1 ]; then
    echo ""
    echo "🌱 首次启动，写入模块设置种子数据..."
    if ! docker compose $COMPOSE_FILES exec -T backend \
        uv run python scripts/seed/seed_module_settings.py; then
        echo "⚠️  种子数据写入失败，请手动执行:"
        echo "   docker compose $COMPOSE_FILES exec backend uv run python scripts/seed/seed_module_settings.py"
    fi

    echo ""
    echo "👤 如需管理员账号: 在 .env 填写 BOOTSTRAP_ADMIN_USERNAME/PASSWORD 后重启 backend"
    echo "   docker compose $COMPOSE_FILES restart backend"
fi

echo ""
echo "✅ 开发环境已启动"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo "   MinIO 控制台: http://localhost:9001"
echo ""
echo "📋 常用命令:"
echo "   查看日志:  docker compose $COMPOSE_FILES logs -f"
echo "   停止服务:  docker compose $COMPOSE_FILES down"
echo "   重置数据:  docker compose $COMPOSE_FILES down && rm -rf postgres-data redis-data minio-data"
echo "   重启后端:  docker compose $COMPOSE_FILES restart backend"
