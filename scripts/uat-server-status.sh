#!/bin/bash
# UAT 服务器状态检查脚本
# 在 UAT 服务器上运行: bash scripts/uat-server-status.sh

# compose 端口映射需与 docker-compose.uat-infra.yml / docker-compose.uat.yml 保持一致
# （.env.uat 存在时加载，避免 ${VAR} 插值告警）
COMPOSE_ARGS=()
if [ -f .env.uat ]; then
    COMPOSE_ARGS=(--env-file .env.uat)
fi

echo "=== UAT 服务器状态检查 ==="
echo ""

echo "📦 容器状态:"
docker compose "${COMPOSE_ARGS[@]}" \
    -f docker-compose.uat-infra.yml \
    -f docker-compose.uat.yml \
    ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "🔍 健康检查:"
# 参数: 容器名(不含 uat- 前缀) 宿主端口 [HTTP 探测路径]
check_service() {
    local name="$1"
    local port="$2"
    local path="${3:-/}"
    local container="uat-${name}"

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

    # 无 HEALTHCHECK 的服务（edbo-service/frontend/nginx）退回 HTTP 端口探测
    if curl -sf --connect-timeout 3 --max-time 3 "http://localhost:${port}${path}" > /dev/null 2>&1; then
        echo "   $name: ✓ (port ${port})"
    else
        echo "   $name: ✗ (port ${port} 不通)"
    fi
}

check_service postgres 5432
check_service redis 6379
check_service minio 9000 /minio/health/live
check_service backend 8000 /health/ready
check_service edbo-service 8001
check_service frontend 3000
check_service nginx 80
echo ""

echo "💾 磁盘使用:"
df -h / | tail -1
echo ""

echo "🐳 Docker 磁盘:"
docker system df
