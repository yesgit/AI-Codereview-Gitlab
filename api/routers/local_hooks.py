"""
本地代码审查 Hook 脚本和 API
支持 pre-commit/pre-push 本地审查
"""
import os
import re
from fastapi import APIRouter, Request, Response
from typing import Optional, Dict, Any
from pydantic import BaseModel

from biz.utils.log import logger
from biz.utils.code_reviewer import CodeReviewer
from biz.gitlab.webhook_handler import filter_changes, _normalize_base_url
from biz.service.branch_webhook_service import BranchWebhookService
from biz.service.webhook_service import WebhookService

router = APIRouter()


# ========== 请求/响应模型 ==========

class ReviewContext(BaseModel):
    gitlab_url: Optional[str] = None
    project_slug: Optional[str] = None
    branch: Optional[str] = None


class ReviewLocalRequest(BaseModel):
    diff: str
    context: ReviewContext = ReviewContext()
    options: Optional[Dict[str, Any]] = None


class ReviewLocalResponse(BaseModel):
    success: bool
    score: int
    passed: bool
    review_result: str
    summary: Optional[str] = None


# ========== 配置获取 ==========

def get_review_config(gitlab_url: str = None, project_slug: str = None, branch: str = None) -> dict:
    """
    获取审查配置，按优先级自动匹配
    
    优先级：
    1. 分支级配置（精确匹配）
    2. 分支级配置（通配符匹配）
    3. 项目级配置
    4. 系统级配置（环境变量）
    
    Returns:
        dict: 配置字典
    """
    
    config = {
        "min_score": 60,
        "custom_prompt_system": None,
        "custom_prompt_user": None,
        "review_style": None,
        "supported_extensions": os.getenv("SUPPORTED_EXTENSIONS", ".java,.py,.php")
    }
    
    # 如果没有提供 gitlab_url 或 project_slug，返回系统默认配置
    if not gitlab_url or not project_slug:
        logger.info("ℹ️ 使用系统级配置（环境变量）")
        return config
    
    # 规范化 URL
    gitlab_url = _normalize_base_url(gitlab_url)
    
    # 1. 尝试分支级配置（精确匹配）
    if branch:
        branch_config = BranchWebhookService.get_branch_webhook(
            gitlab_base_url=gitlab_url,
            project_slug=project_slug,
            branch_pattern=branch
        )
        if branch_config:
            logger.info(f"✅ 使用分支级配置（精确匹配）: {gitlab_url}/{project_slug}:{branch}")
            return {
                "min_score": 60,  # 分支级配置暂无此字段，使用默认
                "custom_prompt_system": branch_config.get("custom_prompt_system"),
                "custom_prompt_user": branch_config.get("custom_prompt_user"),
                "review_style": branch_config.get("review_style"),
                "supported_extensions": branch_config.get("supported_extensions")
            }
    
    # 2. 尝试分支级配置（通配符匹配）
    if branch:
        wildcard_config = BranchWebhookService.match_branch_webhook(
            gitlab_base_url=gitlab_url,
            project_slug=project_slug,
            branch_name=branch
        )
        if wildcard_config:
            logger.info(f"✅ 使用分支级配置（通配符匹配）: {gitlab_url}/{project_slug}:{branch} -> {wildcard_config['branch_pattern']}")
            return {
                "min_score": 60,
                "custom_prompt_system": wildcard_config.get("custom_prompt_system"),
                "custom_prompt_user": wildcard_config.get("custom_prompt_user"),
                "review_style": wildcard_config.get("review_style"),
                "supported_extensions": wildcard_config.get("supported_extensions")
            }
    
    # 3. 尝试项目级配置
    try:
        project_config = WebhookService.get_webhook_mapping_by_gitlab_project(
            gitlab_base_url=gitlab_url,
            project_slug=project_slug
        )
    except Exception as e:
        logger.warning(f"⚠️ 获取项目级配置失败: {e}")
        project_config = None
    
    if project_config:
        logger.info(f"✅ 使用项目级配置: {gitlab_url}/{project_slug}")
        return {
            "min_score": 60,
            "custom_prompt_system": project_config.get("custom_prompt_system"),
            "custom_prompt_user": project_config.get("custom_prompt_user"),
            "review_style": project_config.get("review_style"),
            "supported_extensions": project_config.get("supported_extensions")
        }
    
    # 4. 使用系统级配置
    logger.info(f"ℹ️ 使用系统级配置（环境变量）")
    return config


def parse_diff(diff_text: str) -> list:
    """
    解析 git diff 输出，转换为 changes 列表
    
    简化实现：只提取文件名和 diff 内容
    
    Returns:
        list: changes 列表
    """
    changes = []
    lines = diff_text.split('\n')
    
    current_file = None
    current_diff = []
    in_diff = False
    
    for line in lines:
        # 匹配文件头：diff --git a/file b/file
        if line.startswith('diff --git'):
            # 保存上一个文件
            if current_file and current_diff:
                changes.append({
                    'new_path': current_file,
                    'diff': '\n'.join(current_diff),
                    'deleted_file': False
                })
            
            # 开始新文件
            match = re.search(r'diff --git a/[^ ]+ b/(.+)', line)
            if match:
                current_file = match.group(1)
            else:
                current_file = "unknown"
            
            current_diff = [line]
            in_diff = True
        elif in_diff:
            current_diff.append(line)
    
    # 保存最后一个文件
    if current_file and current_diff:
        changes.append({
            'new_path': current_file,
            'diff': '\n'.join(current_diff),
            'deleted_file': False
        })
    
    return changes


def detect_os_from_user_agent(user_agent: str) -> str:
    """
    根据 User-Agent 检测操作系统
    
    返回值: 'windows' | 'linux' | 'mac' | 'unknown'
    """
    if not user_agent:
        return 'windows'  # 默认返回 windows
    
    ua = user_agent.lower()
    
    # Windows 检测
    if re.search(r'windows|win32|win64|msie|trident', ua):
        return 'windows'
    
    # macOS 检测
    if re.search(r'mac|macintosh|darwin|osx', ua):
        return 'mac'
    
    # Linux 检测
    if re.search(r'linux|x11|ubuntu|debian|fedora|curl|wget', ua):
        return 'linux'
    
    return 'windows'  # 默认返回 windows


# ========== API 端点 ==========

@router.post("/review/local", response_model=ReviewLocalResponse, tags=["本地审查"])
async def review_local(request: Request, body: ReviewLocalRequest):
    """
    本地代码审查 API（不记录数据库）
    
    自动匹配配置：
    1. 分支级配置（gitlab_url + project_slug + branch）
    2. 项目级配置（gitlab_url + project_slug）
    3. 系统级配置（环境变量）
    
    Args:
        diff: git diff 输出
        context: 上下文信息（gitlab_url, project_slug, branch）
        options: 选项（min_score, format 等）
    """
    try:
        # 解析 diff
        changes = parse_diff(body.diff)
        
        # 过滤变更
        changes = filter_changes(changes)
        
        if not changes:
            return ReviewLocalResponse(
                success=True,
                score=100,
                passed=True,
                review_result="关注的文件没有修改",
                summary="无需要审查的文件"
            )
        
        # 获取配置（自动匹配）
        config = get_review_config(
            gitlab_url=body.context.gitlab_url,
            project_slug=body.context.project_slug,
            branch=body.context.branch
        )
        
        # 获取最低分数
        min_score = body.options.get('min_score') if body.options else None
        if min_score is None:
            min_score = config.get("min_score", 60)
        
        # 执行代码评审（review_changes_in_batches 内部会从数据库获取配置）
        code_reviewer = CodeReviewer()
        review_result = code_reviewer.review_changes_in_batches(
            changes=changes,
            commits_text="Local review",
            project_name=body.context.project_slug or "Unknown",
            gitlab_base_url=body.context.gitlab_url,
            project_slug=body.context.project_slug,
            branch_name=body.context.branch or ""
        )
        
        # 解析分数
        score = CodeReviewer.parse_review_score(review_text=review_result)
        
        # 判断是否通过
        passed = score >= min_score
        
        return ReviewLocalResponse(
            success=True,
            score=score,
            passed=passed,
            review_result=review_result,
            summary=f"代码审查完成，得分: {score}/{min_score}"
        )
        
    except Exception as e:
        logger.error(f"本地审查失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return ReviewLocalResponse(
            success=False,
            score=0,
            passed=False,
            review_result=f"AI 评审失败: {str(e)}",
            summary="审查失败"
        )


# ========== Hook 脚本生成 ==========

def generate_pre_commit_script_unix(api_url: str) -> str:
    """生成 Unix/Linux/Mac 版本的 pre-commit hook 脚本"""
    return f"""#!/bin/bash
set -e

# 配置
API_URL="${{AI_REVIEW_API_URL:-{api_url}}}"
MIN_SCORE="${{AI_REVIEW_MIN_SCORE:-60}}"

# 颜色输出
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m'

# 检查是否有暂存的文件
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)
if [ -z "$STAGED_FILES" ]; then
    exit 0
fi

# 获取 git remote 信息
REMOTE_URL=$(git config --get remote.origin.url)
BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)

# 从 remote URL 提取 GitLab URL 和项目路径
GITLAB_URL=""
PROJECT_SLUG=""

if [[ "$REMOTE_URL" =~ git@(.+):(.+)\\.git$ ]]; then
    # SSH 格式: git@gitlab.com:user/project.git
    GITLAB_URL="https://${{BASH_REMATCH[1]}}"
    PROJECT_SLUG="${{BASH_REMATCH[2]}}"
elif [[ "$REMOTE_URL" =~ https?://(.+?)/(.+)\\.git$ ]]; then
    # HTTPS 格式: https://gitlab.com/user/project.git
    GITLAB_URL="https://${{BASH_REMATCH[1]}}"
    PROJECT_SLUG="${{BASH_REMATCH[2]}}"
fi

echo "${{GREEN}}🤖 AI 代码审查中...${{NC}}"
if [ -n "$PROJECT_SLUG" ]; then
    echo "   项目: $PROJECT_SLUG"
    echo "   分支: $BRANCH_NAME"
fi

# 获取 diff
DIFF=$(git diff --cached)

# 构造 JSON 请求体（不依赖外部工具）
JSON_STRING="{{\\\"diff\\\": \\\""
JSON_STRING+=$(echo "$DIFF" | sed 's/\\\\\\\\/\\\\\\\\\\\\\\\\/g' | sed 's/"/\\\\\\\\"/g' | tr -d '\\n' | awk '{{printf "%s", $0}}')
JSON_STRING+="\\\""

if [ -n "$GITLAB_URL" ] && [ -n "$PROJECT_SLUG" ] && [ -n "$BRANCH_NAME" ]; then
    JSON_STRING+=", \\\"context\\\": {{\\\"gitlab_url\\\": \\\"$GITLAB_URL\\\", \\\"project_slug\\\": \\\"$PROJECT_SLUG\\\", \\\"branch\\\": \\\"$BRANCH_NAME\\\"}}"
fi

JSON_STRING+="}}"

# 调用 API
RESPONSE=$(curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d "$JSON_STRING")

# 解析 JSON（使用 grep/sed，不依赖外部工具）
SCORE=$(echo "$RESPONSE" | grep -o '"score":[0-9]*' | cut -d: -f2)
PASSED=$(echo "$RESPONSE" | grep -o '"passed":[a-z]*' | cut -d: -f2)
RESULT=$(echo "$RESPONSE" | sed 's/.*"review_result":"\\(.*\\)\\\\"}}$/\\1/' | sed 's/\\\\n/\\n/g')

if [ "$PASSED" != "true" ]; then
    echo "${{RED}}❌ 代码审查未通过 (得分: $SCORE，最低要求: $MIN_SCORE)${{NC}}"
    echo ""
    echo "$RESULT" | sed 's/\\\\n/\\n/g'
    echo ""
    echo "${{YELLOW}}💡 提示：${{NC}}"
    echo "1. 修复问题后重新提交"
    echo "2. 跳过检查: git commit --no-verify"
    exit 1
fi

echo "${{GREEN}}✅ 代码审查通过 (得分: $SCORE)${{NC}}"
exit 0
"""


def generate_pre_commit_script_windows(api_url: str) -> str:
    """生成 Windows 版本的 pre-commit hook 脚本（智能检测 PowerShell）"""
    return f"""@echo off
setlocal enabledelayedexpansion

REM 配置
if "%AI_REVIEW_API_URL%"=="" set AI_REVIEW_API_URL={api_url}
if "%AI_REVIEW_MIN_SCORE%"=="" set AI_REVIEW_MIN_SCORE=60

REM 检查 PowerShell 是否可用
where powershell >nul 2>&1
if not errorlevel 1 (
    REM PowerShell 可用，调用 PowerShell 版本
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0pre-commit.ps1" "%AI_REVIEW_API_URL%" "%AI_REVIEW_MIN_SCORE%"
    exit /b !errorlevel!
)

REM ===== PowerShell 不可用，使用纯批处理版本 =====

REM 检查暂存文件
for /f "usebackq delims=" %%f in (`git diff --cached --name-only --diff-filter=ACM`) do (
    set STAGED_FILES=1
)

if not defined STAGED_FILES (
    exit /b 0
)

REM 获取 git remote 信息
for /f "delims=" %%i in ('git config --get remote.origin.url') do set REMOTE_URL=%%i
for /f "delims=" %%i in ('git rev-parse --abbrev-ref HEAD') do set BRANCH_NAME=%%i

REM 从 remote URL 提取 GitLab URL 和项目路径
set GITLAB_URL=
set PROJECT_SLUG=

echo !REMOTE_URL! | findstr /C:"git@" >nul
if not errorlevel 1 (
    REM SSH 格式: git@gitlab.com:user/project.git
    for /f "tokens=1-2 delims=@" %%a in ("!REMOTE_URL!") do set HOST=%%b
    set HOST=!HOST:.git=!
    for /f "tokens=1,2 delims=:" %%a in ("!HOST!") do (
        set GITLAB_URL=https://%%a
        set PROJECT_SLUG=%%b
    )
) else (
    echo !REMOTE_URL! | findstr /C:"https://" >nul
    if not errorlevel 1 (
        REM HTTPS 格式: https://gitlab.com/user/project.git
        set TEMP_URL=!REMOTE_URL:https://=!
        for /f "tokens=1,2 delims=/" %%a in ("!TEMP_URL!") do (
            set GITLAB_URL=https://%%a
            set PROJ=%%b
        )
        set PROJECT_SLUG=!PROJ:.git=!
    )
)

echo 🤖 AI 代码审查中...
if defined PROJECT_SLUG (
    echo    项目: !PROJECT_SLUG!
    echo    分支: !BRANCH_NAME!
)

REM 获取 diff
git diff --cached > %TEMP%\\ai-review-diff.txt

REM 构造 JSON 请求体（简化版）
set JSON={{\\\"diff\\\": \\\"\\"

REM 处理 diff 内容（简化处理）
for /f "usebackq delims=" %%L in (%TEMP%\\ai-review-diff.txt) do (
    set LINE=%%L
    set LINE=!LINE:\\=\\\\!
    set LINE=!LINE:"=\\\\\\\"!
    set JSON=!JSON!!LINE!
)

set JSON=!JSON!\\\"\\"

if defined GITLAB_URL (
    if defined PROJECT_SLUG (
        if defined BRANCH_NAME (
            set JSON=!JSON!, \\\"context\\\": {{\\\"gitlab_url\\\": \\\"!GITLAB_URL!\\\", \\\"project_slug\\\": \\\"!PROJECT_SLUG!\\\", \\\"branch\\\": \\\"!BRANCH_NAME!\\\"}}
        )
    )
)

set JSON=!JSON!}}

REM 调用 API 并保存响应
curl -s -X POST "%AI_REVIEW_API_URL%" -H "Content-Type: application/json" -d "!JSON!" > %TEMP%\\ai-review-result.json

REM 简化解析：只提取关键信息
set SCORE=
for /f "tokens=2 delims=:," %%a in ('type %TEMP%\\ai-review-result.json ^| findstr /C:\\"score\\"') do set SCORE=%%a
set SCORE=!SCORE: =!
set SCORE=!SCORE:~0,-1!

set PASSED=
for /f "tokens=2 delims=:," %%a in ('type %TEMP%\\ai-review-result.json ^| findstr /C:\\"passed\\"') do set PASSED=%%a
set PASSED=!PASSED: =!
set PASSED=!PASSED:~0,-1!

REM 清理临时文件
del %TEMP%\\ai-review-diff.txt 2>nul

if "%PASSED%" neq "true" (
    echo ❌ 代码审查未通过 ^(得分: %SCORE%，最低要求: %AI_REVIEW_MIN_SCORE%^)
    echo.
    echo 详细结果已保存到: %TEMP%\\ai-review-result.json
    echo.
    echo 💡 提示：
    echo 1. 修复问题后重新提交
    echo 2. 跳过检查: git commit --no-verify
    del %TEMP%\\ai-review-result.json 2>nul
    exit /b 1
)

echo ✅ 代码审查通过 ^(得分: %SCORE%^)
del %TEMP%\\ai-review-result.json 2>nul
exit /b 0
"""


def generate_pre_commit_ps1(api_url: str) -> str:
    """生成 PowerShell 辅助脚本"""
    return f"""# pre-commit.ps1
param(
    [string]$ApiUrl = "{api_url}",
    [int]$MinScore = 60
)

try {{
    # 检查暂存文件
    $stagedFiles = git diff --cached --name-only --diff-filter=ACM
    if ([string]::IsNullOrEmpty($stagedFiles)) {{
        exit 0
    }}

    # 获取 git 信息
    $remoteUrl = git config --get remote.origin.url
    $branchName = git rev-parse --abbrev-ref HEAD

    # 解析 GitLab URL 和项目路径
    $gitlabUrl = ""
    $projectSlug = ""

    if ($remoteUrl -match "^git@(.+):(.+)\\.git$") {{
        $gitlabUrl = "https://$($matches[1])"
        $projectSlug = $matches[2]
    }} elseif ($remoteUrl -match "^https?://(.+?)/(.+)\\.git$") {{
        $gitlabUrl = "https://$($matches[1])"
        $projectSlug = $matches[2]
    }}

    Write-Host "🤖 AI 代码审查中..."
    if ($projectSlug) {{
        Write-Host "   项目: $projectSlug"
        Write-Host "   分支: $branchName"
    }}

    # 获取 diff
    $diff = git diff --cached

    # 构造 JSON
    $json = @{{
        diff = $diff -replace '\\\\', '\\\\\\\\' -replace '"', '\\\\\\"' -replace "`n", '\\\\n' -replace "`r", '\\\\r'
    }}

    if ($gitlabUrl -and $projectSlug -and $branchName) {{
        $json.context = @{{
            gitlab_url = $gitlabUrl
            project_slug = $projectSlug
            branch = $branchName
        }}
    }}

    $jsonBody = $json | ConvertTo-Json -Compress

    # 调用 API
    $response = curl -s -X POST $ApiUrl -H "Content-Type: application/json" -d $jsonBody
    $result = $response | ConvertFrom-Json

    # 判断结果
    if ($result.passed -eq $false) {{
        Write-Host "❌ 代码审查未通过 (得分: $($result.score)，最低要求: $MinScore)" -ForegroundColor Red
        Write-Host ""
        Write-Host $result.review_result
        Write-Host ""
        Write-Host "💡 提示：" -ForegroundColor Yellow
        Write-Host "1. 修复问题后重新提交"
        Write-Host "2. 跳过检查: git commit --no-verify"
        exit 1
    }}

    Write-Host "✅ 代码审查通过 (得分: $($result.score))" -ForegroundColor Green
    exit 0

}} catch {{
    Write-Host "❌ AI 代码审查失败: $_" -ForegroundColor Red
    Write-Host "💡 提示：使用 --no-verify 跳过检查"
    exit 1
}}
"""


def generate_install_script_unix(api_base_url: str) -> str:
    """生成 Unix/Linux/Mac 安装脚本"""
    return f"""set -e

echo "🚀 AI Code Review Hook 安装程序"
echo ""

# 检查是否在 Git 仓库中
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ 错误：当前目录不是 Git 仓库"
    exit 1
fi

API_URL="{api_base_url}/api/v1/review/local"
API_BASE_URL="{api_base_url}"

echo "📥 从 $API_BASE_URL 下载 hook 脚本..."

# 下载 pre-commit
curl -s "$API_BASE_URL/hooks/pre-commit" > .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
echo "✅ pre-commit hook 已安装"

# 询问是否安装 pre-push
read -p "是否安装 pre-push hook？(y/N): " install_prepush
if [ "$install_prepush" = "y" ] || [ "$install_prepush" = "Y" ]; then
    curl -s "$API_BASE_URL/hooks/pre-push" > .git/hooks/pre-push
    chmod +x .git/hooks/pre-push
    echo "✅ pre-push hook 已安装"
fi

echo ""
echo "🎉 安装完成！"
echo ""
echo "配置环境变量（可选）："
echo "  export AI_REVIEW_API_URL=$API_URL"
echo "  export AI_REVIEW_MIN_SCORE=60"
echo ""
echo "使用方法："
echo "  正常提交：git commit -m 'xxx'"
echo "  跳过检查：git commit --no-verify -m 'xxx'"
"""


def generate_install_script_windows(api_base_url: str) -> str:
    """生成 Windows 安装脚本"""
    return f"""@echo off
setlocal enabledelayedexpansion

echo 🚀 AI Code Review Hook 安装程序
echo.

REM 检查是否在 Git 仓库中
git rev-parse --git-dir >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：当前目录不是 Git 仓库
    exit /b 1
)

set API_URL={api_base_url}/review/local
set API_BASE_URL={api_base_url}

echo 📥 从 !API_BASE_URL! 下载 hook 脚本...

REM 创建 hooks 目录
if not exist .git\\\\hooks mkdir .git\\\\hooks

REM 下载 pre-commit
curl -s "!API_BASE_URL!/hooks/pre-commit" > .git\\\\hooks\\\\pre-commit
echo ✅ pre-commit hook 已安装

REM 下载 PowerShell 辅助脚本（如果检测到 PowerShell）
where powershell >nul 2>&1
if not errorlevel 1 (
    curl -s "!API_BASE_URL!/hooks/pre-commit.ps1" > .git\\\\hooks\\\\pre-commit.ps1
)

REM 询问是否安装 pre-push
set /p install_prepush="是否安装 pre-push hook？(y/N): "
if /i "!install_prepush!"=="y" (
    curl -s "!API_BASE_URL!/hooks/pre-push" > .git\\\\hooks\\\\pre-push
    if not errorlevel 1 (
        where powershell >nul 2>&1
        if not errorlevel 1 (
            curl -s "!API_BASE_URL!/hooks/pre-push.ps1" > .git\\\\hooks\\\\pre-push.ps1
        )
    )
    echo ✅ pre-push hook 已安装
)

echo.
echo 🎉 安装完成！
echo.
echo 配置环境变量（可选）：
echo   set AI_REVIEW_API_URL=!API_URL!
echo   set AI_REVIEW_MIN_SCORE=60
echo.
echo 使用方法：
echo   正常提交：git commit -m "xxx"
echo   跳过检查：git commit --no-verify -m "xxx"
"""


# ========== Hook 端点 ==========

@router.get("/hooks/pre-commit/{os_type}", tags=["Hook脚本"])
async def get_pre_commit_hook_by_os(request: Request, os_type: str):
    """
    获取 pre-commit hook 脚本（通过 URL 指定系统）
    
    os_type: linux | mac | windows
    """
    api_url = f"{request.url.scheme}://{request.url.netloc}/api/v1/review/local"
    
    if os_type in ("linux", "mac"):
        # Unix/Linux/Mac
        script_content = generate_pre_commit_script_unix(api_url)
        filename = "pre-commit.sh"
    else:
        # Windows
        script_content = generate_pre_commit_script_windows(api_url)
        filename = "pre-commit.bat"
    
    return Response(
        content=script_content,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/hooks/pre-commit", tags=["Hook脚本"])
async def get_pre_commit_hook(request: Request, os: str = None):
    """
    获取 pre-commit hook 脚本（通过 User-Agent 自动检测）
    """
    api_url = f"{request.url.scheme}://{request.url.netloc}/api/v1/review/local"
    
    # 判断操作系统
    detected_os = os or detect_os_from_user_agent(request.headers.get("user-agent", ""))
    
    if detected_os in ("linux", "mac"):
        # Unix/Linux/Mac
        script_content = generate_pre_commit_script_unix(api_url)
        filename = "pre-commit.sh"
    else:
        # 默认返回 Windows 版本
        script_content = generate_pre_commit_script_windows(api_url)
        filename = "pre-commit.bat"
    
    return Response(
        content=script_content,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/hooks/pre-commit.ps1", tags=["Hook脚本"])
async def get_pre_commit_hook_ps1(request: Request):
    """获取 PowerShell 辅助脚本"""
    api_url = f"{request.url.scheme}://{request.url.netloc}/api/v1/review/local"
    script_content = generate_pre_commit_ps1(api_url)
    
    return Response(
        content=script_content,
        media_type="text/plain",
        headers={"Content-Disposition": 'attachment; filename="pre-commit.ps1"'}
    )


@router.get("/hooks/pre-push/{os_type}", tags=["Hook脚本"])
async def get_pre_push_hook_by_os(request: Request, os_type: str):
    """
    获取 pre-push hook 脚本（通过 URL 指定系统）
    """
    api_url = f"{request.url.scheme}://{request.url.netloc}/api/v1/review/local"
    
    if os_type in ("linux", "mac"):
        # Unix/Linux/Mac
        script_content = generate_pre_commit_script_unix(api_url)
        filename = "pre-push.sh"
    else:
        # Windows
        script_content = generate_pre_commit_script_windows(api_url)
        filename = "pre-push.bat"
    
    return Response(
        content=script_content,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/hooks/pre-push", tags=["Hook脚本"])
async def get_pre_push_hook(request: Request, os: str = None):
    """
    获取 pre-push hook 脚本（通过 User-Agent 自动检测）
    """
    api_url = f"{request.url.scheme}://{request.url.netloc}/api/v1/review/local"
    
    # 判断操作系统
    detected_os = os or detect_os_from_user_agent(request.headers.get("user-agent", ""))
    
    if detected_os in ("linux", "mac"):
        # Unix/Linux/Mac
        script_content = generate_pre_commit_script_unix(api_url)
        filename = "pre-push.sh"
    else:
        # 默认返回 Windows 版本
        script_content = generate_pre_commit_script_windows(api_url)
        filename = "pre-push.bat"
    
    return Response(
        content=script_content,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/hooks/pre-push.ps1", tags=["Hook脚本"])
async def get_pre_push_hook_ps1(request: Request):
    """获取 pre-push PowerShell 辅助脚本"""
    return await get_pre_commit_hook_ps1(request)


@router.get("/install/{os_type}", tags=["Hook脚本"])
async def get_install_script_by_os(request: Request, os_type: str):
    """
    获取安装脚本（通过 URL 指定系统）
    
    os_type: linux | mac | windows
    """
    api_base_url = f"{request.url.scheme}://{request.url.netloc}"
    
    if os_type in ("linux", "mac"):
        # Unix/Linux/Mac
        script_content = generate_install_script_unix(api_base_url)
        filename = "install.sh"
    else:
        # Windows
        script_content = generate_install_script_windows(api_base_url)
        filename = "install.bat"
    
    return Response(
        content=script_content,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/install", tags=["Hook脚本"])
async def get_install_script(request: Request, os: str = None):
    """
    获取安装脚本（通过 User-Agent 自动检测）
    """
    api_base_url = f"{request.url.scheme}://{request.url.netloc}"
    
    # 判断操作系统
    detected_os = os or detect_os_from_user_agent(request.headers.get("user-agent", ""))
    
    if detected_os in ("linux", "mac"):
        # Unix/Linux/Mac
        script_content = generate_install_script_unix(api_base_url)
        filename = "install.sh"
    else:
        # 默认返回 Windows 版本
        script_content = generate_install_script_windows(api_base_url)
        filename = "install.bat"
    
    return Response(
        content=script_content,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
