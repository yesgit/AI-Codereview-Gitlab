#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 MergeRequestHandler 类，特别是 target_branch_protected 方法"""
from unittest import TestCase, main
from unittest.mock import patch, MagicMock

from biz.gitlab.webhook_handler import MergeRequestHandler


class TestMergeRequestHandler(TestCase):
    def setUp(self):
        """设置测试环境"""
        self.sample_webhook_data = {
            'object_kind': 'merge_request',
            'object_attributes': {
                'iid': 42,
                'target_project_id': 123,
                'action': 'open',
                'target_branch': 'main',
                'last_commit': {
                    'id': 'abc123'
                }
            },
            'project': {
                'name': 'test-project',
                'path_with_namespace': 'group/test-project'
            },
            'user': {
                'username': 'testuser'
            }
        }
        self.gitlab_token = 'test_token'
        self.gitlab_url = 'http://example.com'

        # 创建 MergeRequestHandler 实例
        self.handler = MergeRequestHandler(
            self.sample_webhook_data,
            self.gitlab_token,
            self.gitlab_url
        )

        # mock requests.get to avoid real network calls
        self.patcher = patch('requests.get')
        self.mock_get = self.patcher.start()

    def test_handler_initialization(self):
        """测试 Handler 初始化"""
        self.assertEqual(self.handler.event_type, 'merge_request')
        self.assertEqual(self.handler.merge_request_iid, 42)
        self.assertEqual(self.handler.project_id, 123)
        self.assertEqual(self.handler.action, 'open')

    def test_target_branch_protected_with_main_branch(self):
        """测试目标分支为 main 且受保护的情况"""
        # 模拟 API 返回受保护的分支列表
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = [
            {'name': 'main', 'protected': True},
            {'name': 'release/*', 'protected': True}
        ]
        self.mock_get.return_value = fake_resp

        # 调用方法
        result = self.handler.target_branch_protected()

        # 验证结果
        self.assertTrue(result)
        
        # 验证 API 被正确调用
        self.mock_get.assert_called_once()
        call_args = self.mock_get.call_args
        self.assertIn('protected_branches', call_args[0][0])

    def test_target_branch_protected_with_wildcard(self):
        """测试目标分支匹配通配符规则的情况"""
        # 修改 webhook 数据中的目标分支
        self.sample_webhook_data['object_attributes']['target_branch'] = 'release/v1.0.0'
        handler = MergeRequestHandler(
            self.sample_webhook_data,
            self.gitlab_token,
            self.gitlab_url
        )

        # 模拟 API 返回受保护的分支列表（使用通配符）
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = [
            {'name': 'main', 'protected': True},
            {'name': 'release/*', 'protected': True}
        ]
        self.mock_get.return_value = fake_resp

        # 调用方法
        result = handler.target_branch_protected()

        # 验证结果（应该匹配 release/* 通配符）
        self.assertTrue(result)

    def test_target_branch_not_protected(self):
        """测试目标分支不受保护的情况"""
        # 模拟 API 返回受保护的分支列表（不包含当前目标分支）
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = [
            {'name': 'main', 'protected': True}
        ]
        self.mock_get.return_value = fake_resp

        # 修改目标分支为不受保护的分支
        self.sample_webhook_data['object_attributes']['target_branch'] = 'feature/test-branch'
        handler = MergeRequestHandler(
            self.sample_webhook_data,
            self.gitlab_token,
            self.gitlab_url
        )

        # 调用方法
        result = handler.target_branch_protected()

        # 验证结果
        self.assertFalse(result)

    def test_target_branch_protected_api_error(self):
        """测试 API 返回错误时的处理"""
        # 模拟 API 返回错误
        fake_resp = MagicMock()
        fake_resp.status_code = 403
        fake_resp.text = 'Forbidden'
        self.mock_get.return_value = fake_resp

        # 调用方法
        result = self.handler.target_branch_protected()

        # 验证结果（API 错误时应返回 False）
        self.assertFalse(result)

    def test_target_branch_protected_empty_response(self):
        """测试 API 返回空列表时的处理"""
        # 模拟 API 返回空列表
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = []
        self.mock_get.return_value = fake_resp

        # 调用方法
        result = self.handler.target_branch_protected()

        # 验证结果（没有受保护的分支时返回 False）
        self.assertFalse(result)

    def test_target_branch_protected_without_gitlab_url(self):
        """测试没有配置 gitlab_url 时的处理"""
        # 创建没有 gitlab_url 的 handler
        handler = MergeRequestHandler(
            self.sample_webhook_data,
            self.gitlab_token,
            ''  # 空的 gitlab_url
        )

        # 调用方法
        result = handler.target_branch_protected()

        # 验证结果（没有 URL 时应返回 False）
        self.assertFalse(result)
        # 不应该调用 API
        self.mock_get.assert_not_called()

    def test_get_merge_request_changes_success(self):
        """测试成功获取 MR 变更"""
        # 模拟 API 返回变更数据
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {
            'changes': [
                {
                    'diff': '@@ -1,3 +1,4 @@\n-old line\n+new line',
                    'new_path': 'src/test.py',
                    'deleted_file': False
                }
            ]
        }
        self.mock_get.return_value = fake_resp

        # 调用方法
        result = self.handler.get_merge_request_changes()

        # 验证结果
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['new_path'], 'src/test.py')

    def test_get_merge_request_changes_api_error(self):
        """测试获取 MR 变更时 API 返回错误"""
        # 模拟 API 返回错误
        fake_resp = MagicMock()
        fake_resp.status_code = 404
        self.mock_get.return_value = fake_resp

        # 调用方法
        result = self.handler.get_merge_request_changes()

        # 验证结果（应返回空列表）
        self.assertEqual(result, [])

    def test_get_merge_request_commits_success(self):
        """测试成功获取 MR 提交"""
        # 模拟 API 返回提交数据
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = [
            {
                'id': 'abc123',
                'title': 'Test commit',
                'message': 'Test commit message',
                'author_name': 'Test User',
                'author_email': 'test@example.com',
                'created_at': '2025-01-01T00:00:00Z',
                'web_url': 'http://example.com/commit/abc123'
            }
        ]
        self.mock_get.return_value = fake_resp

        # 调用方法
        result = self.handler.get_merge_request_commits()

        # 验证结果
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], 'abc123')
        self.assertEqual(result[0]['title'], 'Test commit')

    def test_add_merge_request_notes_success(self):
        """测试成功添加 MR 评论"""
        # 模拟 API 返回成功
        fake_resp = MagicMock()
        fake_resp.status_code = 201
        fake_resp.text = ''
        self.mock_get.return_value = fake_resp

        # 调用方法（需要 mock requests.post 而不是 get）
        with patch('requests.post') as mock_post:
            mock_post.return_value = fake_resp
            self.handler.add_merge_request_notes('Test comment')

            # 验证 post 被调用
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            self.assertEqual(call_args[1]['json']['body'], 'Test comment')

    def tearDown(self):
        """清理测试环境"""
        try:
            self.patcher.stop()
        except Exception:
            pass


if __name__ == '__main__':
    main()
