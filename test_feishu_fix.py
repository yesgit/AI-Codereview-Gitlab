#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试飞书消息修复效果 - 使用 Mock 测试"""

import os
import sys
import json
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from biz.utils.im.feishu import FeishuNotifier


def test_push_review_message():
    """测试 Push Review 消息格式（脱敏）"""
    content = """### 🚀 my-app: Push

#### 提交记录:
- **提交信息**: 优化组件返回处理逻辑
- **提交者**: Developer
- **时间**: 2025-12-24T15:35:26+00:00
- [查看提交详情](https://gitlab.example.com/group/project/-/commit/abc123)

#### AI Review 结果: 

# 代码审查报告

## 问题描述和优化建议

### 🐛 功能实现问题
1. **防抖函数使用不当**：`handleBack`方法使用了`_.debounce`，但在组件卸载时没有取消防抖，可能导致内存泄漏。建议在`componentWillUnmount`中取消防抖。
   ```javascript
   componentWillUnmount() {
     if (this.backHandler) {
       this.backHandler.remove();
       this.backHandler = null;
     }
     this.handleBack.cancel(); // 新增：取消防抖
   }
   ```

2. **平台判断冗余**：`handleBack`方法中虽然判断了`Platform.OS`，但`Util.handleBackPress`本身应该已经处理了平台兼容性。建议简化逻辑或确认Util的实现。

### 🔍 潜在风险
1. **内存泄漏风险**：虽然添加了`componentWillUnmount`清理逻辑，但若`Util.handleBackPress`返回`null`或假值，可能导致`remove`调用失败。
   ```javascript
   // 建议增加空值检查
   if (this.backHandler && this.backHandler.remove) {
     this.backHandler.remove();
   }
   ```

### 🎯 最佳实践改进
1. **魔法数字**：`_.debounce`的300ms延迟是硬编码，建议提取为常量，如`const DEBOUNCE_DELAY = 300`。
2. **代码结构**：`handleBack`和`goBack`方法定义顺序混乱，建议按生命周期或功能相关性重新排序。

### 💡 性能小贴士
移除的`console.log`是好评！🎉 但`_.debounce`在频繁回调时可能影响性能，建议评估是否真正需要防抖（比如用户快速点击返回键的场景）。

## 评分明细
- **功能实现的正确性与健壮性**：36/40分（防抖未完全处理扣2分，平台判断冗余扣2分）
- **安全性与潜在风险**：27/30分（内存泄漏风险扣3分）
- **是否符合最佳实践**：16/20分（魔法数字和代码结构各扣2分）
- **性能与资源利用效率**：4/5分（防抖性能考虑不周扣1分）
- **Commits信息的清晰性与准确性**：5/5分（提交信息清晰描述了兼容性改进）

## 总分
总分:88分

> 注：代码整体实现良好，建议在代码简洁性和可维护性方面继续优化~ 😉"""

    return content


def main():
    """主测试函数 - 使用 Mock 测试"""
    # 使用 mock webhook URL
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/mock-webhook"
    
    # 创建飞书通知器
    notifier = FeishuNotifier(webhook_url=webhook_url)
    
    # 获取测试消息内容
    content = test_push_review_message()
    
    print("=" * 60)
    print("Mock 测试：飞书消息修复验证")
    print("=" * 60)
    print("\n消息内容预览：")
    print(content)
    print("\n" + "=" * 60)
    
    # 使用 mock requests.post 来模拟发送
    with patch('biz.utils.im.feishu.requests.post') as mock_post:
        # 设置 mock 返回值
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'msg': 'success'}
        mock_post.return_value = mock_response
        
        try:
            notifier.send_message(
                content=content,
                msg_type='markdown',
                title='🚀 my-app: Push - AI Code Review',
                gitlab_base_url='https://gitlab.example.com',
                project_slug='group/my-app'
            )
            print("\n✅ Mock 发送成功！")
            print("\n验证要点：")
            print("1. AI Review 结果部分应该不再显示 Markdown 源码")
            print("2. 表格和代码块应该正常渲染")
            print("3. 表情符号应该正常显示")
            print("4. 提交信息应该以纯文本形式显示")
            
            # 打印发送的请求数据用于验证
            print("\n" + "=" * 60)
            print("发送的请求数据 (用于验证格式):")
            print("=" * 60)
            if mock_post.called:
                call_args = mock_post.call_args
                request_data = call_args[1]['json'] if call_args else {}
                print(json.dumps(request_data, indent=2, ensure_ascii=False))
                
                # 验证数据结构
                print("\n" + "=" * 60)
                print("数据结构验证:")
                print("=" * 60)
                if request_data.get('msg_type') == 'interactive':
                    print("✅ 使用了交互式卡片格式")
                    card = request_data.get('card', {})
                    if card.get('header'):
                        print("✅ 包含标题头部")
                    if card.get('body') and card['body'].get('elements'):
                        elements = card['body']['elements']
                        print(f"✅ 包含 {len(elements)} 个卡片元素")
                        
                        # 检查元素类型
                        lark_md_count = sum(1 for e in elements if e.get('text', {}).get('tag') == 'lark_md')
                        plain_text_count = sum(1 for e in elements if e.get('text', {}).get('tag') == 'plain_text')
                        print(f"✅ lark_md 元素: {lark_md_count} 个")
                        print(f"✅ plain_text 元素: {plain_text_count} 个")
                        
                else:
                    print("❌ 未使用交互式卡片格式")
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()
