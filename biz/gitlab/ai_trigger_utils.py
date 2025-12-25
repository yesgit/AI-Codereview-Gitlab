"""
@AI 触发评审相关的工具函数
"""
import re
from typing import Optional


def contains_ai_trigger(note_body: Optional[str]) -> bool:
    """
    检查评论内容是否包含 @AI 触发词
    
    支持以下变体（大小写不敏感）：
    - @AI
    - @ai
    - @Ai
    
    Args:
        note_body: 评论内容
        
    Returns:
        bool: 是否包含触发词
    """
    if not note_body:
        return False
    
    pattern = r'@AI|@ai|@Ai'
    return bool(re.search(pattern, note_body))


def should_skip_ai_note(note_body: Optional[str]) -> bool:
    """
    检查是否为 AI 系统添加的评论文本，如果是则应该跳过处理
    
    通过检查评论文本是否包含 AI 评审的标识来避免死循环
    
    Args:
        note_body: 评论内容
        
    Returns:
        bool: 是否应该跳过
    """
    if not note_body:
        return False
    
    # 检查 AI 评审的标识
    ai_markers = [
        '🤖 AI Code Review Result',
        '[Triggered by @AI',
        '[AI-REVIEW-RESULT]'
    ]
    
    return any(marker in note_body for marker in ai_markers)


def format_ai_review_result(review_result: str, trigger_type: str = '@AI comment') -> str:
    """
    格式化 AI 评审结果，添加触发源标识
    
    Args:
        review_result: 原始评审结果
        trigger_type: 触发类型描述
        
    Returns:
        str: 格式化后的评审结果
    """
    trigger_info = f"[Triggered by {trigger_type}]\n\n"
    review_header = "🤖 AI Code Review Result\n\n"
    
    # 如果 review_result 已经包含格式，则不再添加
    if review_header in review_result:
        return review_result
    
    return f"{trigger_info}{review_header}{review_result}"


def extract_ai_trigger_context(note_body: str) -> str:
    """
    从评论中提取 @AI 的上下文信息
    
    例如："@AI 请重点关注安全性问题" -> "请重点关注安全性问题"
    
    Args:
        note_body: 评论内容
        
    Returns:
        str: @AI 之后的文本内容
    """
    if not note_body:
        return ""
    
    # 匹配 @AI 或 @ai 或 @Ai 之后的内容
    pattern = r'@(?:AI|ai|Ai)\s*(.*)'
    match = re.search(pattern, note_body, re.IGNORECASE)
    
    if match:
        return match.group(1).strip()
    
    return ""
