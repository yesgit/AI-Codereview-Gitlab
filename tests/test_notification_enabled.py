"""测试通知启用字段功能"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from biz.utils.im.dingtalk import DingTalkNotifier
from biz.utils.im.feishu import FeishuNotifier
from biz.utils.im.wecom import WeComNotifier


class TestNotificationEnabled:
    """测试通知 enabled 字段功能"""
    
    def test_dingtalk_notifier_with_enabled_true(self):
        """测试钉钉通知器 enabled=true 时发送消息"""
        config = {
            'dingtalk_webhook': 'https://oapi.dingtalk.com/robot/send',
            'dingtalk_enabled': True
        }
        
        with patch('biz.utils.im.dingtalk.requests.post') as mock_post:
            mock_post.return_value = Mock(status_code=200)
            
            notifier = DingTalkNotifier(config)
            notifier.send_message('测试消息')
            
            # 验证消息被发送
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args is not None
    
    def test_dingtalk_notifier_with_enabled_false(self):
        """测试钉钉通知器 enabled=false 时不发送消息"""
        config = {
            'dingtalk_webhook': 'https://oapi.dingtalk.com/robot/send',
            'dingtalk_enabled': False
        }
        
        with patch('biz.utils.im.dingtalk.requests.post') as mock_post:
            mock_post.return_value = Mock(status_code=200)
            
            notifier = DingTalkNotifier(config)
            notifier.send_message('测试消息')
            
            # 验证消息未被发送
            mock_post.assert_not_called()
    
    def test_dingtalk_notifier_without_enabled_field(self):
        """测试钉钉通知器未设置 enabled 字段时的默认行为"""
        config = {
            'dingtalk_webhook': 'https://oapi.dingtalk.com/robot/send'
        }
        
        with patch('biz.utils.im.dingtalk.requests.post') as mock_post:
            with patch.dict('os.environ', {'DINGTALK_ENABLED': '1'}):
                mock_post.return_value = Mock(status_code=200)
                
                notifier = DingTalkNotifier(config)
                notifier.send_message('测试消息')
                
                # 验证消息被发送（因为系统环境变量启用）
                mock_post.assert_called_once()
    
    def test_feishu_notifier_with_enabled_true(self):
        """测试飞书通知器 enabled=true 时发送消息"""
        config = {
            'feishu_webhook': 'https://open.feishu.cn/open-apis/bot/v2/hook',
            'feishu_enabled': True
        }
        
        with patch('biz.utils.im.feishu.requests.post') as mock_post:
            mock_post.return_value = Mock(status_code=200)
            
            notifier = FeishuNotifier(config)
            notifier.send_message('测试消息')
            
            # 验证消息被发送
            mock_post.assert_called_once()
    
    def test_feishu_notifier_with_enabled_false(self):
        """测试飞书通知器 enabled=false 时不发送消息"""
        config = {
            'feishu_webhook': 'https://open.feishu.cn/open-apis/bot/v2/hook',
            'feishu_enabled': False
        }
        
        with patch('biz.utils.im.feishu.requests.post') as mock_post:
            mock_post.return_value = Mock(status_code=200)
            
            notifier = FeishuNotifier(config)
            notifier.send_message('测试消息')
            
            # 验证消息未被发送
            mock_post.assert_not_called()
    
    def test_wecom_notifier_with_enabled_true(self):
        """测试企业微信通知器 enabled=true 时发送消息"""
        config = {
            'wecom_webhook': 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send',
            'wecom_enabled': True
        }
        
        with patch('biz.utils.im.wecom.requests.post') as mock_post:
            mock_post.return_value = Mock(status_code=200)
            
            notifier = WeComNotifier(config)
            notifier.send_message('测试消息')
            
            # 验证消息被发送
            mock_post.assert_called_once()
    
    def test_wecom_notifier_with_enabled_false(self):
        """测试企业微信通知器 enabled=false 时不发送消息"""
        config = {
            'wecom_webhook': 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send',
            'wecom_enabled': False
        }
        
        with patch('biz.utils.im.wecom.requests.post') as mock_post:
            mock_post.return_value = Mock(status_code=200)
            
            notifier = WeComNotifier(config)
            notifier.send_message('测试消息')
            
            # 验证消息未被发送
            mock_post.assert_not_called()
    
    def test_all_notifiers_with_mixed_enabled(self):
        """测试多个通知器混合 enabled 状态"""
        config = {
            'dingtalk_webhook': 'https://oapi.dingtalk.com/robot/send',
            'dingtalk_enabled': True,
            'feishu_webhook': 'https://open.feishu.cn/open-apis/bot/v2/hook',
            'feishu_enabled': False,
            'wecom_webhook': 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send',
            'wecom_enabled': True
        }
        
        with patch('biz.utils.im.dingtalk.requests.post') as mock_dingtalk:
            with patch('biz.utils.im.feishu.requests.post') as mock_feishu:
                with patch('biz.utils.im.wecom.requests.post') as mock_wecom:
                    # 设置钉钉 mock 返回值
                    mock_dingtalk_response = Mock(status_code=200)
                    mock_dingtalk_response.json.return_value = {'errmsg': 'ok', 'errcode': 0}
                    mock_dingtalk.return_value = mock_dingtalk_response
                    
                    # 设置飞书 mock 返回值
                    mock_feishu_response = Mock(status_code=200)
                    mock_feishu_response.json.return_value = {'msg': 'success'}
                    mock_feishu.return_value = mock_feishu_response
                    
                    # 设置企业微信 mock 返回值
                    mock_wecom_response = Mock(status_code=200)
                    mock_wecom_response.json.return_value = {'errcode': 0}
                    mock_wecom.return_value = mock_wecom_response
                    
                    # 测试钉钉
                    dingtalk_notifier = DingTalkNotifier(config)
                    dingtalk_notifier.send_message('消息1')
                    
                    # 测试飞书
                    feishu_notifier = FeishuNotifier(config)
                    feishu_notifier.send_message('消息2')
                    
                    # 测试企业微信
                    wecom_notifier = WeComNotifier(config)
                    wecom_notifier.send_message('消息3')
                    
                    # 验证：钉钉和企业微信发送，飞书未发送
                    assert mock_dingtalk.call_count == 1
                    assert mock_feishu.call_count == 0
                    assert mock_wecom.call_count == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
