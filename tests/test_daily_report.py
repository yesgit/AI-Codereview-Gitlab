"""测试日终报告的分组和发送逻辑"""
import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from biz.api.routes.daily_report import get_branch_for_log, match_branch_config


class TestDailyReport:
    """测试日终报告相关功能"""

    def test_get_branch_for_log_mr(self):
        """测试从 MR 日志中获取分支名称"""
        log = {
            'source_branch': 'feature/test-branch',
            'branch': 'main'
        }
        assert get_branch_for_log(log) == 'feature/test-branch'

    def test_get_branch_for_log_push(self):
        """测试从 Push 日志中获取分支名称"""
        log = {
            'branch': 'develop',
        }
        assert get_branch_for_log(log) == 'develop'

    def test_get_branch_for_log_none(self):
        """测试日志中无分支名称的情况"""
        log = {}
        assert get_branch_for_log(log) is None

    def test_match_branch_config_exact_match(self):
        """测试精确匹配分支配置"""
        log = {
            'gitlab_base_url': 'https://gitlab.example.com',
            'project_slug': 'group/project',
            'source_branch': 'main'
        }
        
        branch_configs = [
            {
                'gitlab_base_url': 'https://gitlab.example.com',
                'project_slug': 'group/project',
                'branch_pattern': 'main',
                'dingtalk_url': 'https://oapi.dingtalk.com/robot/send?access_token=xxx'
            }
        ]
        
        result = match_branch_config(log, branch_configs)
        assert result is not None
        assert result['branch_pattern'] == 'main'

    def test_match_branch_config_wildcard_match(self):
        """测试通配符匹配分支配置"""
        log = {
            'gitlab_base_url': 'https://gitlab.example.com',
            'project_slug': 'group/project',
            'source_branch': 'feature/test-branch'
        }
        
        branch_configs = [
            {
                'gitlab_base_url': 'https://gitlab.example.com',
                'project_slug': 'group/project',
                'branch_pattern': 'feature/*',
                'dingtalk_url': 'https://oapi.dingtalk.com/robot/send?access_token=xxx'
            }
        ]
        
        result = match_branch_config(log, branch_configs)
        assert result is not None
        assert result['branch_pattern'] == 'feature/*'

    def test_match_branch_config_wildcard_question(self):
        """测试问号通配符匹配分支配置"""
        log = {
            'gitlab_base_url': 'https://gitlab.example.com',
            'project_slug': 'group/project',
            'source_branch': 'hotfix/v1'
        }
        
        branch_configs = [
            {
                'gitlab_base_url': 'https://gitlab.example.com',
                'project_slug': 'group/project',
                'branch_pattern': 'hotfix/v?',
                'dingtalk_url': 'https://oapi.dingtalk.com/robot/send?access_token=xxx'
            }
        ]
        
        result = match_branch_config(log, branch_configs)
        assert result is not None
        assert result['branch_pattern'] == 'hotfix/v?'

    def test_match_branch_config_exact_priority(self):
        """测试精确匹配优先于通配符匹配"""
        log = {
            'gitlab_base_url': 'https://gitlab.example.com',
            'project_slug': 'group/project',
            'source_branch': 'main'
        }
        
        branch_configs = [
            {
                'gitlab_base_url': 'https://gitlab.example.com',
                'project_slug': 'group/project',
                'branch_pattern': '*',
                'dingtalk_url': 'https://oapi.dingtalk.com/robot/send?access_token=wildcard'
            },
            {
                'gitlab_base_url': 'https://gitlab.example.com',
                'project_slug': 'group/project',
                'branch_pattern': 'main',
                'dingtalk_url': 'https://oapi.dingtalk.com/robot/send?access_token=exact'
            }
        ]
        
        result = match_branch_config(log, branch_configs)
        assert result is not None
        # 应该匹配精确的 'main'，而不是通配符 '*'
        assert result['branch_pattern'] == 'main'
        assert 'exact' in result['dingtalk_url']

    def test_match_branch_config_longer_wildcard_priority(self):
        """测试更具体的通配符优先"""
        log = {
            'gitlab_base_url': 'https://gitlab.example.com',
            'project_slug': 'group/project',
            'source_branch': 'feature/specific-branch'
        }
        
        branch_configs = [
            {
                'gitlab_base_url': 'https://gitlab.example.com',
                'project_slug': 'group/project',
                'branch_pattern': '*',
                'dingtalk_url': 'https://oapi.dingtalk.com/robot/send?access_token=all'
            },
            {
                'gitlab_base_url': 'https://gitlab.example.com',
                'project_slug': 'group/project',
                'branch_pattern': 'feature/*',
                'dingtalk_url': 'https://oapi.dingtalk.com/robot/send?access_token=feature'
            }
        ]
        
        result = match_branch_config(log, branch_configs)
        assert result is not None
        # 应该匹配更具体的 'feature/*'
        assert result['branch_pattern'] == 'feature/*'
        assert 'feature' in result['dingtalk_url']

    def test_match_branch_config_no_match(self):
        """测试没有匹配的分支配置"""
        log = {
            'gitlab_base_url': 'https://gitlab.example.com',
            'project_slug': 'group/project',
            'source_branch': 'develop'
        }
        
        branch_configs = [
            {
                'gitlab_base_url': 'https://gitlab.example.com',
                'project_slug': 'group/project',
                'branch_pattern': 'feature/*',
                'dingtalk_url': 'https://oapi.dingtalk.com/robot/send?access_token=xxx'
            }
        ]
        
        result = match_branch_config(log, branch_configs)
        assert result is None

    def test_match_branch_config_missing_fields(self):
        """测试缺少必要字段的情况"""
        log = {
            'gitlab_base_url': 'https://gitlab.example.com',
            # 缺少 project_slug
            'source_branch': 'main'
        }
        
        branch_configs = [
            {
                'gitlab_base_url': 'https://gitlab.example.com',
                'project_slug': 'group/project',
                'branch_pattern': 'main',
                'dingtalk_url': 'https://oapi.dingtalk.com/robot/send?access_token=xxx'
            }
        ]
        
        result = match_branch_config(log, branch_configs)
        assert result is None


class TestReporter:
    """测试 Reporter 类"""

    @patch('biz.utils.reporter.Factory')
    def test_generate_report_with_title_prefix(self, mock_factory):
        """测试生成带标题前缀的报告"""
        # Mock.py-> LLM client
        mock_client = MagicMock()
        mock_factory.return_value.getClient.return_value = mock_client
        mock_client.completions.return_value = "# Test Report\n\nContent here"
        
        from biz.utils.reporter import Reporter
        
        reporter = Reporter()
        data = '[{"author": "Alice", "commit_messages": "Fix bug"}]'
        title_prefix = "项目:myproject 分支:main"
        
        result = reporter.generate_report(data, title_prefix=title_prefix)
        
        # 验证调用
        mock_client.completions.assert_called_once()
        call_args = mock_client.completions.call_args
        
        # 检查 messages 参数
        messages = call_args.kwargs.get('messages', call_args[0][0] if call_args[0] else [])
        prompt = messages[0]['content']
        assert f"【{title_prefix}】" in prompt
        assert "下面是以json格式记录员工代码提交信息" in prompt

    @patch('biz.utils.reporter.Factory')
    def test_generate_report_without_title_prefix(self, mock_factory):
        """测试生成不带标题前缀的报告"""
        # Mock.py-> LLM client
        mock_client = MagicMock()
        mock_factory.return_value.getClient.return_value = mock_client
        mock_client.completions.return_value = "# Test Report\n\nContent here"
        
        from biz.utils.reporter import Reporter
        
        reporter = Reporter()
        data = '[{"author": "Alice", "commit_messages": "Fix bug"}]'
        
        result = reporter.generate_report(data)
        
        # 验证调用
        mock_client.completions.assert_called_once()
        call_args = mock_client.completions.call_args
        
        # 检查 messages 参数
        messages = call_args.kwargs.get('messages', call_args[0][0] if call_args[0] else [])
        prompt = messages[0]['content']
        assert "【" not in prompt
        assert "下面是以json格式记录员工代码提交信息" in prompt
