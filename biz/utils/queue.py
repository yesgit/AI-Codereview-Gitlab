import os
import time
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


def retry_task(function: callable, data: any, token: str, url: str, url_slug: str, delay: int = 60):
    """
    重试失败的任务，支持两种模式：
    1. RQ (Redis Queue) - 延迟重试
    2. Multiprocessing - 延迟后重新启动进程
    
    :param function: 要重试的函数
    :param data: 任务数据
    :param token: GitLab/GitHub token
    :param url: GitLab/GitHub URL
    :param url_slug: URL 标识
    :param delay: 延迟秒数
    """
    queue_driver = os.getenv('QUEUE_DRIVER', 'multiprocessing').lower()
    
    if queue_driver == 'rq':
        try:
            from redis import Redis
            from rq import Queue
            from rq.job import JobStatus
            
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
            
            redis_conn = Redis.from_url(redis_url)
            q = Queue(queue_name, connection=redis_conn)
            
            # 使用 scheduled_at 参数实现延迟重试
            scheduled_time = time.time() + delay
            job = q.enqueue_in(
                delay,
                function,
                data,
                token,
                url,
                url_slug,
                job_timeout='30m',
                result_ttl=86400  # 保留结果24小时
            )
            logger.info(f'Task scheduled for retry in {delay}s: {job.id}')
        except Exception as e:
            logger.error(f'Failed to schedule retry with RQ: {e}. Falling back to multiprocessing.')
            # 失败时使用多进程模式重试
            _retry_with_multiprocessing(function, data, token, url, url_slug, delay)
    else:
        # 使用多进程模式重试
        _retry_with_multiprocessing(function, data, token, url, url_slug, delay)


def _retry_with_multiprocessing(function: callable, data: any, token: str, url: str, url_slug: str, delay: int):
    """使用多进程延迟重试任务"""
    def delayed_retry():
        time.sleep(delay)
        process = Process(target=function, args=(data, token, url, url_slug))
        process.start()
        logger.info(f'Retry task started in new process after {delay}s: {process.pid}')
    
    # 在新线程中执行延迟重试，避免阻塞
    import threading
    retry_thread = threading.Thread(target=delayed_retry, daemon=True)
    retry_thread.start()
    logger.info(f'Task scheduled for retry in {delay}s using multiprocessing')
