# ============================================
# Stage 1: Frontend build
# ============================================
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ============================================
# Stage 2: App runtime
# ============================================
FROM python:3.10-slim AS app

WORKDIR /app

# 系统工具 (git/ripgrep 供 agentic review 使用)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    ripgrep \
    tree \
    file \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY api ./api
COPY biz ./biz
COPY alembic ./alembic
COPY alembic.ini .
COPY conf ./conf

# 前端产物
COPY --from=frontend-builder /frontend/dist ./frontend/dist

RUN mkdir -p data log

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================
# Stage 3: Worker (Redis Queue 模式，独立扩展)
# ============================================
FROM app AS worker

# RQ Worker: 从 Redis 队列拉取任务执行
# 使用前需设置: QUEUE_DRIVER=rq 和 REDIS_URL
CMD ["sh", "-c", "\
  if [ \"$QUEUE_DRIVER\" = 'rq' ]; then \
    echo 'Starting RQ Worker...'; \
    rq worker --url \"${REDIS_URL:-redis://redis:6379/0}\" \"${WORKER_QUEUE:-default}\"; \
  else \
    echo 'QUEUE_DRIVER not set to rq, worker idle'; \
    tail -f /dev/null; \
  fi"]
