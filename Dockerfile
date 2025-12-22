# 使用官方的 Python 基础镜像作为基础层
FROM python:3.10-slim AS base

# 设置工作目录
WORKDIR /app

# 安装 supervisord 作为进程管理工具
RUN apt-get update && apt-get install -y --no-install-recommends supervisor && rm -rf /var/lib/apt/lists/*

# 复制并安装依赖
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 创建必要目录并复制公共文件
RUN mkdir -p /app/log /app/data /app/conf
COPY biz ./biz
COPY fonts ./fonts
COPY api.py ./api.py
COPY ui.py ./ui.py
COPY conf/prompt_templates.yml ./conf/prompt_templates.yml

# App stage：用于运行 Web 应用（Flask + Streamlit）
FROM base AS app
COPY conf/supervisord.app.conf /etc/supervisor/conf.d/supervisord.conf
# 暴露 Flask 和 Streamlit 的端口
EXPOSE 5001 5002
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

# Worker stage：用于运行后台任务队列/worker
FROM base AS worker
COPY conf/supervisord.worker.conf /etc/supervisor/conf.d/supervisord.conf
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
