"""
测试 URL 规范化（去除尾随斜杠）功能
确保 gitlab_base_url 的尾随斜杠不影响配置匹配
"""
import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def test_db():
    """创建临时测试数据库"""
    # 为每个测试使用不同的数据库名称
    import uuid
    db_name = f'test_url_norm_{uuid.uuid4().hex}.db'
    db_path = os.path.join(tempfile.gettempdir(), db_name)
    os.environ['DB_PATH'] = db_path
    
    # 清理旧的数据库文件（如果存在）
    try:
        if os.path.exists(db_path):
            os.unlink(db_path)
    except:
        pass
    
    yield db_path
    try:
        if os.path.exists(db_path):
            os.unlink(db_path)
    except:
        pass


def test_webhook_url_normalization(test_db):
    """测试 WebhookService 对 URL 的规范化"""
    from biz.service.webhook_service import WebhookService
    from sqlalchemy import text
    
    # 初始化数据库
    WebhookService.init_db()
    
    # 创建配置（无尾随斜杠）
    config = WebhookService.create_or_update_webhook_mapping(
        gitlab_base_url='https://gitlab.example.com',
        project_slug='test-project',
        project_name='Test Project',
        dingtalk_url='https://oapi.dingtalk.com/test'
    )
    
    assert config is not None
    
    # 使用带尾随斜杠的 URL 查询 - 应该能匹配到
    matched_config = WebhookService.get_webhook_mapping_by_gitlab_project(
        'https://gitlab.example.com/',  # 有尾随斜杠
        'test-project'
    )
    
    assert matched_config is not None
    assert matched_config['id'] == config['id']


def test_branch_webhook_url_normalization(test_db):
    """测试 BranchWebhookService 对 URL 的规范化"""
    from biz.service.branch_webhook_service import BranchWebhookService
    
    # 初始化数据库
    BranchWebhookService.init_db()
    
    # 创建配置（无尾随斜杠）
    config = BranchWebhookService.create_or_update_branch_webhook(
        gitlab_base_url='https://gitlab.example.com',
        project_slug='test-project',
        branch_pattern='main',
        dingtalk_url='https://oapi.dingtalk.com/test'
    )
    
    assert config is not None
    
    # 使用带尾随斜杠的 URL 匹配 - 应该能匹配到
    matched_config = BranchWebhookService.match_branch_webhook(
        'https://gitlab.example.com/',  # 有尾随斜杠
        'test-project',
        'main'
    )
    
    assert matched_config is not None
    assert matched_config['id'] == config['id']


def test_webhook_config_fallback_with_trailing_slash(test_db):
    """测试 get_webhook_config_with_fallback 对 URL 的规范化"""
    from biz.service.webhook_service import WebhookService
    from unittest.mock import patch
    
    # 初始化数据库
    WebhookService.init_db()
    
    # 创建项目配置（无尾随斜杠）
    config = WebhookService.create_or_update_webhook_mapping(
        gitlab_base_url='https://gitlab.example.com',
        project_slug='test-project',
        project_name='Test Project',
        feishu_url='https://open.feishu.cn/test'
    )
    
    assert config is not None
    
    # 使用带尾随斜杠的 URL 查询配置 - 应该能匹配到
    with patch.dict(os.environ, {'FEISHU_ENABLED': '1'}):
        result_config = WebhookService.get_webhook_config_with_fallback(
            gitlab_base_url='https://gitlab.example.com/',  # 有尾随斜杠
            project_slug='test-project'
        )
    
    assert result_config is not None
    assert result_config.get('feishu_url') == 'https://open.feishu.cn/test'
