#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2025/3/18 17:58
# @Author  : Arrow
from unittest import TestCase, main
from unittest.mock import patch, MagicMock

from biz.gitlab.webhook_handler import PushHandler


# @Describe:
class TestPushHandler(TestCase):
    def setUp(self):
        """设置测试环境"""
        self.sample_webhook_data = {
            'event_name': 'push',
            'project': {
                'id': 0
            },
        }
        self.gitlab_token = ''
        # provide a dummy base URL so the handler constructs full API URLs
        self.gitlab_url = 'http://example.com'

        # 创建PushHandler实例
        self.handler = PushHandler(self.sample_webhook_data, self.gitlab_token, self.gitlab_url)

        # mock requests.get to avoid real network calls and return a fake commit list
        self.patcher = patch('requests.get')
        self.mock_get = self.patcher.start()
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.text = '[]'
        fake_resp.json.return_value = [{'id': 'c1', 'parent_ids': ['parent123'] }]
        self.mock_get.return_value = fake_resp

    def test_get_parent_commit_id(self):
        """测试获取父提交ID"""
        commit_id = ''
        # 调用测试方法
        parent_id = self.handler.get_parent_commit_id(commit_id)
        self.assertEqual(parent_id, 'parent123')

    def test_get_commit_diff(self):
        """测试获取单个 commit 的 diff"""
        commit_id = 'test_commit_id_123'
        
        # 模拟 API 返回的 diff 数据
        fake_diff_data = [
            {
                'diff': '@@ -1,3 +1,4 @@\n-old line\n+new line',
                'new_path': 'src/test.py',
                'old_path': 'src/test.py',
                'deleted_file': False
            },
            {
                'diff': 'deleted file',
                'new_path': 'src/old.py',
                'old_path': 'src/old.py',
                'deleted_file': True
            }
        ]
        
        # 设置 mock 返回
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = fake_diff_data
        self.mock_get.return_value = fake_resp
        
        # 调用测试方法
        result = self.handler.get_commit_diff(commit_id)
        
        # 验证返回的 diff 格式
        self.assertEqual(len(result), 2)
        
        # 第一个 diff（未删除的文件）
        self.assertEqual(result[0]['diff'], fake_diff_data[0]['diff'])
        self.assertEqual(result[0]['new_path'], 'src/test.py')
        self.assertEqual(result[0]['deleted_file'], False)
        
        # 第二个 diff（删除的文件）
        self.assertEqual(result[1]['diff'], fake_diff_data[1]['diff'])
        self.assertEqual(result[1]['new_path'], 'src/old.py')
        self.assertEqual(result[1]['deleted_file'], True)

    def test_get_commit_diff_api_error(self):
        """测试 API 返回错误时的处理"""
        commit_id = 'test_commit_id_456'
        
        # 模拟 API 返回错误
        fake_resp = MagicMock()
        fake_resp.status_code = 404
        self.mock_get.return_value = fake_resp
        
        # 调用测试方法
        result = self.handler.get_commit_diff(commit_id)
        
        # 验证返回空列表
        self.assertEqual(result, [])

    def test_get_commit_diff_empty_response(self):
        """测试 API 返回空数据时的处理"""
        commit_id = 'test_commit_id_789'
        
        # 模拟 API 返回空数据
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = []
        self.mock_get.return_value = fake_resp
        
        # 调用测试方法
        result = self.handler.get_commit_diff(commit_id)
        
        # 验证返回空列表
        self.assertEqual(result, [])

    def tearDown(self):
        try:
            self.patcher.stop()
        except Exception:
            pass


if __name__ == '__main__':
    main()
