#!/bin/bash
# 快速开发脚本 - 无需重新构建容器

set -e

cd "$(dirname "$0")/.."

echo "🚀 启动开发环境..."

# 检查服务是否已在运行
if docker compose ps | grep -q "erp-backend"; then
    echo "✅ 服务已在运行，使用热重载模式"
    echo "💡 修改代码后会自动重载，无需重启"
else
    echo "⚠️  服务未运行，首次启动需要构建..."
    docker compose up -d
fi

echo ""
echo "📝 开发提示："
echo "  - 后端代码修改：自动重载（uvicorn --reload）"
echo "  - 前端代码修改：自动重载（Next.js dev mode）"
echo "  - 依赖变化：需要重新构建（pnpm install 或 uv sync）"
echo ""
echo "🔍 查看日志："
echo "  docker compose logs -f backend"
echo "  docker compose logs -f frontend"
echo ""
echo "🛑 停止服务："
echo "  docker compose down"
