"""
测试评审风格（review_style）功能
验证每个项目、分支可以设置自己的评审风格
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from biz.service.branch_webhook_service import BranchWebhookService
from biz.utils.code_reviewer import VALID_REVIEW_STYLES, resolve_random_style


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
    
    valid_styles = ['professional', 'sarcastic', 'gentle', 'humorous', 'random']
    
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


class TestRandomReviewStyle:
    """测试随机评审风格功能"""
    
    def test_valid_review_styles_constant(self):
        """测试 VALID_REVIEW_STYLES 常量包含所有预期风格"""
        expected_styles = ['professional', 'sarcastic', 'gentle', 'humorous']
        assert VALID_REVIEW_STYLES == expected_styles
    
    @patch('biz.utils.code_reviewer.random.choice')
    def test_resolve_random_style_with_random(self, mock_choice):
        """测试 resolve_random_style 遇到 'random' 时会调用 random.choice"""
        mock_choice.return_value = 'sarcastic'
        result = resolve_random_style('random')
        assert result == 'sarcastic'
        mock_choice.assert_called_once_with(VALID_REVIEW_STYLES)
    
    def test_resolve_random_style_with_specific_style(self):
        """测试 resolve_random_style 遇到具体风格时直接返回"""
        result = resolve_random_style('professional')
        assert result == 'professional'
    
    @patch.dict(os.environ, {'REVIEW_STYLE': 'gentle'})
    def test_resolve_random_style_with_none(self):
        """测试 resolve_random_style 遇到 None 时使用环境变量"""
        result = resolve_random_style(None)
        assert result == 'gentle'
    
    @patch.dict(os.environ, {}, clear=True)
    def test_resolve_random_style_default(self):
        """测试 resolve_random_style 没有环境变量时使用默认值"""
        result = resolve_random_style(None)
        assert result == 'professional'
    
    @patch('biz.utils.code_reviewer.random.choice')
    @patch('biz.utils.code_reviewer.open')
    @patch('biz.utils.code_reviewer.yaml.safe_load')
    @patch('biz.utils.code_reviewer.Factory')
    def test_random_style_selects_valid_style(self, mock_factory, mock_yaml_load, mock_open, mock_random_choice):
        """测试随机风格会从有效风格列表中选择一个"""
        from biz.utils.code_reviewer import CodeReviewer
        
        # 模拟 LLM client
        mock_client = MagicMock()
        mock_factory.return_value.getClient.return_value = mock_client
        
        # 模拟随机选择返回 'sarcastic'
        mock_random_choice.return_value = 'sarcastic'
        
        # 模拟 YAML 文件内容
        mock_yaml_load.return_value = {
            "code_review_prompt": {
                "system_prompt": "你是一位资深的软件开发工程师。整个评论要保持{{ style }}风格",
                "user_prompt": "以下是代码变更：{diffs_text}"
            }
        }
        
        # 创建 CodeReviewer 实例，传入 random 风格（通过设置环境变量）
        import os
        os.environ['REVIEW_STYLE'] = 'random'
        reviewer = CodeReviewer()
        
        # 验证 random.choice 被调用，参数是 VALID_REVIEW_STYLES
        mock_random_choice.assert_called_once_with(VALID_REVIEW_STYLES)
        
        # 验证最终的提示词中包含随机选择的风格
        assert 'sarcastic' in reviewer.prompts['system_message']['content']
    
    @patch('biz.utils.code_reviewer.random.choice')
    @patch('biz.utils.code_reviewer.open')
    @patch('biz.utils.code_reviewer.yaml.safe_load')
    @patch('biz.utils.code_reviewer.Factory')
    def test_random_style_is_replaced_in_prompt(self, mock_factory, mock_yaml_load, mock_open, mock_random_choice):
        """测试随机风格会被正确替换到提示词中"""
        from biz.utils.code_reviewer import CodeReviewer
        
        # 模拟 LLM client
        mock_client = MagicMock()
        mock_factory.return_value.getClient.return_value = mock_client
        
        # 模拟随机选择返回 'humorous'
        mock_random_choice.return_value = 'humorous'
        
        # 模拟 YAML 文件内容
        mock_yaml_load.return_value = {
            "code_review_prompt": {
                "system_prompt": "整个评论要保持{{ style }}风格",
                "user_prompt": "以下是代码变更：{diffs_text}"
            }
        }
        
        # 创建 CodeReviewer 实例，传入 random 风格（通过设置环境变量）
        import os
        os.environ['REVIEW_STYLE'] = 'random'
        reviewer = CodeReviewer()
        
        # 验证提示词中的 {{ style }} 被 'humorous' 替换
        system_content = reviewer.prompts['system_message']['content']
        assert 'humorous' in system_content
        assert '{{ style }}' not in system_content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
