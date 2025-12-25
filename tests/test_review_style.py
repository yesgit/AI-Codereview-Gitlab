"""
测试评审风格（review_style）功能
验证每个项目、分支可以设置自己的评审风格
"""
import pytest
from unittest.mock import patch, MagicMock
from biz.service.branch_webhook_service import BranchWebhookService


class TestReviewStyleInBranchWebhook:
    """测试分支级 webhook 的 review_style 配置"""
    
    @patch('biz.service.branch_webhook_service.get_engine')
    def test_create_branch_webhook_with_review_style(self, mock_get_engine):
        """测试创建分支 webhook 时可以设置 review_style"""
        mock_conn = MagicMock()
        mock_engine = MagicMock()
        mock_engine.begin.return_value.__enter__.return_value = mock_conn
        mock_get_engine.return_value = mock_engine
        
        # 模拟插入成功
        mock_conn.execute.return_value.mappings.return_value.first.return_value = None
        mock_conn.execute.return_value.lastrowid = 1
        
        result = BranchWebhookService.create_or_update_branch_webhook(
            gitlab_base_url="https://gitlab.com",
            project_slug="mygroup/myproject",
            branch_pattern="feature/*",
            review_style="professional"
        )
        
        assert result is not None
    
    @patch('biz.service.branch_webhook_service.get_engine')
    def test_update_branch_webhook_review_style(self, mock_get_engine):
        """测试更新分支 webhook 的 review_style"""
        mock_conn = MagicMock()
        mock_engine = MagicMock()
        
        # 模拟查询返回记录
        mock_query_result = MagicMock()
        mock_query_result.mappings.return_value.first.return_value = {'id': 1}
        mock_conn.execute.return_value = mock_query_result
        
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_engine.begin.return_value.__enter__.return_value = mock_conn
        mock_get_engine.return_value = mock_engine
        
        result = BranchWebhookService.update_branch_webhook_by_id(
            webhook_id=1,
            gitlab_base_url="https://gitlab.com",
            project_slug="mygroup/myproject",
            branch_pattern="release/*",
            review_style="sarcastic"
        )
        
        assert result is True
    
    @patch('biz.service.branch_webhook_service.BranchWebhookService.get_all_branch_webhooks')
    def test_match_branch_webhook_returns_review_style(self, mock_get_all):
        """测试匹配的分支 webhook 包含 review_style"""
        mock_get_all.return_value = [
            {
                'id': 1,
                'gitlab_base_url': "https://gitlab.com",
                'project_slug': "mygroup/myproject",
                'branch_pattern': 'feature/*',
                'review_style': 'gentle',
                'dingtalk_url': 'https://webhook',
                'feishu_url': None,
                'wecom_url': None
            }
        ]
        
        result = BranchWebhookService.match_branch_webhook(
            "https://gitlab.com", "mygroup/myproject", 'feature/login'
        )
        
        assert result is not None
        assert result['review_style'] == 'gentle'


class TestValidReviewStyles:
    """测试有效的 review_style 值"""
    
    valid_styles = ['professional', 'sarcastic', 'gentle', 'humorous']
    
    @pytest.mark.parametrize('style', valid_styles)
    @patch('biz.service.branch_webhook_service.get_engine')
    def test_valid_review_style_accepted(self, mock_get_engine, style):
        """测试所有有效的 review_style 都可以被接受"""
        mock_conn = MagicMock()
        mock_engine = MagicMock()
        mock_engine.begin.return_value.__enter__.return_value = mock_conn
        mock_get_engine.return_value = mock_engine
        
        mock_conn.execute.return_value.mappings.return_value.first.return_value = None
        mock_conn.execute.return_value.lastrowid = 1
        
        result = BranchWebhookService.create_or_update_branch_webhook(
            gitlab_base_url="https://gitlab.com",
            project_slug="mygroup/myproject",
            branch_pattern="feature/*",
            review_style=style
        )
        
        assert result is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
