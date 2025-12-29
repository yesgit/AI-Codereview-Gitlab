"""
测试飞书通知器的markdown渲染功能
"""
import pytest
from biz.utils.im.feishu import FeishuNotifier


class TestFeishuMarkdownRendering:
    """测试飞书通知器的markdown渲染"""
    
    def test_create_element_from_paragraph_uses_lark_md(self):
        """测试_create_element_from_paragraph方法始终使用lark_md格式"""
        notifier = FeishuNotifier()
        
        # 测试普通文本
        result = notifier._create_element_from_paragraph("普通文本内容")
        assert result["tag"] == "div"
        assert result["text"]["tag"] == "lark_md"
        assert result["text"]["content"] == "普通文本内容"
        
        # 测试包含markdown语法的文本
        markdown_text = "### 标题\n- 列表项1\n- 列表项2"
        result = notifier._create_element_from_paragraph(markdown_text)
        assert result["tag"] == "div"
        assert result["text"]["tag"] == "lark_md"
        assert result["text"]["content"] == markdown_text
        
        # 测试包含emoji的文本
        emoji_text = "🎯 优化建议\n🐛 发现bug"
        result = notifier._create_element_from_paragraph(emoji_text)
        assert result["tag"] == "div"
        assert result["text"]["tag"] == "lark_md"
        assert result["text"]["content"] == emoji_text
        
        # 测试包含加粗的文本
        bold_text = "**总分:94分**"
        result = notifier._create_element_from_paragraph(bold_text)
        assert result["tag"] == "div"
        assert result["text"]["tag"] == "lark_md"
        assert result["text"]["content"] == bold_text
        
        # 测试包含代码块的文本
        code_text = "```python\ndef hello():\n    print('hello')\n```"
        result = notifier._create_element_from_paragraph(code_text)
        assert result["tag"] == "div"
        assert result["text"]["tag"] == "lark_md"
        assert result["text"]["content"] == code_text
        
        # 测试AI审查报告示例（包含多种markdown语法）
        ai_review = """# 代码审查报告
## 问题描述和优化建议
- 🐛 发现问题：代码健壮性不足
- 🎯 优化建议：添加输入验证

**评分明细：**
1. 功能实现：38/40分
2. 安全性：30/30分

总分:94分"""
        result = notifier._create_element_from_paragraph(ai_review)
        assert result["tag"] == "div"
        assert result["text"]["tag"] == "lark_md"
        assert result["text"]["content"] == ai_review
