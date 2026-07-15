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

# 后端代码
COPY api ./api
COPY biz ./biz
COPY alembic ./alembic
COPY alembic.ini .
COPY conf/prompt_templates.yml ./conf/prompt_templates.yml

# 前端产物 (从 frontend-builder 阶段复制)
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# 数据和日志目录
RUN mkdir -p data log

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================
# Stage 3: Worker (可选，独立扩展)
# ============================================
FROM app AS worker

CMD ["python", "-c", "\
import os; \
os.environ['QUEUE_DRIVER'] = os.getenv('QUEUE_DRIVER', 'multiprocessing'); \
print(f'Worker started with {os.environ[\"QUEUE_DRIVER\"]} driver'); \
# Worker 进程由 multiprocessing 或 RQ 管理，这里保持容器存活 \
import time; \
while True: time.sleep(60)"]
