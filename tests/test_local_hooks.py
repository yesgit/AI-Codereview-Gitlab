"""
本地代码审查 Hook 功能测试
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class TestOSDetection:
    """测试操作系统检测功能"""
    
    def test_detect_windows_user_agent(self):
        """测试检测 Windows User-Agent"""
        from api.routers.local_hooks import detect_os_from_user_agent
        
        # Windows User-Agent
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        result = detect_os_from_user_agent(ua)
        assert result == "windows"
        
        # Win32 User-Agent
        ua = "curl/7.68.0 (x86_64-pc-win32)"
        result = detect_os_from_user_agent(ua)
        assert result == "windows"
    
    def test_detect_linux_user_agent(self):
        """测试检测 Linux User-Agent"""
        from api.routers.local_hooks import detect_os_from_user_agent
        
        # Ubuntu User-Agent
        ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        result = detect_os_from_user_agent(ua)
        assert result == "linux"
        
        # curl on Linux
        ua = "curl/7.68.0 (x86_64-pc-linux-gnu)"
        result = detect_os_from_user_agent(ua)
        assert result == "linux"
    
    def test_detect_mac_user_agent(self):
        """测试检测 Mac User-Agent"""
        from api.routers.local_hooks import detect_os_from_user_agent
        
        # macOS User-Agent
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        result = detect_os_from_user_agent(ua)
        assert result == "mac"
        
        # curl on Mac
        ua = "curl/7.64.1 (x86_64-apple-darwin19.0)"
        result = detect_os_from_user_agent(ua)
        assert result == "mac"
    
    def test_detect_unknown_user_agent(self):
        """测试未知 User-Agent"""
        from api.routers.local_hooks import detect_os_from_user_agent
        
        # 空字符串
        result = detect_os_from_user_agent("")
        assert result == "windows"  # 默认返回 windows
        
        # 未知浏览器
        ua = "Mozilla/5.0 (Unknown)"
        result = detect_os_from_user_agent(ua)
        assert result == "windows"


class TestDiffParsing:
    """测试 diff 解析功能"""
    
    def test_parse_simple_diff(self):
        """测试解析简单的 diff"""
        from api.routers.local_hooks import parse_diff
        
        diff_text = """diff --git a/src/main.py b/src/main.py
index 1234567..abcdefg 100644
--- a/src/main.py
+++ b/src/main.py
@@ -1,3 +1,4 @@
 def hello():
-    print("old")
+    print("new")
     return True
"""
        
        changes = parse_diff(diff_text)
        assert len(changes) == 1
        assert changes[0]['new_path'] == "src/main.py"
        assert changes[0]['deleted_file'] == False
        assert 'print("new")' in changes[0]['diff']
    
    def test_parse_multiple_files(self):
        """测试解析多个文件的 diff"""
        from api.routers.local_hooks import parse_diff
        
        diff_text = """diff --git a/src/main.py b/src/main.py
index 1234567..abcdefg 100644
--- a/src/main.py
+++ b/src/main.py
@@ -1,1 +1,1 @@
-old
+new
diff --git a/src/helper.py b/src/helper.py
index abcdefg..1234567 100644
--- a/src/helper.py
+++ b/src/helper.py
@@ -1,1 +1,1 @@
-foo
+bar
"""
        
        changes = parse_diff(diff_text)
        assert len(changes) == 2
        assert changes[0]['new_path'] == "src/main.py"
        assert changes[1]['new_path'] == "src/helper.py"
    
    def test_parse_empty_diff(self):
        """测试解析空的 diff"""
        from api.routers.local_hooks import parse_diff
        
        changes = parse_diff("")
        assert len(changes) == 0


class TestReviewLocalAPI:
    """测试本地审查 API"""
    
    def test_review_local_without_changes(self):
        """测试没有变更的情况"""
        response = client.post(
            "/api/v1/review/local",
            json={
                "diff": "",
                "context": {
                    "gitlab_url": "https://gitlab.com",
                    "project_slug": "test/project",
                    "branch": "main"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True
        assert data['score'] == 100
        assert data['passed'] == True
        assert "没有修改" in data['review_result']
    
    def test_review_local_unsupported_files(self):
        """测试不支持的文件类型"""
        response = client.post(
            "/api/v1/review/local",
            json={
                "diff": """diff --git a/README.md b/README.md
index 1234567..abcdefg 100644
--- a/README.md
+++ b/README.md
@@ -1,1 +1,1 @@
-old content
+new content
""",
                "context": {
                    "gitlab_url": "https://gitlab.com",
                    "project_slug": "test/project",
                    "branch": "main"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True
        assert data['score'] == 100
        assert data['passed'] == True
    
    def test_review_local_context_optional(self):
        """测试上下文信息是可选的"""
        response = client.post(
            "/api/v1/review/local",
            json={
                "diff": """diff --git a/test.py b/test.py
index 1234567..abcdefg 100644
--- a/test.py
+++ b/test.py
@@ -1,1 +1,1 @@
-old
+new
""",
                "context": {}
            }
        )
        
        assert response.status_code == 200


class TestHookScriptGeneration:
    """测试 Hook 脚本生成"""
    
    def test_get_pre_commit_hook_default_windows(self):
        """测试默认返回 Windows 版本"""
        response = client.get("/api/v1/hooks/pre-commit")
        
        assert response.status_code == 200
        assert "pre-commit" in response.headers.get("content-disposition", "")
        assert "bat" in response.headers.get("content-disposition", "")
    
    def test_get_pre_commit_hook_linux(self):
        """测试指定 Linux 版本"""
        response = client.get("/api/v1/hooks/pre-commit?os=linux")
        
        assert response.status_code == 200
        content_disposition = response.headers.get("content-disposition", "")
        assert "pre-commit.sh" in content_disposition or ".sh" in content_disposition
    
    def test_get_pre_commit_hook_mac(self):
        """测试指定 Mac 版本"""
        response = client.get("/api/v1/hooks/pre-commit?os=mac")
        
        assert response.status_code == 200
        content_disposition = response.headers.get("content-disposition", "")
        assert ".sh" in content_disposition
    
    def test_get_pre_commit_ps1(self):
        """测试获取 PowerShell 脚本"""
        response = client.get("/api/v1/hooks/pre-commit.ps1")
        
        assert response.status_code == 200
        assert "pre-commit.ps1" in response.headers.get("content-disposition", "")
        content = response.text
        assert "param(" in content  # PowerShell 函数参数
    
    def test_get_pre_push_hook(self):
        """测试获取 pre-push hook"""
        response = client.get("/api/v1/hooks/pre-push")
        
        assert response.status_code == 200
        assert "pre-push" in response.headers.get("content-disposition", "")
    
    def test_get_install_script_default_windows(self):
        """测试默认返回 Windows 安装脚本"""
        response = client.get("/api/v1/install")
        
        assert response.status_code == 200
        assert "install.bat" in response.headers.get("content-disposition", "")
    
    def test_get_install_script_linux(self):
        """测试指定 Linux 安装脚本"""
        response = client.get("/api/v1/install?os=linux")
        
        assert response.status_code == 200
        content_disposition = response.headers.get("content-disposition", "")
        assert "install.sh" in content_disposition or ".sh" in content_disposition


class TestScriptContent:
    """测试脚本内容"""
    
    def test_unix_script_contains_required_elements(self):
        """测试 Unix 脚本包含必要元素"""
        response = client.get("/api/v1/hooks/pre-commit?os=linux")
        content = response.text
        
        # 检查 shebang
        assert "#!/bin/bash" in content
        
        # 检查关键命令
        assert "git diff --cached" in content
        assert "git config --get remote.origin.url" in content
        assert "curl" in content
        
        # 检查不依赖 jq
        assert "jq" not in content
    
    def test_windows_script_contains_required_elements(self):
        """测试 Windows 脚本包含必要元素"""
        response = client.get("/api/v1/hooks/pre-commit")
        content = response.text
        
        # 检查批处理标记
        assert "@echo off" in content or "REM" in content
        
        # 检查关键命令
        assert "git diff --cached" in content
        assert "git config --get remote.origin.url" in content
        assert "curl" in content
        
        # 检查 PowerShell 检测
        assert "powershell" in content.lower()
    
    def test_install_script_contains_prompts(self):
        """测试安装脚本包含提示"""
        response = client.get("/api/v1/install")
        content = response.text
        
        # 检查安装提示
        assert "🚀" in content or "AI Code Review" in content
        assert "pre-commit" in content


class TestConfigMatching:
    """测试配置匹配逻辑"""
    
    def test_get_config_no_context(self):
        """测试无上下文时使用系统配置"""
        from api.routers.local_hooks import get_review_config
        
        config = get_review_config()
        assert config is not None
        assert config["min_score"] == 60
    
    def test_get_config_with_branch(self):
        """测试有分支信息时的配置"""
        from api.routers.local_hooks import get_review_config
        
        # 注意：这个测试可能需要 mock 数据库
        config = get_review_config(
            gitlab_url="https://gitlab.com",
            project_slug="test/project",
            branch="main"
        )
        
        # 应该返回某种配置（分支级、项目级或系统级）
        assert config is not None
        assert "min_score" in config
        assert "custom_prompt_system" in config


class TestRequestModels:
    """测试请求/响应模型"""
    
    def test_review_context_model(self):
        """测试 ReviewContext 模型"""
        from api.routers.local_hooks import ReviewContext
        
        # 全部字段
        context = ReviewContext(
            gitlab_url="https://gitlab.com",
            project_slug="test/project",
            branch="main"
        )
        assert context.gitlab_url == "https://gitlab.com"
        assert context.project_slug == "test/project"
        assert context.branch == "main"
        
        # 可选字段
        context = ReviewContext()
        assert context.gitlab_url is None
        assert context.project_slug is None
        assert context.branch is None
    
    def test_review_local_request_model(self):
        """测试 ReviewLocalRequest 模型"""
        from api.routers.local_hooks import ReviewLocalRequest, ReviewContext
        
        context = ReviewContext(gitlab_url="https://gitlab.com")
        request = ReviewLocalRequest(
            diff="diff --git a/test.py b/test.py",
            context=context,
            options={"min_score": 70}
        )
        
        assert request.diff == "diff --git a/test.py b/test.py"
        assert request.context.gitlab_url == "https://gitlab.com"
        assert request.options["min_score"] == 70
        
        # 默认值
        request = ReviewLocalRequest(diff="test")
        assert request.context is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
