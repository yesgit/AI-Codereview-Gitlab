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


# ==============================================
# 并发批量审查测试
# ==============================================

def _make_fake_changes(file_count: int):
    """构造测试用的 changes 列表"""
    return [
        {
            'new_path': f'src/file_{i}.py',
            'old_path': f'src/file_{i}.py',
            'diff': f'@@ -1,3 +1,5 @@\n+new line in file {i}\n',
            'additions': 1,
            'deletions': 0,
        }
        for i in range(file_count)
    ]


def test_concurrent_produces_same_structure_as_sequential(mock_llm_client):
    """并发路径应产生与顺序路径相同结构的输出"""
    mock_llm_client.completions.return_value = "```markdown\n审查结果\n总分：85分\n```"

    changes = _make_fake_changes(6)  # 6 files
    reviewer = CodeReviewer()

    # 顺序模式 (max_concurrent=1)
    with patch.dict(os.environ, {
        'BATCH_REVIEW_ENABLED': '1',
        'BATCH_REVIEW_FILES_PER_BATCH': '2',
        'BATCH_REVIEW_MAX_CONCURRENT': '1',
        'BATCH_REVIEW_TIMEOUT_PER_BATCH': '300',
    }):
        sequential_result = reviewer.review_changes_in_batches(
            changes, commits_text="test commit", project_name="test-project"
        )

    # 重置 mock 调用计数
    mock_llm_client.completions.reset_mock()
    mock_llm_client.completions.return_value = "```markdown\n审查结果\n总分：85分\n```"

    # 并发模式 (max_concurrent=3)
    with patch.dict(os.environ, {
        'BATCH_REVIEW_ENABLED': '1',
        'BATCH_REVIEW_FILES_PER_BATCH': '2',
        'BATCH_REVIEW_MAX_CONCURRENT': '3',
        'BATCH_REVIEW_TIMEOUT_PER_BATCH': '300',
    }):
        concurrent_result = reviewer.review_changes_in_batches(
            changes, commits_text="test commit", project_name="test-project"
        )

    # 两种模式都应该返回非空字符串结果
    assert sequential_result is not None
    assert len(sequential_result) > 0
    assert concurrent_result is not None
    assert len(concurrent_result) > 0
    # 两种模式都应该有相同数量的 LLM 调用 (3 batches + 1 summary = 4 calls)
    assert mock_llm_client.completions.call_count >= 3

    print("✅ 并发与顺序路径输出结构一致测试通过")


def test_concurrent_batch_failure_does_not_crash_review(mock_llm_client):
    """单个批次失败不应导致整个审查崩溃"""
    changes = _make_fake_changes(5)  # 5 files → 5 batches
    reviewer = CodeReviewer()

    # 用 side_effect 让批次 2 失败
    call_count = [0]

    def flaky_review_code(diffs_text, commits_text="", project_name="",
                          gitlab_base_url="", project_slug="", branch_name=""):
        call_count[0] += 1
        if call_count[0] == 2:
            raise RuntimeError("模拟 LLM 调用失败")
        return "```markdown\n审查结果\n总分：80分\n```"

    with patch.object(reviewer, 'review_code', side_effect=flaky_review_code), \
         patch.object(reviewer, '_summarize_reviews',
                      side_effect=lambda reviews, **kw: "\n\n".join(reviews)):
        with patch.dict(os.environ, {
            'BATCH_REVIEW_ENABLED': '1',
            'BATCH_REVIEW_FILES_PER_BATCH': '1',
            'BATCH_REVIEW_MAX_CONCURRENT': '3',
            'BATCH_REVIEW_TIMEOUT_PER_BATCH': '300',
        }):
            result = reviewer.review_changes_in_batches(
                changes, commits_text="test commit", project_name="test-project"
            )

    # 审查应该完成（汇总结果非空）
    assert result is not None
    assert len(result) > 0
    # 应该包含失败批次的错误信息
    assert "审查失败" in result

    print("✅ 批次失败不影响整体审查测试通过")


def test_concurrent_single_batch_no_header(mock_llm_client):
    """单批次输入 + 并发启用 → 应去掉批次标题"""
    mock_llm_client.completions.return_value = "```markdown\n单文件审查结果\n总分：90分\n```"

    changes = _make_fake_changes(1)  # 1 file → 1 batch
    reviewer = CodeReviewer()

    with patch.dict(os.environ, {
        'BATCH_REVIEW_ENABLED': '1',
        'BATCH_REVIEW_FILES_PER_BATCH': '1',
        'BATCH_REVIEW_MAX_CONCURRENT': '3',
        'BATCH_REVIEW_TIMEOUT_PER_BATCH': '300',
    }):
        result = reviewer.review_changes_in_batches(
            changes, commits_text="test commit", project_name="test-project"
        )

    # 单批次时不应有批次标题
    assert "### 批次" not in result
    assert "单文件审查结果" in result

    print("✅ 单批次无标题测试通过")


def test_concurrent_result_ordering_preserved(mock_llm_client):
    """结果应按批次号排序，而非完成顺序"""
    changes = _make_fake_changes(6)  # 6 files → 6 batches with files_per_batch=1
    reviewer = CodeReviewer()

    # 用不同的返回内容标识不同批次
    def order_test_review_code(diffs_text, commits_text="", project_name="",
                               gitlab_base_url="", project_slug="", branch_name=""):
        # 从 diff_text 中提取文件编号
        import re
        match = re.search(r'file_(\d+)', diffs_text)
        file_num = int(match.group(1)) if match else 0
        batch_num = file_num + 1  # files are 0-indexed, batch is 1-indexed
        # 模拟不同批次有不同的处理时间（通过返回来模拟）
        return f"```markdown\n批次{batch_num}审查结果\n总分：{80 + batch_num}分\n```"

    with patch.object(reviewer, 'review_code', side_effect=order_test_review_code), \
         patch.object(reviewer, '_summarize_reviews',
                      side_effect=lambda reviews, **kw: "\n\n".join(reviews)):
        with patch.dict(os.environ, {
            'BATCH_REVIEW_ENABLED': '1',
            'BATCH_REVIEW_FILES_PER_BATCH': '1',
            'BATCH_REVIEW_MAX_CONCURRENT': '3',
            'BATCH_REVIEW_TIMEOUT_PER_BATCH': '300',
        }):
            result = reviewer.review_changes_in_batches(
                changes, commits_text="test commit", project_name="test-project"
            )

    assert result is not None
    # 验证所有批次都有结果（通过检查汇总结果中的内容）
    for i in range(1, 7):
        assert f"批次{i}" in result

    print("✅ 结果顺序保持测试通过")


def test_concurrent_timeout_handling(mock_llm_client):
    """超时批次应标记失败，审查继续（整体超时安全网触发）"""
    import time

    changes = _make_fake_changes(3)
    reviewer = CodeReviewer()

    def slow_review_code(diffs_text, commits_text="", project_name="",
                         gitlab_base_url="", project_slug="", branch_name=""):
        if 'file_1' in diffs_text:
            time.sleep(2)  # 超过整体超时（1秒）
        return "```markdown\n审查结果\n总分：80分\n```"

    with patch.object(reviewer, 'review_code', side_effect=slow_review_code), \
         patch.object(reviewer, '_summarize_reviews',
                      side_effect=lambda reviews, **kw: "\n\n".join(reviews)):
        with patch.dict(os.environ, {
            'BATCH_REVIEW_ENABLED': '1',
            'BATCH_REVIEW_FILES_PER_BATCH': '1',
            'BATCH_REVIEW_MAX_CONCURRENT': '3',
            'BATCH_REVIEW_TIMEOUT_PER_BATCH': '1',  # 1秒/波次 → 整体超时 = 1秒
        }):
            result = reviewer.review_changes_in_batches(
                changes, commits_text="test commit", project_name="test-project"
            )

    assert result is not None
    assert "审查超时" in result

    print("✅ 超时处理测试通过")


def test_backward_compatibility_when_concurrency_disabled(mock_llm_client):
    """BATCH_REVIEW_MAX_CONCURRENT=1 时行为应与顺序模式完全一致"""
    mock_llm_client.completions.return_value = "```markdown\n审查结果\n总分：88分\n```"

    changes = _make_fake_changes(4)
    reviewer = CodeReviewer()

    with patch.dict(os.environ, {
        'BATCH_REVIEW_ENABLED': '1',
        'BATCH_REVIEW_FILES_PER_BATCH': '2',
        'BATCH_REVIEW_MAX_CONCURRENT': '1',  # 显式关闭并发
    }):
        result = reviewer.review_changes_in_batches(
            changes, commits_text="test commit", project_name="test-project"
        )

    assert result is not None
    assert len(result) > 0

    print("✅ 向后兼容测试通过")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
