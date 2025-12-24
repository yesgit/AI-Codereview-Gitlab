# Base stage - common Python dependencies
FROM python:3.11-slim AS base
WORKDIR /app

# Install redis-cli for health checks
RUN apt-get update && apt-get install -y --no-install-recommends redis-tools && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Frontend build stage
FROM node:18-slim AS frontend-builder
WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package.json frontend/package-lock.json ./

# Install dependencies
RUN npm install

# Copy frontend source code
COPY frontend/ ./

# Build frontend
RUN npm run build

# App stage - FastAPI + Pre-built Frontend
FROM base AS app
WORKDIR /app

# Copy Python packages
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copy application code
COPY docker-entrypoint.sh .
COPY alembic.ini .
COPY alembic ./alembic
COPY api ./api
COPY biz ./biz
COPY conf ./conf

# Copy built frontend from frontend-builder stage
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Make entrypoint script executable
RUN chmod +x docker-entrypoint.sh

# Create data and log directories
RUN mkdir -p /app/data /app/log

# Expose port
EXPOSE 5001

# Set entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Run application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "5001"]

# Worker stage - for background tasks (doesn't need frontend)
FROM base AS worker
WORKDIR /app

# Copy Python packages
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copy application code
COPY docker-entrypoint.sh .
COPY alembic.ini .
COPY alembic ./alembic
COPY api ./api
COPY biz ./biz
COPY conf ./conf

# Make entrypoint script executable
RUN chmod +x docker-entrypoint.sh

# Create data and log directories
RUN mkdir -p /app/data /app/log

# Set entrypoint for worker
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# 根据队列驱动决定启动方式
# multiprocessing: 不需要独立 worker（由 app 处理），保持容器运行
# rq: 启动 RQ worker
CMD ["sh", "-c", "if [ \"$QUEUE_DRIVER\" = \"rq\" ]; then exec /app/docker-entrypoint.sh \"worker\"; else echo '⚠️  multiprocessing mode: worker not needed, keeping container alive'; tail -f /dev/null; fi"]
