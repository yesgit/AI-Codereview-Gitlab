#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 NoteHandler 类
"""
from unittest import TestCase, main
from unittest.mock import patch, MagicMock

from biz.gitlab.webhook_handler import NoteHandler


class TestNoteHandler(TestCase):
    """测试 Note 事件处理器"""
    
    def setUp(self):
        """设置测试环境"""
        self.gitlab_token = 'test_token'
        self.gitlab_url = 'http://gitlab.example.com'
    
    def test_parse_commit_note_event(self):
        """测试解析 commit note 事件"""
        webhook_data = {
            'object_kind': 'note',
            'object_attributes': {
                'note': '@AI 请帮我审查',
                'noteable_type': 'Commit',
                'noteable_iid': 'abc123def456'
            },
            'project': {
                'id': 123
            },
            'user': {
                'username': 'testuser'
            }
        }
        
        handler = NoteHandler(webhook_data, self.gitlab_token, self.gitlab_url)
        
        self.assertEqual(handler.event_type, 'note')
        self.assertEqual(handler.note_type, 'Commit')
        self.assertEqual(handler.commit_id, 'abc123def456')
        self.assertEqual(handler.note_body, '@AI 请帮我审查')
        self.assertEqual(handler.author, 'testuser')
        self.assertEqual(handler.project_id, 123)
    
    def test_parse_mr_note_event(self):
        """测试解析 MergeRequest note 事件"""
        webhook_data = {
            'object_kind': 'note',
            'object_attributes': {
                'note': '@ai review',
                'noteable_type': 'MergeRequest',
                'noteable_iid': 42
            },
            'project': {
                'id': 456
            },
            'user': {
                'username': 'reviewer'
            }
        }
        
        handler = NoteHandler(webhook_data, self.gitlab_token, self.gitlab_url)
        
        self.assertEqual(handler.note_type, 'MergeRequest')
        self.assertEqual(handler.mr_iid, 42)
        self.assertEqual(handler.author, 'reviewer')
        self.assertEqual(handler.project_id, 456)
    
    def test_parse_invalid_event(self):
        """测试无效的事件类型"""
        webhook_data = {
            'object_kind': 'push'
        }
        
        handler = NoteHandler(webhook_data, self.gitlab_token, self.gitlab_url)
        
        # NoteHandler 会记录 event_type，但只有当它是 'note' 时才会解析 note 事件
        self.assertEqual(handler.event_type, 'push')
        # note_type 应该是 None，因为没有调用 parse_note_event
        self.assertIsNone(handler.note_type)
    
    def test_parse_note_event_without_user(self):
        """测试没有用户信息的 note 事件"""
        webhook_data = {
            'object_kind': 'note',
            'object_attributes': {
                'note': '@AI',
                'noteable_type': 'Commit',
                'noteable_iid': 'commit123'
            },
            'project': {
                'id': 123
            }
        }
        
        handler = NoteHandler(webhook_data, self.gitlab_token, self.gitlab_url)
        
        # 应该有默认值
        self.assertEqual(handler.author, 'Unknown')
    
    def test_get_commit_diff(self):
        """测试获取 commit diff"""
        webhook_data = {
            'object_kind': 'note',
            'object_attributes': {
                'note': '@AI',
                'noteable_type': 'Commit',
                'noteable_iid': 'test_commit_id'
            },
            'project': {'id': 123}
        }
        
        handler = NoteHandler(webhook_data, self.gitlab_token, self.gitlab_url)
        
        # Mock requests.get
        with patch('requests.get') as mock_get:
            fake_resp = MagicMock()
            fake_resp.status_code = 200
            fake_resp.json.return_value = [
                {
                    'diff': '@@ -1,1 +1,2 @@\n-old\n+new',
                    'new_path': 'test.py',
                    'old_path': 'test.py',
                    'deleted_file': False
                },
                {
                    'diff': 'deleted file',
                    'new_path': 'old.py',
                    'old_path': 'old.py',
                    'deleted_file': True
                }
            ]
            mock_get.return_value = fake_resp
            
            diff = handler.get_commit_diff()
            
            self.assertEqual(len(diff), 2)
            self.assertEqual(diff[0]['new_path'], 'test.py')
            self.assertEqual(diff[0]['deleted_file'], False)
            self.assertEqual(diff[1]['deleted_file'], True)
    
    def test_get_commit_diff_api_error(self):
        """测试 API 返回错误时的处理"""
        webhook_data = {
            'object_kind': 'note',
            'object_attributes': {
                'note': '@AI',
                'noteable_type': 'Commit',
                'noteable_iid': 'test_commit_id'
            },
            'project': {'id': 123}
        }
        
        handler = NoteHandler(webhook_data, self.gitlab_token, self.gitlab_url)
        
        with patch('requests.get') as mock_get:
            fake_resp = MagicMock()
            fake_resp.status_code = 404
            mock_get.return_value = fake_resp
            
            diff = handler.get_commit_diff()
            
            self.assertEqual(diff, [])
    
    def test_get_commit_diff_without_commit_id(self):
        """测试没有 commit_id 时"""
        webhook_data = {
            'object_kind': 'note',
            'object_attributes': {
                'note': '@AI',
                'noteable_type': 'Commit',
                'noteable_iid': None
            },
            'project': {'id': 123}
        }
        
        handler = NoteHandler(webhook_data, self.gitlab_token, self.gitlab_url)
        diff = handler.get_commit_diff()
        
        self.assertEqual(diff, [])
    
    def test_get_merge_request_changes(self):
        """测试获取 MR changes"""
        webhook_data = {
            'object_kind': 'note',
            'object_attributes': {
                'note': '@AI',
                'noteable_type': 'MergeRequest',
                'noteable_iid': 10
            },
            'user': {'username': 'user1'},
            'project': {'id': 123}
        }
        
        handler = NoteHandler(webhook_data, self.gitlab_token, self.gitlab_url)
        
        with patch('requests.get') as mock_get:
            fake_resp = MagicMock()
            fake_resp.status_code = 200
            fake_resp.json.return_value = {
                'changes': [
                    {
                        'diff': 'some diff',
                        'new_path': 'src/main.py',
                        'additions': 5,
                        'deletions': 2
                    }
                ]
            }
            mock_get.return_value = fake_resp
            
            changes = handler.get_merge_request_changes()
            
            self.assertEqual(len(changes), 1)
            self.assertEqual(changes[0]['new_path'], 'src/main.py')
    
    def test_get_merge_request_changes_api_error(self):
        """测试 MR API 返回错误"""
        webhook_data = {
            'object_kind': 'note',
            'object_attributes': {
                'note': '@AI',
                'noteable_type': 'MergeRequest',
                'noteable_iid': 10
            },
            'user': {'username': 'user1'},
            'project': {'id': 123}
        }
        
        handler = NoteHandler(webhook_data, self.gitlab_token, self.gitlab_url)
        
        with patch('requests.get') as mock_get:
            fake_resp = MagicMock()
            fake_resp.status_code = 404
            mock_get.return_value = fake_resp
            
            changes = handler.get_merge_request_changes()
            
            self.assertEqual(changes, [])
    
    def test_add_commit_comment(self):
        """测试添加 commit 评论"""
        webhook_data = {
            'object_kind': 'note',
            'object_attributes': {
                'note': '@AI',
                'noteable_type': 'Commit',
                'noteable_iid': 'commit123'
            },
            'project': {'id': 123}
        }
        
        handler = NoteHandler(webhook_data, self.gitlab_token, self.gitlab_url)
        
        with patch('requests.post') as mock_post:
            fake_resp = MagicMock()
            fake_resp.status_code = 201
            mock_post.return_value = fake_resp
            
            handler.add_commit_comment('Test review result')
            
            # 验证调用了一次
            self.assertEqual(mock_post.call_count, 1)
    
    def test_add_commit_comment_without_commit_id(self):
        """测试没有 commit_id 时添加评论（应该不调用 API）"""
        webhook_data = {
            'object_kind': 'note',
            'object_attributes': {
                'note': '@AI',
                'noteable_type': 'Commit',
                'noteable_iid': None
            },
            'project': {'id': 123}
        }
        
        handler = NoteHandler(webhook_data, self.gitlab_token, self.gitlab_url)
        
        with patch('requests.post') as mock_post:
            handler.add_commit_comment('Test review result')
            
            # 不应该调用 API
            self.assertEqual(mock_post.call_count, 0)
    
    def test_add_merge_request_comment(self):
        """测试添加 MR 评论"""
        webhook_data = {
            'object_kind': 'note',
            'object_attributes': {
                'note': '@AI',
                'noteable_type': 'MergeRequest',
                'noteable_iid': 5
            },
            'user': {'username': 'user1'},
            'project': {'id': 123}
        }
        
        handler = NoteHandler(webhook_data, self.gitlab_token, self.gitlab_url)
        
        with patch('requests.post') as mock_post:
            fake_resp = MagicMock()
            fake_resp.status_code = 201
            mock_post.return_value = fake_resp
            
            handler.add_merge_request_comment('Test review result')
            
            self.assertEqual(mock_post.call_count, 1)
    
    def test_add_merge_request_comment_without_mr_iid(self):
        """测试没有 mr_iid 时添加评论（应该不调用 API）"""
        webhook_data = {
            'object_kind': 'note',
            'object_attributes': {
                'note': '@AI',
                'noteable_type': 'MergeRequest',
                'noteable_iid': None
            },
            'user': {'username': 'user1'},
            'project': {'id': 123}
        }
        
        handler = NoteHandler(webhook_data, self.gitlab_token, self.gitlab_url)
        
        with patch('requests.post') as mock_post:
            handler.add_merge_request_comment('Test review result')
            
            self.assertEqual(mock_post.call_count, 0)


if __name__ == '__main__':
    main()
