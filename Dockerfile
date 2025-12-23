# 使用官方的 Python 基础镜像作为基础层
FROM python:3.11-slim AS base

# 设置工作目录
WORKDIR /app

# 安装 supervisord、MySQL 客户端和其他依赖
# 添加重试机制应对网络问题
RUN apt-get update && \
    for i in 1 2 3; do apt-get install -y --no-install-recommends \
        supervisor \
        default-mysql-client \
        unzip \
        curl \
        && break || sleep 5; done && \
    rm -rf /var/lib/apt/lists/*

# 复制并安装依赖
COPY requirements.txt ./
# 使用国内镜像源加速 pip 安装，启用 cache 提高速度
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 创建必要目录并复制公共文件
RUN mkdir -p /app/log /app/data /app/conf
COPY biz ./biz
COPY fonts ./fonts
COPY api.py ./api.py
COPY ui.py ./ui.py
COPY conf/prompt_templates.yml ./conf/prompt_templates.yml

# 复制 Alembic 数据库迁移文件
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

# 复制 Docker 入口脚本并设置权限
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# App stage：用于运行 Web 应用（Flask + Streamlit）
FROM base AS app
COPY conf/supervisord.app.conf /etc/supervisor/conf.d/supervisord.conf
# 暴露 Flask 和 Streamlit 的端口
EXPOSE 5001 5002
# 使用入口脚本自动执行数据库迁移
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

# Worker stage：用于运行后台任务队列/worker
FROM base AS worker
COPY conf/supervisord.worker.conf /etc/supervisor/conf.d/supervisord.conf
# 使用入口脚本自动执行数据库迁移
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
