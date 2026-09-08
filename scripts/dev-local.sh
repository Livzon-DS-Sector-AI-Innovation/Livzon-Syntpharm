#!/bin/bash
# 个人开发一键启动脚本
# 用法: bash scripts/dev-local.sh

set -e

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.local.yml"

# 检查配置
if [ ! -f .env.local ]; then
    echo "❌ 请先配置 .env.local"
    echo "   cp .env.local.example .env.local && vim .env.local"
    exit 1
fi

source .env.local

echo "🔍 检查测试服务器连通性..."
if curl -sf --connect-timeout 3 "http://172.17.62.101:18000/health/live" > /dev/null 2>&1; then
    echo "   测试服务器: ✓ 可达"
else
    echo "   测试服务器: ✗ 不可达"
    echo "   是否继续启动？(y/N)"
    read -r answer
    [ "$answer" = "y" ] || exit 0
fi

echo ""
echo "🚀 启动本地开发环境..."
docker compose $COMPOSE_FILES up -d backend frontend

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
