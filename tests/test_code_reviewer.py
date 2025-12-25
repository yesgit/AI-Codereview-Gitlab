import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from jinja2 import Template

from biz.utils.code_reviewer import CodeReviewer
from biz.utils.db import get_engine
from biz.service.webhook_service import WebhookService


@pytest.fixture(autouse=True)
def mock_llm_client():
    """Mock LLM 客户端以避免需要真实的 API key"""
    with patch('biz.llm.factory.Factory.getClient') as mock_factory:
        mock_client = Mock()
        mock_client.completions.return_value = "测试审查结果"
        mock_factory.return_value = mock_client
        yield mock_client


def setup_module():
    # Use in-memory sqlite for tests
    os.environ['DB_DRIVER'] = 'sqlite'
    os.environ['DB_FILE'] = ':memory:'
    # Clear cached engine so tests create a fresh in-memory engine
    try:
        get_engine.cache_clear()
    except Exception:
        pass
    WebhookService.init_db()


def test_jinja2_rendering_with_database_prompt(mock_llm_client):
    """测试从数据库读取的 Jinja2 模板是否被正确渲染"""
    # 设置测试环境变量
    os.environ['REVIEW_STYLE'] = 'professional'
    
    # 创建包含 Jinja2 语法的测试 prompt
    system_prompt = """你是一位资深的软件工程师。
{% if style == 'professional' %}
请使用专业的工程术语。
{% elif style == 'sarcastic' %}
请使用讽刺性语言。
{% elif style == 'gentle' %}
请使用温和措辞。
{% elif style == 'humorous' %}
请使用幽默元素。
{% endif %}
"""
    
    user_prompt = """请审查以下代码：
{% if style == 'professional' %}
重点关注代码质量和架构。
{% elif style == 'sarcastic' %}
大胆指出问题。
{% elif style == 'gentle' %}
温和地提出建议。
{% elif style == 'humorous' %}
有趣地分析代码。
{% endif %}
"""
    
    # 创建数据库映射
    WebhookService.create_or_update_webhook_mapping(
        project_name='test-project',
        url_slug='test-slug',
        custom_prompt_system=system_prompt,
        custom_prompt_user=user_prompt
    )
    
    # 创建 CodeReviewer 实例（使用 fixture 中的 mock）
    reviewer = CodeReviewer()
    
    # 调用 review_code
    result = reviewer.review_code(
        diffs_text="测试代码变更",
        commits_text="测试提交",
        project_name='test-project'
    )
    
    # 验证 LLM 被调用
    assert mock_llm_client.completions.called
    
    # 获取发送给 LLM 的 messages
    call_args = mock_llm_client.completions.call_args
    messages = call_args[1]['messages']
    
    # 检查 system_prompt 是否被正确渲染
    system_content = messages[0]['content']
    assert '{%' not in system_content, "system_prompt 中不应包含 Jinja2 语法"
    assert '请使用专业的工程术语' in system_content, "应包含 professional 风格的内容"
    assert '请使用讽刺性语言' not in system_content, "不应包含其他风格的内容"
    
    # 检查 user_prompt 是否被正确渲染
    user_content = messages[1]['content']
    assert '{%' not in user_content, "user_prompt 中不应包含 Jinja2 语法"
    assert '重点关注代码质量和架构' in user_content, "应包含 professional 风格的内容"
    assert '大胆指出问题' not in user_content, "不应包含其他风格的内容"
    
    print("✅ Jinja2 渲染测试通过 - professional 风格")


def test_jinja2_rendering_with_different_styles(mock_llm_client):
    """测试不同 style 参数的渲染结果"""
    test_cases = [
        ('professional', '请使用专业的工程术语', '重点关注代码质量和架构'),
        ('sarcastic', '请使用讽刺性语言', '大胆指出问题'),
        ('gentle', '请使用温和措辞', '温和地提出建议'),
        ('humorous', '请使用幽默元素', '有趣地分析代码'),
    ]
    
    for style, expected_system, expected_user in test_cases:
        # 设置环境变量
        os.environ['REVIEW_STYLE'] = style
        
        # 创建包含 Jinja2 语法的测试 prompt
        system_prompt = """{% if style == 'professional' %}请使用专业的工程术语。{% elif style == 'sarcastic' %}请使用讽刺性语言。{% elif style == 'gentle' %}请使用温和措辞。{% elif style == 'humorous' %}请使用幽默元素。{% endif %}"""
        user_prompt = """{% if style == 'professional' %}重点关注代码质量和架构。{% elif style == 'sarcastic' %}大胆指出问题。{% elif style == 'gentle' %}温和地提出建议。{% elif style == 'humorous' %}有趣地分析代码。{% endif %}"""
        
        # 创建数据库映射
        WebhookService.create_or_update_webhook_mapping(
            project_name=f'test-project-{style}',
            url_slug=f'test-slug-{style}',
            custom_prompt_system=system_prompt,
            custom_prompt_user=user_prompt
        )
        
        # 创建 CodeReviewer 实例（使用 fixture 中的 mock）
        reviewer = CodeReviewer()
        
        # 调用 review_code
        reviewer.review_code(
            diffs_text="测试代码变更",
            commits_text="测试提交",
            project_name=f'test-project-{style}'
        )
        
        # 获取发送给 LLM 的 messages
        call_args = mock_llm_client.completions.call_args
        messages = call_args[1]['messages']
        
        # 检查渲染结果
        system_content = messages[0]['content']
        user_content = messages[1]['content']
        
        assert '{%' not in system_content, f"{style} 风格: system_prompt 中不应包含 Jinja2 语法"
        assert '{%' not in user_content, f"{style} 风格: user_prompt 中不应包含 Jinja2 语法"
        assert expected_system in system_content, f"{style} 风格: 应包含 '{expected_system}'"
        assert expected_user in user_content, f"{style} 风格: 应包含 '{expected_user}'"
        
        print(f"✅ Jinja2 渲染测试通过 - {style} 风格")


def test_jinja2_rendering_with_complex_template(mock_llm_client):
    """测试复杂模板的渲染"""
    os.environ['REVIEW_STYLE'] = 'professional'
    
    # 创建复杂的 Jinja2 模板
    complex_prompt = """你是一位代码审查专家。
当前风格：{{ style }}

{% if style == 'professional' %}
审查重点：
1. 代码质量
2. 架构设计
3. 安全性
{% elif style == 'sarcastic' %}
哦，又是你的代码？让我们看看这次又有什么"惊喜"。
{% elif style == 'gentle' %}
建议关注以下方面：
- 代码规范
- 最佳实践
- 可维护性
{% elif style == 'humorous' %}
🎯 让我们愉快地审查代码吧！
🐛 找bug就像找彩蛋
{% endif %}

请提供详细的审查报告。"""
    
    # 创建数据库映射
    WebhookService.create_or_update_webhook_mapping(
        project_name='test-complex',
        url_slug='test-complex-slug',
        custom_prompt_system=complex_prompt,
        custom_prompt_user="请审查代码。"
    )
    
    # 创建 CodeReviewer 实例（使用 fixture 中的 mock）
    reviewer = CodeReviewer()
    
    # 调用 review_code
    reviewer.review_code(
        diffs_text="测试代码变更",
        commits_text="测试提交",
        project_name='test-complex'
    )
    
    # 获取发送给 LLM 的 messages
    call_args = mock_llm_client.completions.call_args
    messages = call_args[1]['messages']
    
    # 检查渲染结果
    system_content = messages[0]['content']
    
    # 验证 Jinja2 变量被替换
    assert '{{ style }}' not in system_content, "变量 {{ style }} 应被替换"
    assert '当前风格：professional' in system_content, "应包含替换后的变量值"
    
    # 验证条件语句被正确渲染
    assert '{%' not in system_content, "不应包含 Jinja2 语法"
    assert '审查重点：' in system_content, "应包含 professional 风格的内容"
    assert '1. 代码质量' in system_content
    assert '2. 架构设计' in system_content
    assert '3. 安全性' in system_content
    
    # 验证其他分支不被渲染
    assert '又是你的代码' not in system_content
    assert '建议关注以下方面' not in system_content
    assert '愉快地审查代码' not in system_content
    
    print("✅ 复杂模板渲染测试通过")


def test_render_without_jinja2_syntax(mock_llm_client):
    """测试不包含 Jinja2 语法的 prompt 也能正常工作"""
    os.environ['REVIEW_STYLE'] = 'professional'
    
    # 创建不包含 Jinja2 语法的 prompt
    simple_system = "你是一位代码审查专家，请审查以下代码。"
    simple_user = "代码变更内容："
    
    # 创建数据库映射
    WebhookService.create_or_update_webhook_mapping(
        project_name='test-simple',
        url_slug='test-simple-slug',
        custom_prompt_system=simple_system,
        custom_prompt_user=simple_user
    )
    
    # 创建 CodeReviewer 实例（使用 fixture 中的 mock）
    reviewer = CodeReviewer()
    
    # 调用 review_code
    result = reviewer.review_code(
        diffs_text="测试代码变更",
        commits_text="测试提交",
        project_name='test-simple'
    )
    
    # 获取发送给 LLM 的 messages
    call_args = mock_llm_client.completions.call_args
    messages = call_args[1]['messages']
    
    # 检查渲染结果
    system_content = messages[0]['content']
    user_content = messages[1]['content']
    
    # 简单的 prompt 应该保持不变
    assert system_content == simple_system
    assert '代码变更内容：' in user_content
    
    print("✅ 无 Jinja2 语法测试通过")


def test_fallback_to_default_prompt(mock_llm_client):
    """测试当数据库中没有自定义 prompt 时，使用默认 prompt"""
    os.environ['REVIEW_STYLE'] = 'professional'
    
    # 创建 CodeReviewer 实例（使用 fixture 中的 mock）
    reviewer = CodeReviewer()
    
    # 调用 review_code，使用不存在的项目名称
    result = reviewer.review_code(
        diffs_text="测试代码变更",
        commits_text="测试提交",
        project_name='nonexistent-project'
    )
    
    # 获取发送给 LLM 的 messages
    call_args = mock_llm_client.completions.call_args
    messages = call_args[1]['messages']
    
    # 应该使用默认的 prompts
    system_content = messages[0]['content']
    assert '代码审查目标' in system_content or '资深软件开发工程师' in system_content
    
    print("✅ 默认 prompt 回退测试通过")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
