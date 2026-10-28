#!/bin/bash
# 个人开发模式一键启动脚本
# 本机只启动 backend + frontend，数据库/Redis/MinIO/EDBO 全部连 UAT
# 用法: bash scripts/dev-local.sh

set -e

cd "$(dirname "$0")/.."

COMPOSE_FILES="-f docker-compose.local-dev.yml"

# 检查配置
if [ ! -f .env.local ]; then
    echo "❌ 请先配置 .env.local"
    echo "   cp .env.local.example .env.local && vim .env.local"
    exit 1
fi

# 从 .env.local 的 DATABASE_URL 提取 UAT 主机（默认 172.17.62.101 内网 IP）
UAT_HOST=$(grep -E '^DATABASE_URL=' .env.local | head -1 | sed -E 's#.*@([^:/]+):.*#\1#')
UAT_HOST="${UAT_HOST:-172.17.62.101}"

echo "🔍 检查 UAT 服务连通性 (${UAT_HOST})..."
check_port() {
    local name="$1" port="$2"
    if timeout 3 bash -c "echo > /dev/tcp/${UAT_HOST}/${port}" 2>/dev/null; then
        echo "   ${name}: ✓ (${UAT_HOST}:${port})"
    else
        echo "   ${name}: ✗ (${UAT_HOST}:${port} 不可达)"
        return 1
    fi
}

CHECK_FAILED=0
check_port postgres 5432 || CHECK_FAILED=1
check_port redis 6379 || CHECK_FAILED=1
check_port minio 9000 || CHECK_FAILED=1
check_port edbo-service 8001 || CHECK_FAILED=1

if [ "$CHECK_FAILED" -ne 0 ]; then
    echo ""
    echo "⚠️  存在不可达的 UAT 服务，请确认已连接内网/VPN。"
    echo "   是否继续启动？(y/N)"
    read -r answer
    [ "$answer" = "y" ] || exit 0
fi

echo ""
echo "🚀 启动本地开发环境（仅 backend + frontend）..."
docker compose $COMPOSE_FILES --env-file .env.local up -d --build backend frontend

echo ""
echo "✅ 开发环境已启动"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo ""
echo "📋 常用命令:"
echo "   查看日志:  docker compose $COMPOSE_FILES logs -f"
echo "   停止服务:  docker compose $COMPOSE_FILES down"
echo "   重启后端:  docker compose $COMPOSE_FILES restart backend"
echo "   执行迁移:  docker compose $COMPOSE_FILES --env-file .env.local run --rm migrate"
