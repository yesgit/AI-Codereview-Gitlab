#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 @AI 触发词识别工具函数
"""
from unittest import TestCase, main
from biz.gitlab.ai_trigger_utils import (
    contains_ai_trigger,
    should_skip_ai_note,
    format_ai_review_result,
    extract_ai_trigger_context
)


class TestAITriggerUtils(TestCase):
    """测试 @AI 触发词识别工具"""
    
    def test_contains_ai_trigger_uppercase(self):
        """测试大写 @AI"""
        self.assertTrue(contains_ai_trigger("@AI"))
        self.assertTrue(contains_ai_trigger("请帮我看一下 @AI"))
        self.assertTrue(contains_ai_trigger("代码在附件，@AI 帮忙审查一下"))
    
    def test_contains_ai_trigger_lowercase(self):
        """测试小写 @ai"""
        self.assertTrue(contains_ai_trigger("@ai"))
        self.assertTrue(contains_ai_trigger("review @ai please"))
        self.assertTrue(contains_ai_trigger("需要代码审查 @ai"))
    
    def test_contains_ai_trigger_mixed(self):
        """测试混合大小写 @Ai"""
        self.assertTrue(contains_ai_trigger("@Ai"))
        self.assertTrue(contains_ai_trigger("check @Ai"))
        self.assertTrue(contains_ai_trigger("@Ai 请帮忙"))
    
    def test_contains_ai_trigger_not_found(self):
        """测试不包含触发词"""
        self.assertFalse(contains_ai_trigger("请帮我审查"))
        self.assertFalse(contains_ai_trigger("AI 评审"))
        self.assertFalse(contains_ai_trigger("@REVIEW"))
        self.assertFalse(contains_ai_trigger("code review needed"))
    
    def test_contains_ai_trigger_empty(self):
        """测试空字符串"""
        self.assertFalse(contains_ai_trigger(""))
        self.assertFalse(contains_ai_trigger(None))
    
    def test_should_skip_ai_note_with_robot_emoji(self):
        """测试包含机器人表情的评论应该跳过"""
        self.assertTrue(should_skip_ai_note("🤖 AI Code Review Result\n..."))
        self.assertTrue(should_skip_ai_note("🤖 AI Code Review Result\n评分：85分"))
    
    def test_should_skip_ai_note_with_trigger_marker(self):
        """测试包含触发源标记的评论应该跳过"""
        self.assertTrue(should_skip_ai_note("[Triggered by @AI]"))
        self.assertTrue(should_skip_ai_note("[Triggered by @AI comment by user]"))
        self.assertTrue(should_skip_ai_note("[AI-REVIEW-RESULT]"))
    
    def test_should_skip_ai_note_without_marker(self):
        """测试普通评论不应该跳过"""
        self.assertFalse(should_skip_ai_note("@AI 请帮我审查"))
        self.assertFalse(should_skip_ai_note("LGTM"))
        self.assertFalse(should_skip_ai_note("代码看起来不错"))
        self.assertFalse(should_skip_ai_note(""))
    
    def test_format_ai_review_result_new(self):
        """测试格式化新的评审结果"""
        review_result = "评分：85分\n\n代码质量不错"
        formatted = format_ai_review_result(review_result, "@AI comment by user")
        
        self.assertIn("[Triggered by @AI comment by user]", formatted)
        self.assertIn("🤖 AI Code Review Result", formatted)
        self.assertIn("评分：85分", formatted)
    
    def test_format_ai_review_result_already_formatted(self):
        """测试已经格式化的结果不再重复格式化"""
        review_result = "🤖 AI Code Review Result\n\n评分：85分"
        formatted = format_ai_review_result(review_result, "@AI comment by user")
        
        # 应该保持原样，不再添加额外的标记
        self.assertIn("🤖 AI Code Review Result", formatted)
        # 不应该重复添加 [Triggered by]
        self.assertEqual(formatted, review_result)
    
    def test_extract_ai_trigger_context_simple(self):
        """测试提取简单上下文"""
        self.assertEqual(
            extract_ai_trigger_context("@AI 请帮我审查"),
            "请帮我审查"
        )
    
    def test_extract_ai_trigger_context_with_prefix(self):
        """测试带前缀的上下文提取"""
        self.assertEqual(
            extract_ai_trigger_context("代码在附件，@AI 帮忙审查一下"),
            "帮忙审查一下"
        )
    
    def test_extract_ai_trigger_context_empty_after_trigger(self):
        """测试触发词后为空"""
        self.assertEqual(
            extract_ai_trigger_context("@AI"),
            ""
        )
    
    def test_extract_ai_trigger_context_no_trigger(self):
        """测试没有触发词"""
        self.assertEqual(
            extract_ai_trigger_context("请帮我审查代码"),
            ""
        )
    
    def test_extract_ai_trigger_context_case_insensitive(self):
        """测试大小写不敏感"""
        self.assertEqual(
            extract_ai_trigger_context("@ai review this"),
            "review this"
        )
        self.assertEqual(
            extract_ai_trigger_context("@Ai check this"),
            "check this"
        )


if __name__ == '__main__':
    main()
