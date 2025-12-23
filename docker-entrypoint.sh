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

# 执行数据库迁移
echo "📦 Running database migrations..."
if alembic upgrade head; then
    echo "✅ Database migrations completed successfully!"
else
    echo "⚠️  Database migrations failed, but continuing..."
fi

# 启动应用
echo "🎉 Starting application services..."
exec "$@"
