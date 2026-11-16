#!/bin/bash
# 服务状态检查脚本（默认检查本地 base + dev 栈）
# 用法: bash scripts/test-server-status.sh
#
# 仓库没有独立的测试环境 compose 文件，默认对齐本地开发栈（docker-compose.yml +
# docker-compose.dev.yml）。要检查其它环境，用环境变量覆盖：
#   COMPOSE_FILES="-f docker-compose.uat-infra.yml -f docker-compose.uat.yml" \
#   CONTAINER_PREFIX=uat- bash scripts/test-server-status.sh

COMPOSE_FILES=${COMPOSE_FILES:-"-f docker-compose.yml -f docker-compose.dev.yml"}
CONTAINER_PREFIX=${CONTAINER_PREFIX:-erp-}
HEALTHCHECK_HOST=${HEALTHCHECK_HOST:-localhost}

COMPOSE_ARGS=()
if [ -f .env.local ]; then
    COMPOSE_ARGS=(--env-file .env.local)
fi

echo "=== 服务状态检查（${COMPOSE_FILES}）==="
echo ""

echo "📦 容器状态:"
# shellcheck disable=SC2086  # COMPOSE_FILES 需按空格拆成多个 -f 参数
docker compose "${COMPOSE_ARGS[@]}" $COMPOSE_FILES \
    ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "🔍 健康检查:"
# 参数: 容器名(不含前缀) [宿主端口] [HTTP 探测路径]；端口留空表示无端口映射，只看容器状态
check_service() {
    local name="$1"
    local port="${2:-}"
    local path="${3:-/}"
    local container="${CONTAINER_PREFIX}${name}"

    if ! docker ps --format '{{.Names}}' | grep -qx "$container"; then
        echo "   $name: ✗ (容器未运行)"
        return
    fi

    # 优先使用容器 HEALTHCHECK 状态（postgres/redis/minio/backend 均已定义健康检查）
    local health
    health=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container" 2>/dev/null)
    case "$health" in
        healthy)   echo "   $name: ✓ (healthy)"; return ;;
        starting)  echo "   $name: ⏳ (starting)"; return ;;
        unhealthy) echo "   $name: ✗ (unhealthy)"; return ;;
    esac

    if [ -z "$port" ]; then
        echo "   $name: ✓ (运行中，无端口映射)"
        return
    fi

    # 无 HEALTHCHECK 的服务（edbo-service/frontend/nginx）退回 HTTP 端口探测
    if curl -sf --connect-timeout 3 --max-time 3 "http://${HEALTHCHECK_HOST}:${port}${path}" > /dev/null 2>&1; then
        echo "   $name: ✓ (port ${port})"
    else
        echo "   $name: ✗ (port ${port} 不通)"
    fi
}

check_service postgres 5432
check_service redis 6379
check_service minio 9000 /minio/health/live
check_service backend 8000 /health/ready
check_service edbo-service
check_service frontend 3000
check_service nginx 80
echo ""

echo "💾 磁盘使用:"
df -h / | tail -1
echo ""

echo "🐳 Docker 磁盘:"
docker system df