"""
测试日报功能和调度器（FastAPI 版本）
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

import pandas as pd

from api.main import app, setup_daily_report_scheduler
from biz.api.routes.daily_report import daily_report_task


@pytest.fixture
def client():
    """FastAPI 测试客户端"""
    from fastapi.testclient import TestClient
    return TestClient(app)


def test_setup_daily_report_scheduler():
    """测试调度器启动"""
    scheduler = setup_daily_report_scheduler()
    
    assert scheduler is not None
    assert scheduler.running
    # 检查是否有任务
    jobs = scheduler.get_jobs()
    assert len(jobs) == 1


def test_daily_report_trigger_route_no_data(client):
    """测试手动触发日报路由 - 无数据情况"""
    # 模拟没有数据
    with patch('biz.api.routes.daily_report.ReviewService') as mock_service:
        mock_df = pd.DataFrame()
        mock_service.return_value.get_mr_review_logs.return_value = mock_df
        
        response = client.get("/review/daily_report")
        
        assert response.status_code == 200
        assert response.json()["message"] == "Daily report generated and sent successfully."


def test_daily_report_trigger_route_with_data(client):
    """测试手动触发日报路由 - 有数据情况"""
    # 模拟有数据
    with patch('biz.api.routes.daily_report.ReviewService') as mock_review_service, \
         patch('biz.api.routes.daily_report.BranchWebhookService') as mock_branch_service, \
         patch('biz.api.routes.daily_report.WebhookService') as mock_webhook_service, \
         patch('biz.api.routes.daily_report.notifier.send_notification') as mock_notify, \
         patch('biz.api.routes.daily_report.Reporter') as mock_reporter_class:
        
        # 模拟审查日志
        mock_df = pd.DataFrame([{
            'gitlab_base_url': 'https://gitlab.example.com',
            'project_slug': 'test-project',
            'project_name': 'Test Project',
            'author': 'testuser',
            'commit_messages': 'test commit',
            'source_branch': 'main',
            'created_at': datetime.now(timezone.utc).timestamp()
        }])
        mock_review_service.return_value.get_mr_review_logs.return_value = mock_df
        
        # 模拟没有分支配置和项目配置（使用默认配置）
        mock_branch_service.get_all_branch_webhooks.return_value = []
        mock_webhook_service.get_webhook_mapping_by_gitlab_project.return_value = None
        mock_webhook_service.is_valid_webhook_config.return_value = False
        
        # 模拟报告生成
        mock_reporter_instance = Mock()
        mock_reporter_instance.generate_report.return_value = 'Test Report'
        mock_reporter_class.return_value = mock_reporter_instance
        
        response = client.get("/review/daily_report")
        
        assert response.status_code == 200
        assert response.json()["message"] == "Daily report generated and sent successfully."
        
        # 验证通知被调用
        assert mock_notify.called


def test_daily_report_task_no_data():
    """测试日报任务函数 - 无数据情况"""
    with patch('biz.api.routes.daily_report.ReviewService') as mock_service, \
         patch('biz.api.routes.daily_report.notifier.send_notification') as mock_notify:
        mock_df = pd.DataFrame()
        mock_service.return_value.get_mr_review_logs.return_value = mock_df
        
        # 执行任务
        daily_report_task()
        
        # 验证即使没有数据也会发送通知
        assert mock_notify.called
        # 验证通知内容包含"今日暂无提交"
        call_args = mock_notify.call_args
        assert "今日暂无提交" in call_args[1]['content'] or "今日暂无提交" in call_args[0][0]


def test_daily_report_task_with_project_and_branch_config():
    """测试日报任务 - 有分支配置的情况"""
    with patch('biz.api.routes.daily_report.ReviewService') as mock_review_service, \
         patch('biz.api.routes.daily_report.BranchWebhookService') as mock_branch_service, \
         patch('biz.api.routes.daily_report.WebhookService') as mock_webhook_service, \
         patch('biz.api.routes.daily_report.DingTalkNotifier') as mock_dt_notifier, \
         patch('biz.api.routes.daily_report.Reporter') as mock_reporter:
        
        # 模拟审查日志
        mock_df = pd.DataFrame([{
            'gitlab_base_url': 'https://gitlab.example.com',
            'project_slug': 'test-project',
            'project_name': 'Test Project',
            'author': 'testuser',
            'commit_messages': 'test commit',
            'source_branch': 'feature/test',
            'created_at': datetime.now(timezone.utc).timestamp()
        }])
        mock_review_service.return_value.get_mr_review_logs.return_value = mock_df
        
        # 模拟分支配置（显式启用日报）
        mock_branch_service.get_all_branch_webhooks.return_value = [{
            'id':1,
            'gitlab_base_url': 'https://gitlab.example.com',
            'project_slug': 'test-project',
            'branch_pattern': 'feature/*',
            'dingtalk_url': 'https://oapi.dingtalk.com/robot/send?access_token=test',
            'feishu_url': None,
            'wecom_url': None,
            'daily_report_enabled': True
        }]
        
        # 模拟报告生成
        mock_reporter.return_value.generate_report.return_value = 'Test Report'
        
        # 执行任务
        daily_report_task()
        
        # 验证报告生成器被调用
        assert mock_reporter.called


def test_daily_report_task_exact_branch_match():
    """测试日报任务 - 分支精确匹配"""
    with patch('biz.api.routes.daily_report.ReviewService') as mock_review_service, \
         patch('biz.api.routes.daily_report.BranchWebhookService') as mock_branch_service, \
         patch('biz.api.routes.daily_report.WebhookService') as mock_webhook_service, \
         patch('biz.api.routes.daily_report.DingTalkNotifier') as mock_dt_notifier, \
         patch('biz.api.routes.daily_report.Reporter') as mock_reporter_class:
        
        # 模拟审查日志 - 精确分支名
        mock_df = pd.DataFrame([{
            'gitlab_base_url': 'https://gitlab.example.com',
            'project_slug': 'test-project',
            'project_name': 'Test Project',
            'author': 'testuser',
            'commit_messages': 'test commit',
            'source_branch': 'main',  # 精确匹配
            'created_at': datetime.now(timezone.utc).timestamp()
        }])
        mock_review_service.return_value.get_mr_review_logs.return_value = mock_df
        
        # 模拟分支配置 - 精确匹配（显式启用日报）
        mock_branch_service.get_all_branch_webhooks.return_value = [{
            'id': 1,
            'gitlab_base_url': 'https://gitlab.example.com',
            'project_slug': 'test-project',
            'branch_pattern': 'main',  # 精确匹配
            'dingtalk_url': 'https://oapi.dingtalk.com/robot/send?access_token=test',
            'feishu_url': None,
            'wecom_url': None,
            'daily_report_enabled': True
        }]
        
        # 模拟报告生成
        mock_reporter_instance = Mock()
        mock_reporter_instance.generate_report.return_value = 'Test Report'
        mock_reporter_class.return_value = mock_reporter_instance
        
        # 执行任务
        daily_report_task()
        
        # 验证 DingTalkNotifier 被调用
        assert mock_dt_notifier.called


def test_daily_report_task_wildcard_branch_match():
    """测试日报任务 - 分支通配符匹配"""
    with patch('biz.api.routes.daily_report.ReviewService') as mock_review_service, \
         patch('biz.api.routes.daily_report.BranchWebhookService') as mock_branch_service, \
         patch('biz.api.routes.daily_report.WebhookService') as mock_webhook_service, \
         patch('biz.api.routes.daily_report.DingTalkNotifier') as mock_dt_notifier, \
         patch('biz.api.routes.daily_report.Reporter') as mock_reporter_class:
        
        # 模拟审查日志 - 通配符匹配的分支
        mock_df = pd.DataFrame([{
            'gitlab_base_url': 'https://gitlab.example.com',
            'project_slug': 'test-project',
            'project_name': 'Test Project',
            'author': 'testuser',
            'commit_messages': 'test commit',
            'source_branch': 'feature/test-branch',  # 匹配 feature/*
            'created_at': datetime.now(timezone.utc).timestamp()
        }])
        mock_review_service.return_value.get_mr_review_logs.return_value = mock_df
        
        # 模拟分支配置 - 通配符匹配（显式启用日报）
        mock_branch_service.get_all_branch_webhooks.return_value = [{
            'id': 1,
            'gitlab_base_url': 'https://gitlab.example.com',
            'project_slug': 'test-project',
            'branch_pattern': 'feature/*',  # 通配符匹配
            'dingtalk_url': 'https://oapi.dingtalk.com/robot/send?access_token=test',
            'feishu_url': None,
            'wecom_url': None,
            'daily_report_enabled': True
        }]
        
        # 模拟报告生成
        mock_reporter_instance = Mock()
        mock_reporter_instance.generate_report.return_value = 'Test Report'
        mock_reporter_class.return_value = mock_reporter_instance
        
        # 执行任务
        daily_report_task()
        
        # 验证 DingTalkNotifier 被调用
        assert mock_dt_notifier.called


def test_daily_report_task_push_review_enabled():
    """测试日报任务 - Push 审查模式"""
    with patch('biz.api.routes.daily_report.push_review_enabled', True), \
         patch('biz.api.routes.daily_report.ReviewService') as mock_review_service, \
         patch('biz.api.routes.daily_report.BranchWebhookService') as mock_branch_service, \
         patch('biz.api.routes.daily_report.WebhookService') as mock_webhook_service, \
         patch('biz.api.routes.daily_report.notifier.send_notification') as mock_notify, \
         patch('biz.api.routes.daily_report.Reporter') as mock_reporter_class:
        
        # 模拟 Push 审查日志
        mock_df = pd.DataFrame([{
            'gitlab_base_url': 'https://gitlab.example.com',
            'project_slug': 'test-project',
            'project_name': 'Test Project',
            'author': 'testuser',
            'commit_messages': 'test commit',
            'branch': 'main',  # Push 使用 branch 字段
            'created_at': datetime.now(timezone.utc).timestamp()
        }])
        mock_review_service.return_value.get_push_review_logs.return_value = mock_df
        mock_branch_service.get_all_branch_webhooks.return_value = []
        mock_webhook_service.get_webhook_mapping_by_gitlab_project.return_value = None
        mock_webhook_service.is_valid_webhook_config.return_value = False
        
        # 模拟报告生成
        mock_reporter_instance = Mock()
        mock_reporter_instance.generate_report.return_value = 'Test Report'
        mock_reporter_class.return_value = mock_reporter_instance
        
        # 执行任务
        daily_report_task()
        
        # 验证调用了 get_push_review_logs
        mock_review_service.return_value.get_push_review_logs.assert_called_once()
        # 验证通知被调用
        assert mock_notify.called


def test_daily_report_task_unmatched_logs_fallback():
    """测试日报任务 - 未匹配分支的日志回退到项目配置"""
    with patch('biz.api.routes.daily_report.ReviewService') as mock_review_service, \
         patch('biz.api.routes.daily_report.BranchWebhookService') as mock_branch_service, \
         patch('biz.api.routes.daily_report.WebhookService') as mock_webhook_service, \
         patch('biz.api.routes.daily_report.notifier.send_notification') as mock_notify, \
         patch('biz.api.routes.daily_report.Reporter') as mock_reporter_class:
        
        # 模拟审查日志 - 分支不匹配任何配置
        mock_df = pd.DataFrame([{
            'gitlab_base_url': 'https://gitlab.example.com',
            'project_slug': 'test-project',
            'project_name': 'Test Project',
            'author': 'testuser',
            'commit_messages': 'test commit',
            'source_branch': 'unmatched-branch',
            'created_at': datetime.now(timezone.utc).timestamp()
        }])
        mock_review_service.return_value.get_mr_review_logs.return_value = mock_df
        
        # 模拟分支配置 - 不匹配
        mock_branch_service.get_all_branch_webhooks.return_value = [{
            'id': 1,
            'gitlab_base_url': 'https://gitlab.example.com',
            'project_slug': 'test-project',
            'branch_pattern': 'feature/*',
            'dingtalk_url': 'https://oapi.dingtalk.com/robot/send?access_token=test',
            'feishu_url': None,
            'wecom_url': None
        }]
        
        # 模拟项目配置
        mock_webhook_service.get_webhook_mapping_by_gitlab_project.return_value = None
        mock_webhook_service.is_valid_webhook_config.return_value = False
        
        # 模拟报告生成
        mock_reporter_instance = Mock()
        mock_reporter_instance.generate_report.return_value = 'Test Report'
        mock_reporter_class.return_value = mock_reporter_instance
        
        # 执行任务
        daily_report_task()
        
        # 验证通知被调用（使用默认配置）
        assert mock_notify.called


def test_daily_report_task_error_handling():
    """测试日报任务 - 异常处理"""
    with patch('biz.api.routes.daily_report.ReviewService') as mock_service:
        # 模拟抛出异常
        mock_service.return_value.get_mr_review_logs.side_effect = Exception("Test error")
        
        # 不应该抛出异常（异常应该被捕获并记录日志）
        daily_report_task()


def test_daily_report_deduplication():
    """测试日报 - 重复提交去重"""
    with patch('biz.api.routes.daily_report.ReviewService') as mock_review_service, \
         patch('biz.api.routes.daily_report.BranchWebhookService') as mock_branch_service, \
         patch('biz.api.routes.daily_report.WebhookService') as mock_webhook_service, \
         patch('biz.api.routes.daily_report.notifier.send_notification') as mock_notify, \
         patch('biz.api.routes.daily_report.Reporter') as mock_reporter:
        
        # 模拟重复的审查日志（同一作者、同一消息）
        mock_df = pd.DataFrame([
            {
                'gitlab_base_url': 'https://gitlab.example.com',
                'project_slug': 'test-project',
                'project_name': 'Test Project',
                'author': 'testuser',
                'commit_messages': 'same commit message',  # 重复
                'source_branch': 'main',
                'created_at': datetime.now(timezone.utc).timestamp()
            },
            {
                'gitlab_base_url': 'https://gitlab.example.com',
                'project_slug': 'test-project',
                'project_name': 'Test Project',
                'author': 'testuser',
                'commit_messages': 'same commit message',  # 重复
                'source_branch': 'main',
                'created_at': datetime.now(timezone.utc).timestamp()
            }
        ])
        mock_review_service.return_value.get_mr_review_logs.return_value = mock_df
        mock_branch_service.get_all_branch_webhooks.return_value = []
        mock_webhook_service.get_webhook_mapping_by_gitlab_project.return_value = None
        mock_webhook_service.is_valid_webhook_config.return_value = False
        
        # 模拟报告生成
        mock_reporter.return_value.generate_report.return_value = 'Test Report'
        
        # 执行任务
        daily_report_task()
        
        # 验证生成器被调用（且应该只处理一条记录）
        assert mock_reporter.called


def test_match_branch_config_exact():
    """测试分支配置匹配 - 精确匹配"""
    from biz.api.routes.daily_report import match_branch_config
    
    log = {
        'gitlab_base_url': 'https://gitlab.example.com',
        'project_slug': 'test-project',
        'source_branch': 'main'
    }
    
    branch_configs = [
        {'branch_pattern': 'main', 'dingtalk_url': 'url1'},
        {'branch_pattern': 'feature/*', 'dingtalk_url': 'url2'}
    ]
    
    result = match_branch_config(log, branch_configs)
    
    assert result is not None
    assert result['branch_pattern'] == 'main'


def test_match_branch_config_wildcard():
    """测试分支配置匹配 - 通配符匹配"""
    from biz.api.routes.daily_report import match_branch_config
    
    log = {
        'gitlab_base_url': 'https://gitlab.example.com',
        'project_slug': 'test-project',
        'source_branch': 'feature/test-branch'
    }
    
    branch_configs = [
        {'branch_pattern': 'main', 'dingtalk_url': 'url1'},
        {'branch_pattern': 'feature/*', 'dingtalk_url': 'url2'}
    ]
    
    result = match_branch_config(log, branch_configs)
    
    assert result is not None
    assert result['branch_pattern'] == 'feature/*'


def test_match_branch_config_no_match():
    """测试分支配置匹配 - 无匹配"""
    from biz.api.routes.daily_report import match_branch_config
    
    log = {
        'gitlab_base_url': 'https://gitlab.example.com',
        'project_slug': 'test-project',
        'source_branch': 'develop'
    }
    
    branch_configs = [
        {'branch_pattern': 'main', 'dingtalk_url': 'url1'},
        {'branch_pattern': 'feature/*', 'dingtalk_url': 'url2'}
    ]
    
    result = match_branch_config(log, branch_configs)
    
    assert result is None


def test_get_branch_for_log():
    """测试从日志获取分支名称"""
    from biz.api.routes.daily_report import get_branch_for_log
    
    # MR log
    log1 = {'source_branch': 'main'}
    assert get_branch_for_log(log1) == 'main'
    
    # Push log
    log2 = {'branch': 'develop'}
    assert get_branch_for_log(log2) == 'develop'
    
    # 无分支信息
    log3 = {}
    assert get_branch_for_log(log3) is None


def test_daily_report_multiple_projects():
    """测试日报 - 多个项目"""
    with patch('biz.api.routes.daily_report.ReviewService') as mock_review_service, \
         patch('biz.api.routes.daily_report.BranchWebhookService') as mock_branch_service, \
         patch('biz.api.routes.daily_report.WebhookService') as mock_webhook_service, \
         patch('biz.api.routes.daily_report.notifier.send_notification') as mock_notify, \
         patch('biz.api.routes.daily_report.Reporter') as mock_reporter_class:
        
        # 模拟两个项目的审查日志
        mock_df = pd.DataFrame([
            {
                'gitlab_base_url': 'https://gitlab.example.com',
                'project_slug': 'project1',
                'project_name': 'Project 1',
                'author': 'user1',
                'commit_messages': 'commit1',
                'source_branch': 'main',
                'created_at': datetime.now(timezone.utc).timestamp()
            },
            {
                'gitlab_base_url': 'https://gitlab.example.com',
                'project_slug': 'project2',
                'project_name': 'Project 2',
                'author': 'user2',
                'commit_messages': 'commit2',
                'source_branch': 'main',
                'created_at': datetime.now(timezone.utc).timestamp()
            }
        ])
        mock_review_service.return_value.get_mr_review_logs.return_value = mock_df
        
        mock_branch_service.get_all_branch_webhooks.return_value = []
        mock_webhook_service.get_webhook_mapping_by_gitlab_project.return_value = None
        mock_webhook_service.is_valid_webhook_config.return_value = False
        
        # 模拟报告生成
        mock_reporter_instance = Mock()
        mock_reporter_instance.generate_report.return_value = 'Test Report'
        mock_reporter_class.return_value = mock_reporter_instance
        
        # 执行任务
        daily_report_task()
        
        # 应该为每个项目发送通知
        assert mock_notify.call_count == 2
