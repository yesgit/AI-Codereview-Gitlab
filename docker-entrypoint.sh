#!/bin/bash
# Docker 容器启动入口脚本 - 自动执行数据库迁移

set -e

echo "🚀 Starting AI Code Review Application..."

# 等待数据库就绪（如果使用 MySQL）
if [ -n "$MYSQL_HOST" ]; then
    echo "⏳ Waiting for MySQL to be ready..."
    max_tries=30
    tries=0
    until mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1" &> /dev/null || [ $tries -eq $max_tries ]; do
        tries=$((tries + 1))
        echo "  MySQL not ready yet (attempt $tries/$max_tries)..."
        sleep 2
    done
    
    if [ $tries -eq $max_tries ]; then
        echo "❌ Failed to connect to MySQL after $max_tries attempts"
        exit 1
    fi
    echo "✅ MySQL is ready!"
fi

# 等待 Redis 就绪
echo "⏳ Waiting for Redis to be ready..."
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
max_tries=30
tries=0

# 构建 redis-cli 命令
until [ $tries -eq $max_tries ]; do
    if [ -n "$REDIS_PASSWORD" ]; then
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" ping &> /dev/null && break
    else
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping &> /dev/null && break
    fi
    tries=$((tries + 1))
    echo "  Redis not ready yet (attempt $tries/$max_tries)..."
    sleep 2
done

if [ $tries -eq $max_tries ]; then
    echo "❌ Failed to connect to Redis after $max_tries attempts"
    exit 1
fi
echo "✅ Redis is ready!"

# 执行数据库迁移（除非设置了 SKIP_DB_MIGRATION）
if [ "$SKIP_DB_MIGRATION" != "true" ]; then
    echo "📦 Running database migrations..."
    if alembic upgrade head; then
        echo "✅ Database migrations completed successfully!"
    else
        echo "⚠️  Database migrations failed, but continuing..."
    fi
else
    echo "⏭️  Skipping database migrations (SKIP_DB_MIGRATION=true)"
fi

# 启动应用
echo "🎉 Starting application services..."

# 检查是 worker 还是 app
if [[ "$@" == *"worker"* ]]; then
    echo "👷 Starting RQ worker..."
    echo "   Redis URL: ${REDIS_URL:-redis://redis:6379/0}"
    echo "   Queue: ${WORKER_QUEUE:-default}"
    # 启动 RQ worker
    exec rq worker --url "${REDIS_URL:-redis://redis:6379/0}" --log-format="%(asctime)s: %(message)s" "${WORKER_QUEUE:-default}"
else
    exec "$@"
fi
