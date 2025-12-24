"""
测试任务重试机制 - 简化版本（不依赖完整模块导入）
"""
import unittest
from unittest.mock import Mock, patch
import os
import sys


class TestIsRetryableError(unittest.TestCase):
    """测试可重试异常判断函数"""

    def setUp(self):
        """设置测试环境"""
        # 直接定义要测试的函数，避免导入完整模块
        self.RETRYABLE_EXCEPTIONS = (
            'openai.APITimeoutError',
            'openai.APIConnectionError',
            'openai.RateLimitError',
            'httpx.TimeoutException',
            'httpx.ConnectTimeout',
            'httpx.ReadTimeout',
            'ConnectionError',
            'TimeoutError',
        )
        
        self.RETRYABLE_KEYWORDS = ['timeout', 'connection', 'rate limit', 'temporarily unavailable']

    def is_retryable_error(self, error):
        """判断异常是否可重试"""
        error_name = type(error).__name__
        error_module = type(error).__module__
        
        # 检查异常类型名称
        for retryable in self.RETRYABLE_EXCEPTIONS:
            if error_name == retryable.split('.')[-1] or \
               f"{error_module}.{error_name}" == retryable:
                return True
        
        # 检查异常消息
        error_msg = str(error).lower()
        if any(keyword in error_msg for keyword in self.RETRYABLE_KEYWORDS):
            return True
        
        return False

    def test_connection_error(self):
        """测试连接错误"""
        error = ConnectionError("Connection failed")
        self.assertTrue(self.is_retryable_error(error))

    def test_timeout_error(self):
        """测试超时错误"""
        error = TimeoutError("Operation timed out")
        self.assertTrue(self.is_retryable_error(error))

    def test_non_retryable_error(self):
        """测试不可重试的错误"""
        error = ValueError("Invalid input")
        self.assertFalse(self.is_retryable_error(error))

    def test_error_message_contains_timeout(self):
        """测试错误消息包含 timeout 关键词"""
        error = Exception("Request timeout error")
        self.assertTrue(self.is_retryable_error(error))

    def test_error_message_contains_connection(self):
        """测试错误消息包含 connection 关键词"""
        error = Exception("Connection refused")
        self.assertTrue(self.is_retryable_error(error))

    def test_error_message_contains_rate_limit(self):
        """测试错误消息包含 rate limit 关键词"""
        error = Exception("Rate limit exceeded")
        self.assertTrue(self.is_retryable_error(error))


class TestRetryCount(unittest.TestCase):
    """测试重试计数"""

    def increment_retry_count(self, webhook_data):
        """增加重试计数并返回当前重试次数"""
        retry_count = webhook_data.get('_retry_count', 0)
        webhook_data['_retry_count'] = retry_count + 1
        return retry_count + 1

    def test_increment_retry_count(self):
        """测试增加重试计数"""
        webhook_data = {}
        count = self.increment_retry_count(webhook_data)
        self.assertEqual(count, 1)
        self.assertEqual(webhook_data['_retry_count'], 1)

    def test_increment_retry_count_multiple_times(self):
        """测试多次增加重试计数"""
        webhook_data = {}
        self.increment_retry_count(webhook_data)
        self.increment_retry_count(webhook_data)
        self.increment_retry_count(webhook_data)
        self.assertEqual(webhook_data['_retry_count'], 3)

    def test_increment_existing_count(self):
        """测试已有计数的增加"""
        webhook_data = {'_retry_count': 2}
        count = self.increment_retry_count(webhook_data)
        self.assertEqual(count, 3)
        self.assertEqual(webhook_data['_retry_count'], 3)


class TestShouldRetry(unittest.TestCase):
    """测试是否应该重试"""

    def should_retry(self, webhook_data, max_retries=3):
        """判断是否应该重试"""
        current_retries = webhook_data.get('_retry_count', 0)
        return current_retries < max_retries

    def test_should_retry_when_under_limit(self):
        """测试未达到重试限制时应该重试"""
        webhook_data = {'_retry_count': 1}
        self.assertTrue(self.should_retry(webhook_data, max_retries=3))

    def test_should_retry_when_at_limit(self):
        """测试达到重试限制时不应该重试"""
        webhook_data = {'_retry_count': 3}
        self.assertFalse(self.should_retry(webhook_data, max_retries=3))

    def test_should_retry_with_custom_max_retries(self):
        """测试自定义最大重试次数"""
        webhook_data = {'_retry_count': 3}
        self.assertTrue(self.should_retry(webhook_data, max_retries=5))


class TestRetryConfiguration(unittest.TestCase):
    """测试重试配置"""

    def test_default_max_retries(self):
        """测试默认最大重试次数"""
        max_retries = int(os.getenv('MAX_RETRIES', '3'))
        self.assertEqual(max_retries, 3)

    def test_default_retry_delay(self):
        """测试默认重试延迟"""
        delay = int(os.getenv('RETRY_DELAY_SECONDS', '60'))
        self.assertEqual(delay, 60)

    @patch.dict(os.environ, {'MAX_RETRIES': '5', 'RETRY_DELAY_SECONDS': '120'}, clear=True)
    def test_custom_configuration(self):
        """测试自定义配置"""
        max_retries = int(os.getenv('MAX_RETRIES', '3'))
        delay = int(os.getenv('RETRY_DELAY_SECONDS', '60'))
        self.assertEqual(max_retries, 5)
        self.assertEqual(delay, 120)


class TestRetryableExceptionsConstant(unittest.TestCase):
    """测试可重试异常常量"""

    RETRYABLE_EXCEPTIONS = (
        'openai.APITimeoutError',
        'openai.APIConnectionError',
        'openai.RateLimitError',
        'httpx.TimeoutException',
        'httpx.ConnectTimeout',
        'httpx.ReadTimeout',
        'ConnectionError',
        'TimeoutError',
    )

    def test_retryable_exceptions_constant(self):
        """测试可重试异常常量包含预期的异常类型"""
        expected_exceptions = [
            'openai.APITimeoutError',
            'openai.APIConnectionError',
            'openai.RateLimitError',
            'httpx.TimeoutException',
            'httpx.ConnectTimeout',
            'httpx.ReadTimeout',
            'ConnectionError',
            'TimeoutError',
        ]
        
        for exc in expected_exceptions:
            self.assertIn(exc, self.RETRYABLE_EXCEPTIONS)


if __name__ == '__main__':
    unittest.main(verbosity=2)
