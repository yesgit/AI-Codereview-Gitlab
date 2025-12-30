"""
队列状态服务：支持查询 RQ (Redis Queue) 队列的状态和任务信息
"""
import os
import json
import datetime
from typing import Dict, List, Any, Optional

from biz.utils.log import logger


class QueueService:
    """队列服务类，用于查询队列状态和任务信息"""
    
    def __init__(self):
        self.queue_driver = os.getenv('QUEUE_DRIVER', 'multiprocessing').lower()
        self.queue_name = os.getenv('WORKER_QUEUE', 'default')
    
    def get_redis_connection(self):
        """获取 Redis 连接"""
        try:
            from redis import Redis
            
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
            
            return Redis.from_url(redis_url)
        except ImportError:
            logger.error("redis package not installed")
            return None
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return None
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        获取队列状态
        
        Returns:
            Dict: 包含队列统计和按项目分组的任务信息
        """
        if self.queue_driver != 'rq':
            return {
                "queue_driver": self.queue_driver,
                "supported": False,
                "message": "队列状态统计功能仅支持 Redis Queue (RQ) 模式"
            }
        
        try:
            from rq import Queue
            
            redis_conn = self.get_redis_connection()
            if not redis_conn:
                return {
                    "queue_driver": self.queue_driver,
                    "supported": False,
                    "message": "无法连接到 Redis"
                }
            
            queue = Queue(self.queue_name, connection=redis_conn)
            
            # 获取各状态的任务数
            stats = {
                "pending": queue.count,
                "processing": queue.started_job_registry.count,
                "failed": queue.failed_job_registry.count,
                "completed": queue.finished_job_registry.count
            }
            
            # 获取等待中的任务详情（按项目分组）
            pending_jobs = self._get_jobs(queue.get_jobs())
            by_project = self._group_jobs_by_project(pending_jobs)
            
            return {
                "queue_driver": self.queue_driver,
                "supported": True,
                "stats": stats,
                "by_project": by_project,
                "total": sum(stats.values())
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            return {
                "queue_driver": self.queue_driver,
                "supported": False,
                "message": f"获取队列状态失败: {str(e)}"
            }
    
    def _get_jobs(self, jobs: List) -> List[Dict[str, Any]]:
        """
        解析任务信息
        
        Args:
            jobs: RQ Job 对象列表
            
        Returns:
            List: 任务信息列表
        """
        job_list = []
        
        for job in jobs:
            try:
                # 获取任务基本信息
                job_info = {
                    "job_id": job.id,
                    "created_at": self._format_timestamp(job.created_at),
                    "enqueued_at": self._format_timestamp(job.enqueued_at),
                    "status": job.get_status(),
                    "function_name": job.func_name
                }
                
                # 解析任务参数，提取项目信息
                # args 可能是 positional args，第一个参数通常是 webhook_data
                args = job.args if job.args else []
                if args and isinstance(args[0], dict):
                    webhook_data = args[0]
                    self._extract_job_info_from_webhook(job_info, webhook_data)
                # 如果第一个参数不是 dict，尝试 kwargs
                elif job.kwargs and 'webhook_data' in job.kwargs:
                    webhook_data = job.kwargs['webhook_data']
                    self._extract_job_info_from_webhook(job_info, webhook_data)
                
                job_list.append(job_info)
            except Exception as e:
                logger.warning(f"Failed to parse job {job.id}: {e}")
                continue
        
        return job_list
    
    def _extract_job_info_from_webhook(self, job_info: Dict, webhook_data: Dict):
        """从 webhook 数据中提取任务信息"""
        # 提取事件类型
        job_info["event_type"] = webhook_data.get('object_kind', 'unknown')
        
        # 提取项目信息
        project = webhook_data.get('project', {})
        job_info["project_name"] = project.get('name', 'unknown')
        
        # 提取作者信息
        user = webhook_data.get('user', {})
        job_info["author"] = user.get('username', user.get('name', 'unknown'))
        
        # 如果是 merge_request 事件，提取分支信息
        if job_info["event_type"] == 'merge_request':
            object_attributes = webhook_data.get('object_attributes', {})
            job_info["source_branch"] = object_attributes.get('source_branch', '')
            job_info["target_branch"] = object_attributes.get('target_branch', '')
            
            # 尝试从 changes 中获取文件数量
            changes = webhook_data.get('changes', [])
            if isinstance(changes, list):
                job_info["changed_files"] = len(changes)
        elif job_info["event_type"] == 'push':
            # push 事件
            job_info["branch"] = webhook_data.get('ref', '').replace('refs/heads/', '')
            
            # 尝试获取提交数量
            commits = webhook_data.get('commits', [])
            if isinstance(commits, list):
                job_info["commit_count"] = len(commits)
        
        # 尝试获取 URL
        object_attributes = webhook_data.get('object_attributes', {})
        job_info["url"] = object_attributes.get('url', '')
    
    def _group_jobs_by_project(self, jobs: List[Dict]) -> Dict[str, Dict]:
        """按项目分组任务"""
        grouped = {}
        
        for job in jobs:
            project_name = job.get('project_name', 'unknown')
            
            if project_name not in grouped:
                grouped[project_name] = {
                    "pending": 0,
                    "processing": 0,
                    "tasks": []
                }
            
            # 更新状态计数
            status = job.get('status', 'pending')
            if status in ['pending', 'processing']:
                grouped[project_name][status] += 1
            
            grouped[project_name]["tasks"].append(job)
        
        return grouped
    
    def _format_timestamp(self, timestamp: Optional[float]) -> str:
        """格式化时间戳（从 UTC 转换为北京时间 +8小时）"""
        if not timestamp:
            return ''
        
        try:
            # 转换为 datetime 对象（已经是 UTC 时间）
            dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
            # 转换为北京时间 (+8小时)
            beijing_time = dt + datetime.timedelta(hours=8)
            return beijing_time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return ''
