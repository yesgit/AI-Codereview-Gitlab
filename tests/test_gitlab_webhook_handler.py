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

    def tearDown(self):
        try:
            self.patcher.stop()
        except Exception:
            pass


if __name__ == '__main__':
    main()
