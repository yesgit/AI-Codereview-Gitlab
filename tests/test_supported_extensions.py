"""测试 supported_extensions 功能"""
import os
import pytest
from unittest.mock import patch, MagicMock

from biz.service.webhook_service import WebhookService
from biz.service.branch_webhook_service import BranchWebhookService
from biz.platforms.gitlab.webhook_handler import get_supported_extensions, filter_changes, normalize_extensions


def test_get_supported_extensions_from_config():
    """测试从配置获取支持的文件扩展名"""
    # 测试环境变量配置
    with patch.dict(os.environ, {'SUPPORTED_EXTENSIONS': '.java,.py,.js'}):
        exts = get_supported_extensions(None, None)
        assert exts == ['.java', '.py', '.js']


def test_get_supported_extensions_from_webhook():
    """测试从项目 webhook 配置获取支持的文件扩展名"""
    # 模拟项目 webhook 配置
    mock_config = {
        'gitlab_base_url': 'https://gitlab.com',
        'project_slug': 'test/project',
        'supported_extensions': '.java,.go,.ts'
    }
    
    with patch.object(WebhookService, 'get_webhook_mapping_by_gitlab_project', return_value=mock_config):
        exts = get_supported_extensions('https://gitlab.com', 'test/project')
        assert exts == ['.java', '.go', '.ts']


def test_get_supported_extensions_from_branch():
    """测试从分支 webhook 配置获取支持的文件扩展名（优先级更高）"""
    # 模拟分支 webhook 配置
    branch_config = {
        'gitlab_base_url': 'https://gitlab.com',
        'project_slug': 'test/project',
        'branch_pattern': 'feature/*',
        'supported_extensions': '.ts,.vue,.go'
    }
    
    with patch.object(BranchWebhookService, 'match_branch_webhook', return_value=branch_config):
        exts = get_supported_extensions('https://gitlab.com', 'test/project', branch_name='feature/test')
        # 分支配置应该覆盖项目配置
        assert exts == ['.ts', '.vue', '.go']


def test_filter_changes_with_extensions():
    """测试使用扩展名过滤文件变更"""
    # 模拟文件变更
    changes = [
        {'old_path': 'src/main.java', 'new_path': 'src/main.java', 'diff': 'diff1'},
        {'old_path': 'src/utils.py', 'new_path': 'src/utils.py', 'diff': 'diff2'},
        {'old_path': 'README.md', 'new_path': 'README.md', 'diff': 'diff3'},
        {'old_path': 'config.yml', 'new_path': 'config.yml', 'diff': 'diff4'},
    ]
    
    # 只评审 .java 和 .py 文件
    with patch.dict(os.environ, {'SUPPORTED_EXTENSIONS': '.java,.py'}):
        filtered = filter_changes(changes, 'https://gitlab.com', 'test/project')
        
        assert len(filtered) == 2
        paths = [change['new_path'] for change in filtered]
        assert 'src/main.java' in paths
        assert 'src/utils.py' in paths
        assert 'README.md' not in paths
        assert 'config.yml' not in paths


def test_filter_changes_all_extensions():
    """测试不限制扩展名时过滤所有变更"""
    changes = [
        {'old_path': 'src/main.java', 'new_path': 'src/main.java', 'diff': 'diff1'},
        {'old_path': 'README.md', 'new_path': 'README.md', 'diff': 'diff2'},
    ]
    
    # 使用环境变量设置多个扩展名
    with patch.dict(os.environ, {'SUPPORTED_EXTENSIONS': '.java,.md,.py,.js'}):
        filtered = filter_changes(changes, 'https://gitlab.com', 'test/project')
        # 应该包含两个文件
        assert len(filtered) >= 2


def test_extensions_string_parsing():
    """测试扩展名字符串解析"""
    # 测试不同格式的字符串
    test_cases = [
        ('.java,.py,.js', ['.java', '.py', '.js']),
        ('.java, .py, .js', ['.java', '.py', '.js']),
        ('.java,.py,.js,', ['.java', '.py', '.js']),  # 末尾逗号
        ('java,py,js', ['java', 'py', 'js']),  # 无点号
        ('', []),  # 空字符串
    ]
    
    for input_str, expected in test_cases:
        result = [ext.strip() for ext in input_str.split(',') if ext.strip()]
        assert result == expected, f"Failed for input: {input_str}, got {result}, expected {expected}"



# ==================== 容错机制测试 ====================

class TestNormalizeExtensions:
    """测试扩展名规范化函数的容错逻辑"""
    
    def test_auto_add_dot(self):
        """测试自动添加点号"""
        # 缺少点号的扩展名应该自动添加
        result = normalize_extensions("java,py,js", "测试配置")
        assert result == ['.java', '.py', '.js']
    
    def test_case_normalization(self):
        """测试大小写转换"""
        # 混合大小写应该转换为小写
        result = normalize_extensions(".JAVA,.Py,.JS", "测试配置")
        assert result == ['.java', '.py', '.js']
    
    def test_skip_empty_values(self):
        """测试跳过空值"""
        # 连续逗号和空值应该被跳过
        result = normalize_extensions(".java,, .py,  ,.js", "测试配置")
        assert result == ['.java', '.py', '.js']
    
    def test_deduplication(self):
        """测试去重"""
        # 重复的扩展名应该去重
        result = normalize_extensions(".java,.py,.java,.js,.py", "测试配置")
        assert result == ['.java', '.py', '.js']
        assert len(result) == 3
    
    def test_filter_invalid_extensions(self):
        """测试过滤无效扩展名"""
        # 包含非法字符的扩展名应该被过滤
        result = normalize_extensions(".java,.py#,.js!,.go", "测试配置")
        assert '.java' in result
        assert '.go' in result
        assert '.py#' not in result
        assert '.js!' not in result
    
    def test_valid_extensions_pattern(self):
        """测试有效扩展名格式"""
        # 有效的扩展名应该被接受
        result = normalize_extensions(".java,.py,.ts,.js,.tsx,.jsx,.go,.rs", "测试配置")
        assert len(result) == 8
        assert '.tsx' in result
        assert '.jsx' in result
    
    def test_empty_string(self):
        """测试空字符串"""
        result = normalize_extensions("", "测试配置")
        assert result == []
    
    def test_whitespace_only(self):
        """测试只有空格"""
        result = normalize_extensions("   ", "测试配置")
        assert result == []
    
    def test_all_invalid(self):
        """测试全部无效的情况"""
        # 所有扩展名都无效时应该返回空列表
        result = normalize_extensions(".java!,.py#,.js$", "测试配置")
        assert result == []


class TestFallbackMechanism:
    """测试降级机制"""
    
    def test_fallback_to_project_when_branch_empty(self):
        """测试分支配置为空时降级到项目配置"""
        # 分支配置返回 None 或空配置
        with patch.object(BranchWebhookService, 'match_branch_webhook', return_value=None):
            mock_project_config = {
                'gitlab_base_url': 'https://gitlab.com',
                'project_slug': 'test/project',
                'supported_extensions': '.java,.py'
            }
            with patch.object(WebhookService, 'get_webhook_mapping_by_gitlab_project', return_value=mock_project_config):
                exts = get_supported_extensions('https://gitlab.com', 'test/project', branch_name='feature/test')
                assert exts == ['.java', '.py']
    
    def test_fallback_to_env_when_project_empty(self):
        """测试项目配置为空时降级到环境变量"""
        # 分支和项目配置都为空
        with patch.object(BranchWebhookService, 'match_branch_webhook', return_value=None):
            with patch.object(WebhookService, 'get_webhook_mapping_by_gitlab_project', return_value=None):
                with patch.dict(os.environ, {'SUPPORTED_EXTENSIONS': '.ts,.js'}):
                    exts = get_supported_extensions('https://gitlab.com', 'test/project', branch_name='feature/test')
                    assert exts == ['.ts', '.js']
    
    def test_fallback_to_default_when_all_empty(self):
        """测试所有配置都为空时降级到硬编码默认值"""
        # 所有配置都为空
        with patch.object(BranchWebhookService, 'match_branch_webhook', return_value=None):
            with patch.object(WebhookService, 'get_webhook_mapping_by_gitlab_project', return_value=None):
                with patch.dict(os.environ, {'SUPPORTED_EXTENSIONS': ''}, clear=False):
                    exts = get_supported_extensions('https://gitlab.com', 'test/project', branch_name='feature/test')
                    # 应该返回硬编码默认值
                    assert exts == ['.java', '.py', '.php']
    
    def test_fallback_when_all_invalid(self):
        """测试配置全部无效时降级"""
        # 分支配置包含无效扩展名，应该跳过并降级
        invalid_config = {
            'gitlab_base_url': 'https://gitlab.com',
            'project_slug': 'test/project',
            'supported_extensions': '.java!,.py#'
        }
        with patch.object(BranchWebhookService, 'match_branch_webhook', return_value=invalid_config):
            with patch.dict(os.environ, {'SUPPORTED_EXTENSIONS': '.ts,.js'}):
                exts = get_supported_extensions('https://gitlab.com', 'test/project', branch_name='feature/test')
                # 应该降级到环境变量（因为分支配置解析为空）
                assert exts == ['.ts', '.js']


class TestEdgeCases:
    """测试边缘情况"""
    
    def test_filter_changes_with_empty_extensions(self):
        """测试扩展名列表为空时的过滤"""
        changes = [
            {'old_path': 'src/main.java', 'new_path': 'src/main.java', 'diff': 'diff1'},
            {'old_path': 'README.md', 'new_path': 'README.md', 'diff': 'diff2'},
        ]
        
        # 模拟 get_supported_extensions 返回空列表
        with patch('biz.platforms.gitlab.webhook_handler.get_supported_extensions', return_value=[]):
            filtered = filter_changes(changes, 'https://gitlab.com', 'test/project')
            # 应该没有文件被过滤
            assert len(filtered) == 0
    
    def test_config_with_whitespace(self):
        """测试配置包含多余空格"""
        # 配置字符串包含多余空格
        result = normalize_extensions("  .java  ,  .py  ,  .js  ", "测试配置")
        assert result == ['.java', '.py', '.js']
    
    def test_mixed_valid_invalid(self):
        """测试混合有效和无效扩展名"""
        # 部分有效，部分无效
        result = normalize_extensions(".java,.py!,.go,.js#,.ts", "测试配置")
        assert '.java' in result
        assert '.go' in result
        assert '.ts' in result
        assert '.py!' not in result
        assert '.js#' not in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
