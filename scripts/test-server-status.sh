#!/bin/bash
# 测试服务器状态检查脚本
# 在测试服务器上运行: bash scripts/test-server-status.sh

echo "=== 测试服务器状态检查 ==="
echo ""

echo "📦 容器状态:"
docker compose -f docker-compose.infra.yml -f docker-compose.test.yml ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "🔍 健康检查:"
for svc in "postgres:15432" "redis:16379" "minio:19000" "backend:18000" "frontend:13000"; do
    name=${svc%%:*}
    port=${svc##*:}
    if curl -sf --connect-timeout 3 "http://localhost:$port" > /dev/null 2>&1 || \
       docker exec test-${name} pg_isready > /dev/null 2>&1 || \
       docker exec test-${name} redis-cli ping > /dev/null 2>&1; then
        echo "   $name: ✓"
    else
        echo "   $name: ✗"
    fi
done
echo ""

echo "💾 磁盘使用:"
df -h / | tail -1
echo ""

echo "🐳 Docker 磁盘:"
docker system df
