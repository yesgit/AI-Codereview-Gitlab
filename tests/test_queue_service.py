"""
队列服务单元测试
"""
import os
import pytest
from unittest.mock import Mock, patch, MagicMock

# 设置测试环境
os.environ['QUEUE_DRIVER'] = 'rq'
os.environ['REDIS_HOST'] = 'localhost'
os.environ['REDIS_PORT'] = '6379'
os.environ['REDIS_DB'] = '0'
os.environ['WORKER_QUEUE'] = 'test_queue'


class TestQueueService:
    """测试队列服务"""

    def test_queue_driver_multiprocessing_not_supported(self):
        """测试 multiprocessing 模式不支持队列状态统计"""
        os.environ['QUEUE_DRIVER'] = 'multiprocessing'
        
        from biz.service.queue_service import QueueService
        
        service = QueueService()
        result = service.get_queue_status()
        
        assert result['queue_driver'] == 'multiprocessing'
        assert result['supported'] is False
        assert '仅支持 Redis Queue' in result['message']

    def test_queue_status_rq_mode_skip(self):
        """测试 RQ 模式获取队列状态 - 跳过（需要真实 Redis）"""
        # 这个测试需要真实的 Redis 连接，暂时跳过
        # 如果需要测试，可以在测试环境启动 Redis 并运行完整测试
        pytest.skip("需要 Redis 连接")

    def test_redis_connection_failure_skip(self):
        """测试 Redis 连接失败 - 跳过（需要 mock）"""
        # 这个测试需要 mock __import__，暂时跳过
        pytest.skip("需要更复杂的 mock")

    def test_extract_job_info_from_webhook_merge_request(self):
        """测试从 webhook 数据中提取 MR 任务信息"""
        from biz.service.queue_service import QueueService
        
        service = QueueService()
        job_info = {
            'event_type': 'unknown',
            'project_name': 'unknown',
            'author': 'unknown'
        }
        
        webhook_data = {
            'object_kind': 'merge_request',
            'project': {
                'name': 'test-project'
            },
            'user': {
                'username': 'test-user'
            },
            'object_attributes': {
                'source_branch': 'feature-1',
                'target_branch': 'main',
                'url': 'http://example.com/mr/1'
            },
            'changes': [
                {'old_path': 'file1.py', 'new_path': 'file1.py'},
                {'old_path': 'file2.py', 'new_path': 'file2.py'}
            ]
        }
        
        service._extract_job_info_from_webhook(job_info, webhook_data)
        
        assert job_info['event_type'] == 'merge_request'
        assert job_info['project_name'] == 'test-project'
        assert job_info['author'] == 'test-user'
        assert job_info['source_branch'] == 'feature-1'
        assert job_info['target_branch'] == 'main'
        assert job_info['url'] == 'http://example.com/mr/1'
        assert job_info['changed_files'] == 2

    def test_extract_job_info_from_webhook_push(self):
        """测试从 webhook 数据中提取 Push 任务信息"""
        from biz.service.queue_service import QueueService
        
        service = QueueService()
        job_info = {
            'event_type': 'unknown',
            'project_name': 'unknown',
            'author': 'unknown'
        }
        
        webhook_data = {
            'object_kind': 'push',
            'project': {
                'name': 'test-project'
            },
            'user': {
                'name': 'test-user'
            },
            'ref': 'refs/heads/feature-1',
            'commits': [
                {'id': 'abc123', 'message': 'commit 1'},
                {'id': 'def456', 'message': 'commit 2'}
            ]
        }
        
        service._extract_job_info_from_webhook(job_info, webhook_data)
        
        assert job_info['event_type'] == 'push'
        assert job_info['project_name'] == 'test-project'
        assert job_info['author'] == 'test-user'
        assert job_info['branch'] == 'feature-1'
        assert job_info['commit_count'] == 2

    def test_group_jobs_by_project(self):
        """测试按项目分组任务"""
        from biz.service.queue_service import QueueService
        
        service = QueueService()
        jobs = [
            {'project_name': 'project-a', 'status': 'pending'},
            {'project_name': 'project-a', 'status': 'processing'},
            {'project_name': 'project-b', 'status': 'pending'},
            {'project_name': 'project-a', 'status': 'pending'},
        ]
        
        result = service._group_jobs_by_project(jobs)
        
        assert 'project-a' in result
        assert 'project-b' in result
        assert result['project-a']['pending'] == 2
        assert result['project-a']['processing'] == 1
        assert result['project-b']['pending'] == 1
        assert len(result['project-a']['tasks']) == 3
        assert len(result['project-b']['tasks']) == 1

    def test_format_timestamp(self):
        """测试时间戳格式化"""
        from biz.service.queue_service import QueueService
        from datetime import datetime, timedelta, timezone
        
        service = QueueService()
        
        # 创建一个 UTC 时间戳（2025-01-01 00:00:00 UTC）
        utc_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        timestamp = utc_time.timestamp()
        
        # 格式化后应该是北京时间（+8小时），即 2025-01-01 08:00:00
        result = service._format_timestamp(timestamp)
        
        assert result == '2025-01-01 08:00:00'

    def test_format_timestamp_none(self):
        """测试时间戳为 None 的情况"""
        from biz.service.queue_service import QueueService
        
        service = QueueService()
        result = service._format_timestamp(None)
        
        assert result == ''

    def test_format_timestamp_zero(self):
        """测试时间戳为 0 的情况"""
        from biz.service.queue_service import QueueService
        
        service = QueueService()
        result = service._format_timestamp(0)
        
        # 不应该抛出异常
        assert isinstance(result, str)

    def test_get_jobs_with_mock(self):
        """测试解析任务信息（使用 Mock）"""
        from biz.service.queue_service import QueueService
        
        service = QueueService()
        
        # 创建 Mock Job 对象
        mock_job = Mock()
        mock_job.id = 'test-job-id'
        mock_job.created_at = 1735689600.0  # 2025-01-01 00:00:00 UTC
        mock_job.enqueued_at = 1735689700.0
        mock_job.get_status.return_value = 'pending'
        mock_job.func_name = 'handle_merge_request_event'
        mock_job.args = [
            {
                'object_kind': 'merge_request',
                'project': {'name': 'test-project'},
                'user': {'username': 'test-user'},
                'object_attributes': {
                    'source_branch': 'feature',
                    'target_branch': 'main'
                }
            }
        ]
        
        jobs = service._get_jobs([mock_job])
        
        assert len(jobs) == 1
        assert jobs[0]['job_id'] == 'test-job-id'
        assert jobs[0]['status'] == 'pending'
        assert jobs[0]['event_type'] == 'merge_request'
        assert jobs[0]['project_name'] == 'test-project'
        assert jobs[0]['author'] == 'test-user'
