"""
测试分支级 Webhook 配置服务
验证通配符匹配、优先级排序等核心逻辑
"""
import pytest
from unittest.mock import Mock, patch
from biz.service.branch_webhook_service import BranchWebhookService


class TestBranchWebhookMatching:
    """测试分支匹配逻辑"""
    
    def setup_method(self):
        """每个测试前的设置"""
        self.gitlab_base_url = "https://gitlab.com"
        self.project_slug = "mygroup/myproject"
    
    @patch('biz.service.branch_webhook_service.BranchWebhookService.get_all_branch_webhooks')
    def test_exact_match_priority(self, mock_get_all):
        """测试精确匹配优先于通配符匹配"""
        # 模拟数据库返回的配置
        mock_get_all.return_value = [
            {
                'id': 1,
                'gitlab_base_url': self.gitlab_base_url,
                'project_slug': self.project_slug,
                'branch_pattern': 'main',
                'dingtalk_url': 'https://exact-match-webhook',
                'feishu_url': None,
                'wecom_url': None
            },
            {
                'id': 2,
                'gitlab_base_url': self.gitlab_base_url,
                'project_slug': self.project_slug,
                'branch_pattern': 'mai*',  # 通配符也能匹配
                'dingtalk_url': 'https://wildcard-webhook',
                'feishu_url': None,
                'wecom_url': None
            }
        ]
        
        result = BranchWebhookService.match_branch_webhook(
            self.gitlab_base_url, self.project_slug, 'main'
        )
        
        assert result is not None
        assert result['branch_pattern'] == 'main'  # 精确匹配优先
        assert result['dingtalk_url'] == 'https://exact-match-webhook'
    
    @patch('biz.service.branch_webhook_service.BranchWebhookService.get_all_branch_webhooks')
    def test_longest_wildcard_priority(self, mock_get_all):
        """测试最长通配符模式优先匹配"""
        mock_get_all.return_value = [
            {
                'id': 1,
                'gitlab_base_url': self.gitlab_base_url,
                'project_slug': self.project_slug,
                'branch_pattern': 'feature/*',  # 长度 9
                'dingtalk_url': 'https://feature-webhook',
                'feishu_url': None,
                'wecom_url': None
            },
            {
                'id': 2,
                'gitlab_base_url': self.gitlab_base_url,
                'project_slug': self.project_slug,
                'branch_pattern': 'feature/user/*',  # 长度 14，更长更具体
                'dingtalk_url': 'https://feature-user-webhook',
                'feishu_url': None,
                'wecom_url': None
            }
        ]
        
        result = BranchWebhookService.match_branch_webhook(
            self.gitlab_base_url, self.project_slug, 'feature/user/login'
        )
        
        assert result is not None
        assert result['branch_pattern'] == 'feature/user/*'  # 最长模式优先
        assert result['dingtalk_url'] == 'https://feature-user-webhook'
    
    @patch('biz.service.branch_webhook_service.BranchWebhookService.get_all_branch_webhooks')
    def test_wildcard_pattern_matching(self, mock_get_all):
        """测试各种通配符模式匹配"""
        mock_get_all.return_value = [
            {
                'id': 1,
                'gitlab_base_url': self.gitlab_base_url,
                'project_slug': self.project_slug,
                'branch_pattern': 'feature/*',
                'dingtalk_url': 'https://feature-webhook',
                'feishu_url': None,
                'wecom_url': None
            }
        ]
        
        # 应该匹配单级路径
        result = BranchWebhookService.match_branch_webhook(
            self.gitlab_base_url, self.project_slug, 'feature/login'
        )
        assert result is not None
        assert result['dingtalk_url'] == 'https://feature-webhook'
        
        # 注意：fnmatch中的 * 也会匹配 /，所以多级路径也会匹配
        result = BranchWebhookService.match_branch_webhook(
            self.gitlab_base_url, self.project_slug, 'feature/user/login'
        )
        assert result is not None  # feature/* 在fnmatch中会匹配多级路径
        assert result['dingtalk_url'] == 'https://feature-webhook'
        
        # 不应该匹配不同前缀
        result = BranchWebhookService.match_branch_webhook(
            self.gitlab_base_url, self.project_slug, 'hotfix/bug'
        )
        assert result is None
    
    @patch('biz.service.branch_webhook_service.BranchWebhookService.get_all_branch_webhooks')
    def test_no_match_returns_none(self, mock_get_all):
        """测试无匹配时返回None"""
        mock_get_all.return_value = [
            {
                'id': 1,
                'gitlab_base_url': self.gitlab_base_url,
                'project_slug': self.project_slug,
                'branch_pattern': 'feature/*',
                'dingtalk_url': 'https://feature-webhook',
                'feishu_url': None,
                'wecom_url': None
            }
        ]
        
        result = BranchWebhookService.match_branch_webhook(
            self.gitlab_base_url, self.project_slug, 'hotfix/bug'
        )
        
        assert result is None
    
    @patch('biz.service.branch_webhook_service.BranchWebhookService.get_all_branch_webhooks')
    def test_empty_configs_returns_none(self, mock_get_all):
        """测试空配置列表返回None"""
        mock_get_all.return_value = []
        
        result = BranchWebhookService.match_branch_webhook(
            self.gitlab_base_url, self.project_slug, 'main'
        )
        
        assert result is None
    
    @patch('biz.service.branch_webhook_service.BranchWebhookService.get_all_branch_webhooks')
    def test_question_mark_wildcard(self, mock_get_all):
        """测试问号通配符匹配单个字符"""
        mock_get_all.return_value = [
            {
                'id': 1,
                'gitlab_base_url': self.gitlab_base_url,
                'project_slug': self.project_slug,
                'branch_pattern': 'release/v?.?',
                'dingtalk_url': 'https://release-webhook',
                'feishu_url': None,
                'wecom_url': None
            }
        ]
        
        # 应该匹配
        result = BranchWebhookService.match_branch_webhook(
            self.gitlab_base_url, self.project_slug, 'release/v1.0'
        )
        assert result is not None
        
        # 不应该匹配（字符数不对）
        result = BranchWebhookService.match_branch_webhook(
            self.gitlab_base_url, self.project_slug, 'release/v10.0'
        )
        assert result is None


class TestBranchWebhookPriority:
    """测试分支配置优先级排序"""
    
    @patch('biz.service.branch_webhook_service.BranchWebhookService.get_all_branch_webhooks')
    def test_priority_order(self, mock_get_all):
        """测试优先级顺序：精确 > 长通配符 > 短通配符"""
        mock_get_all.return_value = [
            {'branch_pattern': 'f*', 'dingtalk_url': 'url1'},  # 最短
            {'branch_pattern': 'feature/*', 'dingtalk_url': 'url2'},  # 中等
            {'branch_pattern': 'feature/user/*', 'dingtalk_url': 'url3'},  # 最长通配符
            {'branch_pattern': 'feature/user/login', 'dingtalk_url': 'url4'},  # 精确
        ]
        
        result = BranchWebhookService.match_branch_webhook(
            'https://gitlab.com', 'mygroup/myproject', 'feature/user/login'
        )
        
        assert result['dingtalk_url'] == 'url4'  # 精确匹配


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
