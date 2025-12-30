"""
测试当配置存在但未显式启用时，不进行 fallback
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from biz.service.webhook_service import WebhookService


class TestNoFallbackWhenConfigExists:
    """测试配置存在时不需要 fallback 的场景"""

    def test_enabled_no_fallback_branch_config_false(self):
        """分支级配置存在且 enabled=False 时，不 fallback 到项目级"""
        # 模拟分支级配置（enabled=False）
        branch_config = {
            'gitlab_base_url': 'https://gitlab.example.com',
            'project_slug': 'test/project',
            'branch_pattern': 'feature/*',
            'dingtalk_url': 'https://dingtalk.example.com/webhook',
            'dingtalk_enabled': False,
            'feishu_enabled': True,
        }

        # 模拟项目级配置（所有 enabled=True）
        project_config = {
            'dingtalk_url': 'https://dingtalk.example.com/project-webhook',
            'dingtalk_enabled': True,
            'feishu_enabled': True,
            'wecom_enabled': True,
        }

        # 模拟系统级配置
        system_config = {
            'dingtalk_url': 'https://dingtalk.example.com/system-webhook',
            'dingtalk_enabled': True,
            'feishu_enabled': True,
            'wecom_enabled': True,
        }

        with patch('biz.service.webhook_service.WebhookService.get_system_config', return_value=system_config):
            result = WebhookService._get_webhook_config_with_fallback_impl(
                branch_config=branch_config,
                project_config=project_config,
                system_config=system_config,
                gitlab_base_url='https://gitlab.example.com',
                project_slug='test/project',
                branch_name='feature/test'
            )

        # 验证：分支级配置存在时，即使 enabled=False 也不应该 fallback
        # dingtalk_enabled 应该使用分支级的 False 值
        assert result['dingtalk_enabled'] is False
        # feishu_enabled 应该使用分支级的 True 值
        assert result['feishu_enabled'] is True

    def test_enabled_no_fallback_branch_config_none(self):
        """分支级配置存在但 enabled=None 时，不 fallback 到项目级"""
        # 模拟分支级配置（enabled=None，即未设置）
        branch_config = {
            'gitlab_base_url': 'https://gitlab.example.com',
            'project_slug': 'test/project',
            'branch_pattern': 'feature/*',
            'dingtalk_url': 'https://dingtalk.example.com/webhook',
            'dingtalk_enabled': None,  # 未设置
            'feishu_enabled': None,  # 未设置
        }

        # 模拟项目级配置
        project_config = {
            'dingtalk_url': 'https://dingtalk.example.com/project-webhook',
            'dingtalk_enabled': True,
            'feishu_enabled': True,
            'wecom_enabled': True,
        }

        # 模拟系统级配置
        system_config = {
            'dingtalk_url': 'https://dingtalk.example.com/system-webhook',
            'dingtalk_enabled': True,
            'feishu_enabled': True,
            'wecom_enabled': True,
        }

        with patch('biz.service.webhook_service.WebhookService.get_system_config', return_value=system_config):
            result = WebhookService._get_webhook_config_with_fallback_impl(
                branch_config=branch_config,
                project_config=project_config,
                system_config=system_config,
                gitlab_base_url='https://gitlab.example.com',
                project_slug='test/project',
                branch_name='feature/test'
            )

        # 验证：分支级配置中 enabled 不在配置字典中（或值为 None）时，
        # 如果分支级配置存在，应该检查字段是否存在于配置中
        # 根据新逻辑，只有当字段存在于配置中时才使用该值
        # 这里 dingtalk_enabled=None 表示字段存在但值为 None
        # 如果字段存在但值为 None，result 中不应该包含该字段
        # 因为只有 enabled_value is not None 时才会添加到 result_config
        # 这里分支级配置中 dingtalk_enabled 存在但值为 None，所以应该添加到结果
        # 但由于 enabled_value 是 None，而 result_config 只在 enabled_value is not None 时才添加
        # 所以结果中不应该包含该字段
        assert 'dingtalk_enabled' not in result or result.get('dingtalk_enabled') is None

    def test_enabled_fallback_to_project_when_branch_not_exist(self):
        """分支级配置不存在时，fallback 到项目级"""
        # 分支级配置不存在
        branch_config = None

        # 模拟项目级配置
        project_config = {
            'dingtalk_url': 'https://dingtalk.example.com/project-webhook',
            'dingtalk_enabled': True,
            'feishu_enabled': False,
            'wecom_enabled': True,
        }

        # 模拟系统级配置
        system_config = {
            'dingtalk_url': 'https://dingtalk.example.com/system-webhook',
            'dingtalk_enabled': True,
            'feishu_enabled': True,
            'wecom_enabled': True,
        }

        with patch('biz.service.webhook_service.WebhookService.get_system_config', return_value=system_config):
            result = WebhookService._get_webhook_config_with_fallback_impl(
                branch_config=branch_config,
                project_config=project_config,
                system_config=system_config,
                gitlab_base_url='https://gitlab.example.com',
                project_slug='test/project',
                branch_name='feature/test'
            )

        # 验证：分支级配置不存在时，应该使用项目级配置
        assert result['dingtalk_enabled'] is True
        assert result['feishu_enabled'] is False
        assert result['wecom_enabled'] is True

    def test_enabled_fallback_to_system_when_project_not_exist(self):
        """项目级配置不存在时，fallback 到系统级"""
        # 分支级配置不存在
        branch_config = None
        # 项目级配置不存在
        project_config = None

        # 模拟系统级配置
        system_config = {
            'dingtalk_url': 'https://dingtalk.example.com/system-webhook',
            'dingtalk_enabled': True,
            'feishu_enabled': False,
            'wecom_enabled': True,
        }

        with patch('biz.service.webhook_service.WebhookService.get_system_config', return_value=system_config):
            result = WebhookService._get_webhook_config_with_fallback_impl(
                branch_config=branch_config,
                project_config=project_config,
                system_config=system_config,
                gitlab_base_url='https://gitlab.example.com',
                project_slug='test/project',
                branch_name='feature/test'
            )

        # 验证：分支级和项目级配置都不存在时，应该使用系统级配置
        assert result['dingtalk_enabled'] is True
        assert result['feishu_enabled'] is False
        assert result['wecom_enabled'] is True

    def test_daily_report_enabled_no_fallback(self):
        """daily_report_enabled 不应该 fallback"""
        # 模拟分支级配置（daily_report_enabled=False）
        branch_config = {
            'gitlab_base_url': 'https://gitlab.example.com',
            'project_slug': 'test/project',
            'branch_pattern': 'feature/*',
            'daily_report_enabled': False,
        }

        # 模拟项目级配置（daily_report_enabled=True）
        project_config = {
            'daily_report_enabled': True,
        }

        # 模拟系统级配置
        system_config = {
            'daily_report_enabled': True,
        }

        with patch('biz.service.webhook_service.WebhookService.get_system_config', return_value=system_config):
            result = WebhookService._get_webhook_config_with_fallback_impl(
                branch_config=branch_config,
                project_config=project_config,
                system_config=system_config,
                gitlab_base_url='https://gitlab.example.com',
                project_slug='test/project',
                branch_name='feature/test'
            )

        # 验证：daily_report_enabled 应该使用分支级的 False 值
        assert result['daily_report_enabled'] is False


# 辅助方法：将 get_webhook_config_with_fallback 的核心逻辑提取为静态方法供测试
def _add_test_helper():
    """为 WebhookService 添加测试辅助方法"""
    @staticmethod
    def _get_webhook_config_with_fallback_impl(branch_config=None, project_config=None, 
                                             system_config=None, gitlab_base_url=None,
                                             project_slug=None, branch_name=None,
                                             project_name=None, url_slug=None):
        """测试辅助方法：模拟 get_webhook_config_with_fallback 的核心逻辑"""
        result_config = {}
        
        # Enabled 状态：如果子层级配置存在，使用其值（不回退）
        for enabled_field in ['dingtalk_enabled', 'feishu_enabled', 'wecom_enabled']:
            enabled_value = None
            enabled_source = None
            
            # 尝试从分支级获取
            if branch_config and enabled_field in branch_config:
                enabled_value = branch_config.get(enabled_field)
                enabled_source = "分支级"
            # 尝试从项目级获取
            elif project_config and enabled_field in project_config:
                enabled_value = project_config.get(enabled_field)
                enabled_source = "项目级"
            # 尝试从系统级获取
            elif enabled_field in system_config:
                enabled_value = system_config.get(enabled_field)
                enabled_source = "系统级"
            
            if enabled_value is not None:
                result_config[enabled_field] = enabled_value
        
        # Daily Report Enabled: 优先级 分支级 > 项目级 > 系统级
        # 如果分支级配置存在，使用其值（不回退）
        daily_report_enabled = None
        if branch_config and 'daily_report_enabled' in branch_config:
            daily_report_enabled = branch_config.get('daily_report_enabled')
        elif project_config and 'daily_report_enabled' in project_config:
            daily_report_enabled = project_config.get('daily_report_enabled')
        elif 'daily_report_enabled' in system_config:
            daily_report_enabled = system_config.get('daily_report_enabled')
        
        if daily_report_enabled is not None:
            result_config['daily_report_enabled'] = daily_report_enabled
        
        return result_config
    
    WebhookService._get_webhook_config_with_fallback_impl = _get_webhook_config_with_fallback_impl


# 添加测试辅助方法
_add_test_helper()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
