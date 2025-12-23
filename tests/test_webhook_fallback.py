"""
测试 Webhook 配置三级回退逻辑
验证分支级 -> 项目级 -> 系统级的回退机制
以及每个字段的独立回退
"""
import pytest
import os
from unittest.mock import Mock, patch
from biz.service.webhook_service import WebhookService


class TestThreeLevelFallback:
    """测试三级配置回退"""
    
    def setup_method(self):
        """每个测试前的设置"""
        self.gitlab_base_url = "https://gitlab.com"
        self.project_slug = "mygroup/myproject"
        self.branch_name = "feature/login"
    
    @patch('biz.service.branch_webhook_service.BranchWebhookService.match_branch_webhook')
    @patch('biz.service.webhook_service.WebhookService.get_webhook_mapping_by_gitlab_project')
    @patch('biz.service.webhook_service.WebhookService.get_system_config')
    def test_use_branch_level_when_available(self, mock_system, mock_project, mock_branch):
        """测试当分支级配置有效时使用分支级"""
        # 分支级有配置
        mock_branch.return_value = {
            'dingtalk_url': 'https://branch-dingtalk',
            'feishu_url': None,
            'wecom_url': None,
            'custom_prompt_system': 'branch prompt'
        }
        # 项目级也有配置
        mock_project.return_value = {
            'dingtalk_url': 'https://project-dingtalk',
            'feishu_url': 'https://project-feishu',
            'wecom_url': None
        }
        # 系统级有配置
        mock_system.return_value = {
            'dingtalk_url': 'https://system-dingtalk',
            'feishu_url': 'https://system-feishu',
            'wecom_url': 'https://system-wecom'
        }
        
        result = WebhookService.get_webhook_config_with_fallback(
            gitlab_base_url=self.gitlab_base_url,
            project_slug=self.project_slug,
            branch_name=self.branch_name
        )
        
        # 钉钉应该使用分支级
        assert result['dingtalk_url'] == 'https://branch-dingtalk'
        # 飞书分支级没有，应该使用项目级
        assert result['feishu_url'] == 'https://project-feishu'
        # 企微前两级都没有，应该使用系统级
        assert result['wecom_url'] == 'https://system-wecom'
        # 提示词使用分支级
        assert result['custom_prompt_system'] == 'branch prompt'
    
    @patch('biz.service.branch_webhook_service.BranchWebhookService.match_branch_webhook')
    @patch('biz.service.webhook_service.WebhookService.get_webhook_mapping_by_gitlab_project')
    @patch('biz.service.webhook_service.WebhookService.get_system_config')
    def test_fallback_to_project_when_branch_empty(self, mock_system, mock_project, mock_branch):
        """测试当分支级配置为空时回退到项目级"""
        # 分支级配置存在但都是空值
        mock_branch.return_value = {
            'dingtalk_url': '',
            'feishu_url': None,
            'wecom_url': None
        }
        # 项目级有配置
        mock_project.return_value = {
            'dingtalk_url': 'https://project-dingtalk',
            'feishu_url': 'https://project-feishu',
            'wecom_url': None
        }
        # 系统级有配置
        mock_system.return_value = {
            'dingtalk_url': '',
            'feishu_url': '',
            'wecom_url': 'https://system-wecom'
        }
        
        result = WebhookService.get_webhook_config_with_fallback(
            gitlab_base_url=self.gitlab_base_url,
            project_slug=self.project_slug,
            branch_name=self.branch_name
        )
        
        # 所有URL都应该回退到项目级（分支级为空）
        assert result['dingtalk_url'] == 'https://project-dingtalk'
        assert result['feishu_url'] == 'https://project-feishu'
        # 企微项目级也是空，回退到系统级
        assert result['wecom_url'] == 'https://system-wecom'
    
    @patch('biz.service.branch_webhook_service.BranchWebhookService.match_branch_webhook')
    @patch('biz.service.webhook_service.WebhookService.get_webhook_mapping_by_gitlab_project')
    @patch('biz.service.webhook_service.WebhookService.get_system_config')
    def test_fallback_to_system_when_all_empty(self, mock_system, mock_project, mock_branch):
        """测试当分支级和项目级都为空时回退到系统级"""
        # 分支级无配置
        mock_branch.return_value = None
        # 项目级无配置
        mock_project.return_value = None
        # 系统级有配置
        mock_system.return_value = {
            'dingtalk_url': 'https://system-dingtalk',
            'feishu_url': 'https://system-feishu',
            'wecom_url': 'https://system-wecom',
            'custom_prompt_system': 'system prompt'
        }
        
        result = WebhookService.get_webhook_config_with_fallback(
            gitlab_base_url=self.gitlab_base_url,
            project_slug=self.project_slug,
            branch_name=self.branch_name
        )
        
        # 所有配置都应该使用系统级
        assert result['dingtalk_url'] == 'https://system-dingtalk'
        assert result['feishu_url'] == 'https://system-feishu'
        assert result['wecom_url'] == 'https://system-wecom'
        assert result['custom_prompt_system'] == 'system prompt'
    
    @patch('biz.service.branch_webhook_service.BranchWebhookService.match_branch_webhook')
    @patch('biz.service.webhook_service.WebhookService.get_webhook_mapping_by_gitlab_project')
    @patch('biz.service.webhook_service.WebhookService.get_system_config')
    def test_no_branch_name_skips_branch_level(self, mock_system, mock_project, mock_branch):
        """测试未提供分支名时跳过分支级配置"""
        # 项目级有配置
        mock_project.return_value = {
            'dingtalk_url': 'https://project-dingtalk',
            'feishu_url': None,
            'wecom_url': None
        }
        # 系统级有配置
        mock_system.return_value = {
            'dingtalk_url': '',
            'feishu_url': 'https://system-feishu',
            'wecom_url': 'https://system-wecom'
        }
        
        result = WebhookService.get_webhook_config_with_fallback(
            gitlab_base_url=self.gitlab_base_url,
            project_slug=self.project_slug
            # 未提供 branch_name
        )
        
        # 不应该调用分支级查询
        mock_branch.assert_not_called()
        # 应该使用项目级和系统级
        assert result['dingtalk_url'] == 'https://project-dingtalk'
        assert result['feishu_url'] == 'https://system-feishu'


class TestFieldIndependentFallback:
    """测试每个字段独立回退"""
    
    @patch('biz.service.branch_webhook_service.BranchWebhookService.match_branch_webhook')
    @patch('biz.service.webhook_service.WebhookService.get_webhook_mapping_by_gitlab_project')
    @patch('biz.service.webhook_service.WebhookService.get_system_config')
    def test_webhook_urls_independent_fallback(self, mock_system, mock_project, mock_branch):
        """测试每个webhook URL字段独立回退"""
        mock_branch.return_value = {
            'dingtalk_url': 'https://branch-dingtalk',  # 有值
            'feishu_url': '',  # 空值，应该回退
            'wecom_url': None  # 空值，应该回退
        }
        mock_project.return_value = {
            'dingtalk_url': 'https://project-dingtalk',  # 被分支级覆盖
            'feishu_url': 'https://project-feishu',  # 分支级为空，使用这个
            'wecom_url': ''  # 空值，继续回退
        }
        mock_system.return_value = {
            'dingtalk_url': 'https://system-dingtalk',  # 被分支级覆盖
            'feishu_url': 'https://system-feishu',  # 被项目级覆盖
            'wecom_url': 'https://system-wecom'  # 前两级都为空，使用这个
        }
        
        result = WebhookService.get_webhook_config_with_fallback(
            gitlab_base_url='https://gitlab.com',
            project_slug='mygroup/myproject',
            branch_name='main'
        )
        
        assert result['dingtalk_url'] == 'https://branch-dingtalk'
        assert result['feishu_url'] == 'https://project-feishu'
        assert result['wecom_url'] == 'https://system-wecom'
    
    @patch('biz.service.branch_webhook_service.BranchWebhookService.match_branch_webhook')
    @patch('biz.service.webhook_service.WebhookService.get_webhook_mapping_by_gitlab_project')
    @patch('biz.service.webhook_service.WebhookService.get_system_config')
    def test_prompts_independent_fallback(self, mock_system, mock_project, mock_branch):
        """测试提示词字段独立回退"""
        mock_branch.return_value = {
            'custom_prompt_system': 'branch system prompt',  # 有值
            'custom_prompt_user': ''  # 空值，应该回退
        }
        mock_project.return_value = {
            'custom_prompt_system': 'project system prompt',  # 被分支级覆盖
            'custom_prompt_user': 'project user prompt'  # 分支级为空，使用这个
        }
        mock_system.return_value = {
            'custom_prompt_system': 'system system prompt',  # 被分支级覆盖
            'custom_prompt_user': 'system user prompt'  # 被项目级覆盖
        }
        
        result = WebhookService.get_webhook_config_with_fallback(
            gitlab_base_url='https://gitlab.com',
            project_slug='mygroup/myproject',
            branch_name='main'
        )
        
        assert result['custom_prompt_system'] == 'branch system prompt'
        assert result['custom_prompt_user'] == 'project user prompt'
    
    @patch('biz.service.branch_webhook_service.BranchWebhookService.match_branch_webhook')
    @patch('biz.service.webhook_service.WebhookService.get_webhook_mapping_by_gitlab_project')
    @patch('biz.service.webhook_service.WebhookService.get_system_config')
    def test_mixed_config_sources(self, mock_system, mock_project, mock_branch):
        """测试混合来源的配置（每个字段可能来自不同层级）"""
        mock_branch.return_value = {
            'dingtalk_url': 'https://branch-dingtalk',
            'feishu_url': None,
            'wecom_url': None,
            'custom_prompt_system': None,
            'custom_prompt_user': None
        }
        mock_project.return_value = {
            'dingtalk_url': None,  # 无效，使用分支级
            'feishu_url': 'https://project-feishu',
            'wecom_url': None,
            'custom_prompt_system': 'project system prompt',
            'custom_prompt_user': None
        }
        mock_system.return_value = {
            'dingtalk_url': None,
            'feishu_url': None,
            'wecom_url': 'https://system-wecom',
            'custom_prompt_system': None,
            'custom_prompt_user': 'system user prompt'
        }
        
        result = WebhookService.get_webhook_config_with_fallback(
            gitlab_base_url='https://gitlab.com',
            project_slug='mygroup/myproject',
            branch_name='main'
        )
        
        # 每个字段来自不同层级
        assert result['dingtalk_url'] == 'https://branch-dingtalk'  # 分支级
        assert result['feishu_url'] == 'https://project-feishu'  # 项目级
        assert result['wecom_url'] == 'https://system-wecom'  # 系统级
        assert result['custom_prompt_system'] == 'project system prompt'  # 项目级
        assert result['custom_prompt_user'] == 'system user prompt'  # 系统级


class TestGitLabTokenFallback:
    """测试 GitLab Token 的三级回退"""
    
    @patch('biz.service.branch_webhook_service.BranchWebhookService.match_branch_webhook')
    @patch('biz.service.webhook_service.WebhookService.get_webhook_mapping_by_gitlab_project')
    @patch('biz.service.webhook_service.WebhookService.get_system_config')
    def test_gitlab_token_from_branch_level(self, mock_system, mock_project, mock_branch):
        """测试使用分支级的 GitLab Token"""
        mock_branch.return_value = {
            'dingtalk_url': 'https://branch-dingtalk',
            'gitlab_token': 'glpat-branch-token-12345'
        }
        mock_project.return_value = {
            'dingtalk_url': 'https://project-dingtalk',
            'gitlab_token': 'glpat-project-token-67890'
        }
        mock_system.return_value = {
            'dingtalk_url': 'https://system-dingtalk',
            'gitlab_token': 'glpat-system-token-abcde'
        }
        
        result = WebhookService.get_webhook_config_with_fallback(
            gitlab_base_url='https://gitlab.com',
            project_slug='mygroup/myproject',
            branch_name='feature/auth'
        )
        
        # 应该使用分支级的 token
        assert result['gitlab_token'] == 'glpat-branch-token-12345'
    
    @patch('biz.service.branch_webhook_service.BranchWebhookService.match_branch_webhook')
    @patch('biz.service.webhook_service.WebhookService.get_webhook_mapping_by_gitlab_project')
    @patch('biz.service.webhook_service.WebhookService.get_system_config')
    def test_gitlab_token_fallback_to_project(self, mock_system, mock_project, mock_branch):
        """测试在分支级为空时回退到项目级 GitLab Token"""
        mock_branch.return_value = {
            'dingtalk_url': 'https://branch-dingtalk',
            'gitlab_token': ''  # 空值
        }
        mock_project.return_value = {
            'dingtalk_url': 'https://project-dingtalk',
            'gitlab_token': 'glpat-project-token-67890'
        }
        mock_system.return_value = {
            'dingtalk_url': 'https://system-dingtalk',
            'gitlab_token': 'glpat-system-token-abcde'
        }
        
        result = WebhookService.get_webhook_config_with_fallback(
            gitlab_base_url='https://gitlab.com',
            project_slug='mygroup/myproject',
            branch_name='feature/auth'
        )
        
        # 分支级为空，应该回退到项目级
        assert result['gitlab_token'] == 'glpat-project-token-67890'
    
    @patch('biz.service.branch_webhook_service.BranchWebhookService.match_branch_webhook')
    @patch('biz.service.webhook_service.WebhookService.get_webhook_mapping_by_gitlab_project')
    @patch('biz.service.webhook_service.WebhookService.get_system_config')
    def test_gitlab_token_fallback_to_system(self, mock_system, mock_project, mock_branch):
        """测试在分支级和项目级都为空时回退到系统级 GitLab Token"""
        mock_branch.return_value = {
            'dingtalk_url': 'https://branch-dingtalk',
            'gitlab_token': None  # 无值
        }
        mock_project.return_value = {
            'dingtalk_url': 'https://project-dingtalk',
            'gitlab_token': ''  # 空值
        }
        mock_system.return_value = {
            'dingtalk_url': 'https://system-dingtalk',
            'gitlab_token': 'glpat-system-token-abcde'
        }
        
        result = WebhookService.get_webhook_config_with_fallback(
            gitlab_base_url='https://gitlab.com',
            project_slug='mygroup/myproject',
            branch_name='feature/auth'
        )
        
        # 前两级都为空，应该使用系统级
        assert result['gitlab_token'] == 'glpat-system-token-abcde'
    
    @patch('biz.service.branch_webhook_service.BranchWebhookService.match_branch_webhook')
    @patch('biz.service.webhook_service.WebhookService.get_webhook_mapping_by_gitlab_project')
    @patch('biz.service.webhook_service.WebhookService.get_system_config')
    def test_gitlab_token_independent_from_other_fields(self, mock_system, mock_project, mock_branch):
        """测试 GitLab Token 独立于其他字段进行回退"""
        mock_branch.return_value = {
            'dingtalk_url': 'https://branch-dingtalk',  # 使用分支级
            'gitlab_token': ''  # 空值，需要回退
        }
        mock_project.return_value = {
            'dingtalk_url': 'https://project-dingtalk',  # 不使用
            'gitlab_token': ''  # 空值，继续回退
        }
        mock_system.return_value = {
            'dingtalk_url': 'https://system-dingtalk',  # 不使用
            'gitlab_token': 'glpat-system-token-abcde'  # 使用系统级 token
        }
        
        result = WebhookService.get_webhook_config_with_fallback(
            gitlab_base_url='https://gitlab.com',
            project_slug='mygroup/myproject',
            branch_name='feature/auth'
        )
        
        # webhook URL 使用分支级，token 使用系统级
        assert result['dingtalk_url'] == 'https://branch-dingtalk'
        assert result['gitlab_token'] == 'glpat-system-token-abcde'
    
    @patch('biz.service.branch_webhook_service.BranchWebhookService.match_branch_webhook')
    @patch('biz.service.webhook_service.WebhookService.get_webhook_mapping_by_gitlab_project')
    @patch('biz.service.webhook_service.WebhookService.get_system_config')
    def test_no_gitlab_token_at_all_levels(self, mock_system, mock_project, mock_branch):
        """测试所有层级都没有 GitLab Token 时不返回该字段"""
        mock_branch.return_value = {
            'dingtalk_url': 'https://branch-dingtalk',
            'gitlab_token': None
        }
        mock_project.return_value = {
            'dingtalk_url': 'https://project-dingtalk',
            'gitlab_token': ''
        }
        mock_system.return_value = {
            'dingtalk_url': 'https://system-dingtalk',
            'gitlab_token': ''
        }
        
        result = WebhookService.get_webhook_config_with_fallback(
            gitlab_base_url='https://gitlab.com',
            project_slug='mygroup/myproject',
            branch_name='feature/auth'
        )
        
        # 所有层级都没有 token，结果中不应该包含 gitlab_token
        assert 'gitlab_token' not in result
        # 但其他字段正常
        assert result['dingtalk_url'] == 'https://branch-dingtalk'


class TestConfigValidation:
    """测试配置有效性验证"""
    
    def test_valid_config_with_dingtalk(self):
        """测试有钉钉URL的配置有效"""
        config = {
            'dingtalk_url': 'https://dingtalk-webhook',
            'feishu_url': None,
            'wecom_url': None
        }
        assert WebhookService.is_valid_webhook_config(config) is True
    
    def test_valid_config_with_feishu(self):
        """测试有飞书URL的配置有效"""
        config = {
            'dingtalk_url': '',
            'feishu_url': 'https://feishu-webhook',
            'wecom_url': None
        }
        assert WebhookService.is_valid_webhook_config(config) is True
    
    def test_invalid_config_all_empty(self):
        """测试所有URL都为空的配置无效"""
        config = {
            'dingtalk_url': '',
            'feishu_url': None,
            'wecom_url': ''
        }
        assert WebhookService.is_valid_webhook_config(config) is False
    
    def test_invalid_config_none(self):
        """测试None配置无效"""
        assert WebhookService.is_valid_webhook_config(None) is False
    
    def test_invalid_config_whitespace_only(self):
        """测试只有空白字符的URL无效"""
        config = {
            'dingtalk_url': '   ',
            'feishu_url': '\n\t',
            'wecom_url': ''
        }
        assert WebhookService.is_valid_webhook_config(config) is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
