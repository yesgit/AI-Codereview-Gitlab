import os
from multiprocessing import Process

from biz.utils.log import logger


def handle_queue(function: callable, data: any, token: str, url: str, url_slug: str):
    """
    处理异步任务，支持两种模式：
    1. RQ (Redis Queue) - 适合分布式部署
    2. Multiprocessing - 适合单机部署
    通过环境变量 QUEUE_DRIVER 控制，可选值: rq / multiprocessing，默认 multiprocessing
    """
    queue_driver = os.getenv('QUEUE_DRIVER', 'multiprocessing').lower()
    
    if queue_driver == 'rq':
        try:
            from redis import Redis
            from rq import Queue
            
            redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
            queue_name = os.getenv('WORKER_QUEUE', 'default')
            
            redis_conn = Redis.from_url(redis_url)
            q = Queue(queue_name, connection=redis_conn)
            
            # 将任务加入 Redis 队列
            job = q.enqueue(function, data, token, url, url_slug, job_timeout='30m')
            logger.info(f'Task enqueued to Redis Queue: {job.id}')
        except Exception as e:
            logger.error(f'Failed to enqueue task to Redis Queue: {e}. Falling back to multiprocessing.')
            # 失败时回退到多进程模式
            _handle_with_multiprocessing(function, data, token, url, url_slug)
    else:
        # 使用多进程模式（默认）
        _handle_with_multiprocessing(function, data, token, url, url_slug)


def _handle_with_multiprocessing(function: callable, data: any, token: str, url: str, url_slug: str):
    """使用多进程处理任务"""
    process = Process(target=function, args=(data, token, url, url_slug))
    process.start()
    logger.info(f'Task started in new process: {process.pid}')
