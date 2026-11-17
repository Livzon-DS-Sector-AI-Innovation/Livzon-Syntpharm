#!/bin/bash
# 个人开发模式一键启动脚本
# 本机只启动 backend + frontend，数据库/Redis/MinIO/EDBO 全部连 UAT
# 用法: bash scripts/dev-local.sh
#
# 覆盖文件统一为 base + dev.yml（docker-compose.local-dev.yml 已在 #114 删除）；
# 容器环境变量来自仓库根 .env，.env.local 只用于 compose 插值，两者需保持一致。

set -e

cd "$(dirname "$0")/.."

COMPOSE_ARGS=(-f docker-compose.yml -f docker-compose.dev.yml)
ENV_FILE="${ENV_FILE:-.env.local}"

# 检查配置：.env.local 供 compose 插值（如 ALLOWED_DEV_ORIGINS），缺失时给出可照抄的模板
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ 缺少 $ENV_FILE"
    echo "   cp .env.dev.example $ENV_FILE 后按本机环境修改（ENV_FILE 可覆盖该路径）"
    exit 1
fi

# 从 $ENV_FILE 的 DATABASE_URL 提取 UAT 主机（默认 172.17.62.101 内网 IP）
UAT_HOST=$(grep -E '^DATABASE_URL=' "$ENV_FILE" | head -1 | sed -E 's#.*@([^:/]+):.*#\1#')
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
docker compose "${COMPOSE_ARGS[@]}" --env-file "$ENV_FILE" up -d --build backend frontend

echo ""
echo "✅ 开发环境已启动"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo ""
echo "📋 常用命令:"
echo "   查看日志:  docker compose ${COMPOSE_ARGS[*]} logs -f"
echo "   停止服务:  docker compose ${COMPOSE_ARGS[*]} down"
echo "   重启后端:  docker compose ${COMPOSE_ARGS[*]} restart backend"
echo "   执行迁移:  docker compose ${COMPOSE_ARGS[*]} --env-file $ENV_FILE run --rm migrate"