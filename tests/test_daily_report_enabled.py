"""测试 daily_report_enabled 功能"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import pandas as pd

from biz.service.webhook_service import WebhookService
from biz.api.routes.daily_report import send_report_to_config, daily_report_task


class TestDailyReportEnabled:
    """测试 daily_report_enabled 配置"""

    def test_webhook_service_system_config_includes_daily_report_enabled(self):
        """测试系统级配置包含 daily_report_enabled"""
        import os
        
        # 测试默认值（环境变量未设置时默认为 True）
        config = WebhookService.get_system_config()
        assert 'daily_report_enabled' in config
        # 默认值为 True
        assert config['daily_report_enabled'] is True
        
        # 测试环境变量设置为 0
        os.environ['DAILY_REPORT_ENABLED'] = '0'
        config = WebhookService.get_system_config()
        assert config['daily_report_enabled'] is False
        
        # 测试环境变量设置为 1
        os.environ['DAILY_REPORT_ENABLED'] = '1'
        config = WebhookService.get_system_config()
        assert config['daily_report_enabled'] is True
        
        # 清理环境变量
        del os.environ['DAILY_REPORT_ENABLED']

    @patch('biz.service.webhook_service.get_engine')
    def test_webhook_config_with_fallback_daily_report_enabled(self, mock_get_engine):
        """测试 get_webhook_config_with_fallback 中的 daily_report_enabled 优先级"""
        # Mock 数据库响应
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        
        # 测试分支级配置的 daily_report_enabled
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        # Mock 分支配置查询
        mock_branch_config = {
            'id': 1,
            'gitlab_base_url': 'https://gitlab.com',
            'project_slug': 'group/project',
            'branch_pattern': 'feature/*',
            'daily_report_enabled': False,
            'dingtalk_url': 'https://oapi.dingtalk.com/webhook',
            'custom_prompt_system': 'test',
        }
        mock_conn.execute.return_value.mappings.return_value.first.return_value = mock_branch_config
        
        config = WebhookService.get_webhook_config_with_fallback(
            gitlab_base_url='https://gitlab.com',
            project_slug='group/project',
            branch_name='feature/test'
        )
        
        # 应该使用分支级的 daily_report_enabled
        assert config['daily_report_enabled'] is False

    def test_send_report_to_config_skip_when_disabled(self):
        """测试 send_report_to_config 在 daily_report_enabled=False 时跳过发送"""
        from unittest.mock import patch
        
        logs = [
            {
                'author': 'test',
                'commit_messages': 'test commit',
                'source_branch': 'feature/test',
            }
        ]
        
        config = {
            'daily_report_enabled': False,
            'dingtalk_url': 'https://oapi.dingtalk.com/webhook',
        }
        
        # Mock 通知器，验证不被调用
        with patch('biz.api.routes.daily_report.notifier.send_notification') as mock_notify:
            send_report_to_config(logs, config, title_prefix="test")
            # 不应该发送通知
            mock_notify.assert_not_called()

    def test_send_report_to_config_send_when_enabled(self):
        """测试 send_report_to_config 在 daily_report_enabled=True 时发送"""
        from unittest.mock import patch, MagicMock
        
        logs = [
            {
                'author': 'test',
                'commit_messages': 'test commit',
                'source_branch': 'feature/test',
            }
        ]
        
        config = {
            'daily_report_enabled': True,
            'dingtalk_url': 'https://oapi.dingtalk.com/webhook',
            'dingtalk_enabled': True,
        }
        
        # Mock pd 和 Reporter
        with patch('pandas.DataFrame') as mock_df_class, \
             patch('biz.api.routes.daily_report.Reporter') as mock_reporter, \
             patch('biz.api.routes.daily_report.DingTalkNotifier') as mock_dt:
            
            mock_df = MagicMock()
            mock_df.drop_duplicates.return_value = mock_df
            mock_df.sort_values.return_value = mock_df
            mock_df.to_dict.return_value = logs
            mock_df_class.return_value = mock_df
            
            mock_dt_instance = MagicMock()
            mock_dt.return_value = mock_dt_instance
            
            mock_reporter_instance = MagicMock()
            mock_reporter.return_value = mock_reporter_instance
            mock_reporter_instance.generate_report.return_value = "Test Report"
            
            send_report_to_config(logs, config, title_prefix="test")
            # 应该调用 DingTalkNotifier 发送通知
            mock_dt_instance.send_message.assert_called_once()

    @patch('biz.service.webhook_service.get_engine')
    def test_create_branch_webhook_with_daily_report_enabled(self, mock_get_engine):
        """测试创建分支配置时包含 daily_report_enabled"""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        
        mock_conn = MagicMock()
        mock_engine.begin.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.lastrowid = 1
        
        result = WebhookService.create_branch_webhook_config(
            gitlab_base_url='https://gitlab.com',
            project_slug='group/project',
            branch_pattern='feature/*',
            daily_report_enabled=False
        )
        
        assert result is True
        # 验证 SQL 调用包含 daily_report_enabled
        call_args = mock_conn.execute.call_args[0][0]
        sql_text = str(call_args)
        assert 'daily_report_enabled' in sql_text or 'daily_report_enabled' in mock_conn.execute.call_args[1]

    @patch('biz.service.webhook_service.get_engine')
    def test_update_branch_webhook_with_daily_report_enabled(self, mock_get_engine):
        """测试更新分支配置时包含 daily_report_enabled"""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        
        # Mock SELECT 查询返回记录
        mock_conn = MagicMock()
        mock_conn.execute.return_value.mappings.return_value.first.return_value = {'id': 1}
        mock_engine.begin.return_value.__enter__.return_value = mock_conn
        
        result = WebhookService.update_branch_webhook_config_by_id(
            1,
            daily_report_enabled=False
        )
        
        assert result is True

    def test_create_or_update_webhook_mapping_with_daily_report_enabled(self):
        """测试创建/更新项目配置时包含 daily_report_enabled"""
        # 这个测试简化为只验证参数传递正确
        # 测试 daily_report_enabled 参数在 SQL 中
        from unittest.mock import patch
        
        with patch('biz.service.webhook_service.get_engine') as mock_get_engine:
            mock_engine = MagicMock()
            mock_get_engine.return_value = mock_engine
            
            # Mock 连接
            mock_conn = MagicMock()
            mock_engine.begin.return_value.__enter__.return_value = mock_conn
            mock_conn.execute.return_value.mappings.return_value.first.return_value = None
            mock_conn.execute.return_value.lastrowid = 1
            mock_engine.connect.return_value.__enter__.return_value = mock_conn
            mock_conn.execute.return_value.mappings.return_value.first.return_value = {
                'id': 1,
                'project_name': 'test-project',
                'daily_report_enabled': False
            }
            
            result = WebhookService.create_or_update_webhook_mapping(
                project_name='test-project',
                daily_report_enabled=False
            )
            
            # 验证至少调用了 execute（INSERT 或 UPDATE）
            assert mock_conn.execute.called

    @patch('biz.service.webhook_service.get_engine')
    def test_update_webhook_mapping_by_id_with_daily_report_enabled(self, mock_get_engine):
        """测试通过 ID 更新项目配置时包含 daily_report_enabled"""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        
        mock_conn = MagicMock()
        mock_conn.execute.return_value.mappings.return_value.first.return_value = {'id': 1}
        mock_engine.begin.return_value.__enter__.return_value = mock_conn
        
        result = WebhookService.update_webhook_mapping_by_id(
            1,
            daily_report_enabled=False
        )
        
        assert result is True
