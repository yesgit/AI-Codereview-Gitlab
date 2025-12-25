"""
测试任务重试机制
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import time
import threading

from biz.queue.worker import (
    is_retryable_error,
    increment_retry_count,
    should_retry,
    handle_retry,
    RETRYABLE_EXCEPTIONS
)
from biz.utils.queue import retry_task, _retry_with_multiprocessing


class TestRetryableError(unittest.TestCase):
    """测试可重试异常判断"""

    def test_openai_timeout_error(self):
        """测试 OpenAI 超时错误"""
        from openai import APITimeoutError
        error = APITimeoutError("Request timed out")
        self.assertTrue(is_retryable_error(error))

    def test_httpx_read_timeout(self):
        """测试 HTTPx 读取超时"""
        from httpx import ReadTimeout
        error = ReadTimeout("timed out")
        self.assertTrue(is_retryable_error(error))

    def test_connection_error(self):
        """测试连接错误"""
        error = ConnectionError("Connection failed")
        self.assertTrue(is_retryable_error(error))

    def test_timeout_error(self):
        """测试超时错误"""
        error = TimeoutError("Operation timed out")
        self.assertTrue(is_retryable_error(error))

    def test_non_retryable_error(self):
        """测试不可重试的错误"""
        error = ValueError("Invalid input")
        self.assertFalse(is_retryable_error(error))

    def test_error_message_contains_timeout(self):
        """测试错误消息包含 timeout 关键词"""
        error = Exception("Request timeout error")
        self.assertTrue(is_retryable_error(error))

    def test_error_message_contains_connection(self):
        """测试错误消息包含 connection 关键词"""
        error = Exception("Connection refused")
        self.assertTrue(is_retryable_error(error))


class TestRetryCount(unittest.TestCase):
    """测试重试计数"""

    def test_increment_retry_count(self):
        """测试增加重试计数"""
        webhook_data = {}
        count = increment_retry_count(webhook_data)
        self.assertEqual(count, 1)
        self.assertEqual(webhook_data['_retry_count'], 1)

    def test_increment_retry_count_multiple_times(self):
        """测试多次增加重试计数"""
        webhook_data = {}
        increment_retry_count(webhook_data)
        increment_retry_count(webhook_data)
        increment_retry_count(webhook_data)
        self.assertEqual(webhook_data['_retry_count'], 3)

    def test_increment_existing_count(self):
        """测试已有计数的增加"""
        webhook_data = {'_retry_count': 2}
        count = increment_retry_count(webhook_data)
        self.assertEqual(count, 3)
        self.assertEqual(webhook_data['_retry_count'], 3)


class TestShouldRetry(unittest.TestCase):
    """测试是否应该重试"""

    def setUp(self):
        """设置测试环境"""
        import os
        self.original_max_retries = os.getenv('MAX_RETRIES', '3')

    def tearDown(self):
        """清理测试环境"""
        import os
        if 'MAX_RETRIES' in os.environ:
            del os.environ['MAX_RETRIES']

    def test_should_retry_when_under_limit(self):
        """测试未达到重试限制时应该重试"""
        webhook_data = {'_retry_count': 1}
        self.assertTrue(should_retry(webhook_data))

    def test_should_retry_when_at_limit(self):
        """测试达到重试限制时不应该重试"""
        webhook_data = {'_retry_count': 3}
        self.assertFalse(should_retry(webhook_data))

    def test_should_retry_with_custom_max_retries(self):
        """测试自定义最大重试次数"""
        import os
        os.environ['MAX_RETRIES'] = '5'
        webhook_data = {'_retry_count': 3}
        self.assertTrue(should_retry(webhook_data))


class TestHandleRetry(unittest.TestCase):
    """测试重试处理逻辑"""

    def setUp(self):
        """设置测试环境"""
        self.mock_function = Mock()
        self.webhook_data = {'project': {'name': 'test'}}
        self.exception = TimeoutError("Request timed out")

    @patch('biz.queue.worker.retry_task')
    @patch('biz.queue.worker.notifier')
    def test_handle_retry_schedules_retry(self, mock_notifier, mock_retry_task):
        """测试重试处理会调度重试任务"""
        import os
        os.environ['MAX_RETRIES'] = '3'
        os.environ['RETRY_DELAY_SECONDS'] = '60'

        handle_retry(self.webhook_data, self.exception, self.mock_function, 'token', 'url', 'slug')

        # 验证调用了 retry_task
        mock_retry_task.assert_called_once_with(
            self.mock_function,
            self.webhook_data,
            'token',
            'url',
            'slug',
            delay=60
        )
        # 验证没有发送通知
        mock_notifier.send_notification.assert_not_called()

    @patch('biz.queue.worker.retry_task')
    @patch('biz.queue.worker.notifier')
    def test_handle_retry_max_retries_reached(self, mock_notifier, mock_retry_task):
        """测试达到最大重试次数时发送通知"""
        import os
        os.environ['MAX_RETRIES'] = '3'
        os.environ['RETRY_DELAY_SECONDS'] = '60'
        
        # 设置重试次数为最大值
        self.webhook_data['_retry_count'] = 3

        handle_retry(self.webhook_data, self.exception, self.mock_function, 'token', 'url', 'slug')

        # 验证没有调用 retry_task
        mock_retry_task.assert_not_called()
        # 验证发送了通知
        mock_notifier.send_notification.assert_called_once()


class TestRetryWithMultiprocessing(unittest.TestCase):
    """测试多进程重试"""

    @patch('threading.Thread')
    @patch('multiprocessing.Process')
    def test_retry_with_multiprocessing(self, mock_process, mock_thread):
        """测试多进程重试"""
        mock_process_instance = Mock()
        mock_process.return_value = mock_process_instance
        
        def test_func(data, token, url, slug):
            return "success"

        _retry_with_multiprocessing(test_func, {'data': 'test'}, 'token', 'url', 'slug', delay=1)

        # 验证创建了线程
        mock_thread.assert_called_once()
        # 验证线程是 daemon 线程
        call_kwargs = mock_thread.call_args[1]
        self.assertTrue(call_kwargs['daemon'])
        # 验证启动了线程
        mock_thread.return_value.start.assert_called_once()


class TestRetryTask(unittest.TestCase):
    """测试重试任务函数"""

    def setUp(self):
        """设置测试环境"""
        import os
        os.environ['QUEUE_DRIVER'] = 'multiprocessing'

    def tearDown(self):
        """清理测试环境"""
        import os
        if 'QUEUE_DRIVER' in os.environ:
            del os.environ['QUEUE_DRIVER']

    @patch('biz.utils.queue._retry_with_multiprocessing')
    def test_retry_task_multiprocessing(self, mock_retry_mp):
        """测试多进程模式下的重试"""
        mock_function = Mock()
        retry_task(mock_function, {'data': 'test'}, 'token', 'url', 'slug', delay=60)

        # 验证调用了多进程重试
        mock_retry_mp.assert_called_once_with(
            mock_function,
            {'data': 'test'},
            'token',
            'url',
            'slug',
            60
        )

    @patch('redis.Redis')
    @patch('rq.Queue')
    def test_retry_task_rq(self, mock_queue, mock_redis):
        """测试 RQ 模式下的重试"""
        import os
        os.environ['QUEUE_DRIVER'] = 'rq'
        os.environ['REDIS_URL'] = 'redis://localhost:6379'
        os.environ['WORKER_QUEUE'] = 'default'

        mock_function = Mock()
        mock_queue_instance = Mock()
        mock_queue.return_value = mock_queue_instance
        mock_redis_instance = Mock()
        mock_redis.from_url.return_value = mock_redis_instance

        retry_task(mock_function, {'data': 'test'}, 'token', 'url', 'slug', delay=60)

        # 验证创建了 RQ 队列
        mock_queue.assert_called_once_with('default', connection=mock_redis_instance)
        # 验证调用了 enqueue_in
        mock_queue_instance.enqueue_in.assert_called_once()


class TestRetryableExceptionsConstant(unittest.TestCase):
    """测试可重试异常常量"""

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
            self.assertIn(exc, RETRYABLE_EXCEPTIONS)


if __name__ == '__main__':
    unittest.main()
