#!/usr/bin/env python3
"""
RQ Worker 入口点
当 QUEUE_DRIVER 设置为 'rq' 时使用此 worker
"""
import os
import redis
from rq import Worker, Queue, Connection

# 从环境变量获取 Redis 连接配置
# 支持 REDIS_URL 或 REDIS_HOST/PORT/DB
if os.getenv('REDIS_URL'):
    redis_url = os.getenv('REDIS_URL')
else:
    redis_host = os.getenv('REDIS_HOST', 'redis')
    redis_port = os.getenv('REDIS_PORT', '6379')
    redis_db = os.getenv('REDIS_DB', '0')
    redis_password = os.getenv('REDIS_PASSWORD', '')
    
    if redis_password:
        redis_url = f'redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}'
    else:
        redis_url = f'redis://{redis_host}:{redis_port}/{redis_db}'

queue_name = os.getenv('WORKER_QUEUE', 'default')

# 创建 Redis 连接
redis_conn = redis.from_url(redis_url)

# 创建队列
queue = Queue(queue_name, connection=redis_conn)

# 打印启动信息
print(f"🚀 Starting RQ Worker on queue: {queue_name}")
print(f"📡 Redis URL: {redis_url}")

# 创建并启动 worker
with Connection(redis_conn):
    worker = Worker([queue])
    worker.work()
