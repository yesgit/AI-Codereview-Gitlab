"""
测试配置 API
"""
import pytest
from fastapi.testclient import TestClient
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.main import app


client = TestClient(app)


class TestConfigAPI:
    """测试配置API"""
    
    def test_get_default_prompts_success(self):
        """测试成功获取默认提示词"""
        response = client.get("/api/v1/config/default-prompts")
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证响应包含必需的字段
        assert 'custom_prompt_system' in data
        assert 'custom_prompt_user' in data
        
        # 验证提示词不为空
        assert len(data['custom_prompt_system']) > 0
        assert len(data['custom_prompt_user']) > 0
        
        # 验证包含关键内容
        assert '代码审查目标' in data['custom_prompt_system']
        assert 'diffs_text' in data['custom_prompt_user']
        
        print("✅ 测试通过：成功获取默认提示词")
        print(f"System Prompt 长度: {len(data['custom_prompt_system'])}")
        print(f"User Prompt 长度: {len(data['custom_prompt_user'])}")
    
    def test_get_default_prompts_structure(self):
        """测试默认提示词结构正确性"""
        response = client.get("/api/v1/config/default-prompts")
        data = response.json()
        
        # 验证 Jinja2 模板变量存在
        assert '{{ style }}' in data['custom_prompt_system'] or '{' + '{' in data['custom_prompt_system']
        assert '{diffs_text}' in data['custom_prompt_user']
        assert '{commits_text}' in data['custom_prompt_user']
        
        # 验证评分标准存在
        assert '40分' in data['custom_prompt_system']
        assert '30分' in data['custom_prompt_system']
        assert '20分' in data['custom_prompt_system']
        
        # 验证不同风格的处理
        assert 'professional' in data['custom_prompt_system'].lower()
        assert 'sarcastic' in data['custom_prompt_system'].lower()
        assert 'gentle' in data['custom_prompt_system'].lower()
        assert 'humorous' in data['custom_prompt_system'].lower()
        
        print("✅ 测试通过：默认提示词结构正确")


if __name__ == '__main__':
    # 运行测试
    test_instance = TestConfigAPI()
    
    print("\n" + "=" * 60)
    print("开始运行配置API测试")
    print("=" * 60 + "\n")
    
    try:
        test_instance.test_get_default_prompts_success()
        test_instance.test_get_default_prompts_structure()
        
        print("\n" + "=" * 60)
        print("所有测试通过！")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
