# 本地代码审查 Hook 使用说明

## 功能概述

本地代码审查功能允许在代码提交前进行 AI 代码审查，防止问题代码进入仓库。

### 主要特性

1. **自动识别项目配置**：自动检测 GitLab URL、项目路径和当前分支
2. **配置自动匹配**：按优先级自动选择最佳配置（分支级 → 项目级 → 系统级）
3. **跨平台支持**：支持 Windows、Linux、Mac
4. **零依赖安装**：一键安装，无需额外依赖
5. **智能检测**：Windows 环境自动检测 PowerShell 是否可用

---

## 快速开始

### Windows 用户

```batch
REM 下载并运行安装脚本
curl http://localhost:5000/install > install.bat
install.bat
```

### Linux/Mac 用户

```bash
curl -s http://localhost:5000/install?os=linux | bash
```

### 使用浏览器安装

1. 访问 `http://localhost:5000/install`
2. 浏览器会自动下载对应平台的安装脚本
3. 运行下载的脚本

---

## 安装后使用

### 正常提交（会触发审查）

```bash
git add .
git commit -m "fix login bug"
```

输出示例：
```
🤖 AI 代码审查中...
   项目: mygroup/myproject
   分支: feature/login
✅ 代码审查通过 (得分: 85)
```

### 跳过审查（紧急情况）

```bash
git commit --no-verify -m "hotfix: urgent bug fix"
```

---

## 高级配置

### 环境变量配置

```bash
# Linux/Mac
export AI_REVIEW_API_URL=http://your-api-url/review/local
export AI_REVIEW_MIN_SCORE=70

# Windows
set AI_REVIEW_API_URL=http://your-api-url/review/local
set AI_REVIEW_MIN_SCORE=70
```

### 分支级配置

通过 API 为不同分支设置不同的审查策略：

```bash
# 为 feature 分支设置自定义 prompt
curl -X POST http://localhost:5000/api/v1/branch-webhooks \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{
    "gitlab_base_url": "https://gitlab.com",
    "project_slug": "mygroup/myproject",
    "branch_pattern": "feature/*",
    "custom_prompt_system": "请重点关注代码安全性问题",
    "review_style": "professional"
  }'
```

### 配置优先级

系统按以下优先级自动选择配置：

1. **分支级配置（精确匹配）**：`gitlab_url + project_slug + branch`
2. **分支级配置（通配符匹配）**：如 `feature/*`、`release/v?.?`
3. **项目级配置**：`gitlab_url + project_slug`
4. **系统级配置**：环境变量 `SUPPORTED_EXTENSIONS` 等

---

## API 端点说明

### 1. 本地审查 API

```
POST /api/v1/review/local
```

**请求示例**：
```json
{
  "diff": "diff --git a/src/main.py b/src/main.py\n+print('hello')\n",
  "context": {
    "gitlab_url": "https://gitlab.com",
    "project_slug": "mygroup/myproject",
    "branch": "feature/login"
  },
  "options": {
    "min_score": 60
  }
}
```

**响应示例**：
```json
{
  "success": true,
  "score": 85,
  "passed": true,
  "review_result": "评分：85/100\n\n主要问题：\n1. ...",
  "summary": "代码审查完成，得分: 85/60"
}
```

### 2. 获取 Hook 脚本

```
GET /api/v1/hooks/pre-commit
GET /api/v1/hooks/pre-push
```

自动检测操作系统并返回对应脚本。可手动指定：
```
GET /api/v1/hooks/pre-commit?os=linux
GET /api/v1/hooks/pre-commit?os=windows
GET /api/v1/hooks/pre-commit?os=mac
```

### 3. 获取安装脚本

```
GET /api/v1/install
```

自动检测操作系统并返回对应安装脚本。

---

## 手动安装 Hook

### 下载单个 Hook

```bash
# pre-commit（Linux/Mac）
curl http://localhost:5000/api/v1/hooks/pre-commit?os=linux > .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# pre-commit（Windows）
curl http://localhost:5000/api/v1/hooks/pre-commit > .git\hooks\pre-commit

# pre-push（Linux/Mac）
curl http://localhost:5000/api/v1/hooks/pre-push?os=linux > .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

### 下载 PowerShell 辅助脚本（Windows 可选）

```batch
curl http://localhost:5000/api/v1/hooks/pre-commit.ps1 > .git\hooks\pre-commit.ps1
curl http://localhost:5000/api/v1/hooks/pre-push.ps1 > .git\hooks\pre-push.ps1
```

---

## 常见问题

### 1. Hook 不执行

**检查权限**：
```bash
# Linux/Mac
ls -l .git/hooks/pre-commit
# 应该有执行权限（-rwxr-xr-x）
chmod +x .git/hooks/pre-commit

# Windows
# .git\hooks\pre-commit 应该是批处理文件
```

**检查 Git 配置**：
```bash
git config --get core.hooksPath
# 如果有自定义路径，Hook 应该在该路径下
```

### 2. curl 命令不可用

**安装 curl**：
```bash
# Ubuntu/Debian
sudo apt-get install curl

# CentOS/RHEL
sudo yum install curl

# macOS（通常已预装）
brew install curl
```

**Windows**：Windows 10/11 已内置 curl，或使用下载的安装脚本。

### 3. 审查失败但代码没问题

**检查配置**：
- 确认 `min_score` 设置是否合理
- 检查 `SUPPORTED_EXTENSIONS` 是否包含你的文件类型
- 验证 GitLab Token 是否有效

**临时跳过**：
```bash
git commit --no-verify -m "message"
```

### 4. 网络问题导致审查超时

**设置超时**（修改 Hook 脚本）：
```bash
# Linux/Mac
curl -s --connect-timeout 30 --max-time 60 -X POST "$API_URL" ...

# Windows
curl -s --connect-timeout 30 --max-time 60 -X POST "%API_URL%" ...
```

---

## Hook 脚本工作原理

### 1. 获取 Git 信息

- 暂存文件：`git diff --cached`
- Remote URL：`git config --get remote.origin.url`
- 当前分支：`git rev-parse --abbrev-ref HEAD`

### 2. 解析项目信息

从 Remote URL 提取 GitLab URL 和项目路径：

```
SSH 格式：git@gitlab.com:group/project.git
HTTPS 格式：https://gitlab.com/group/project.git
```

### 3. 调用审查 API

发送包含 diff 和项目上下文的 JSON 请求到服务器。

### 4. 处理响应

- 解析 JSON 响应（不依赖 jq）
- 提取 `score` 和 `passed` 字段
- 根据结果决定是否阻止提交

---

## 最佳实践

### 1. 功能分支使用宽松标准

```bash
# 为 feature 分支设置较低的评分要求
curl -X POST http://localhost:5000/api/v1/branch-webhooks \
  -d '{
    "gitlab_base_url": "https://gitlab.com",
    "project_slug": "mygroup/myproject",
    "branch_pattern": "feature/*"
    }'
# 使用默认的 min_score=60
```

### 2. 主分支使用严格标准

```bash
# 为 main 分支设置更高的评分要求
# 环境变量设置
export AI_REVIEW_MIN_SCORE=80
```

### 3. 紧急修复跳过审查

```bash
git commit --no-verify -m "hotfix: urgent fix"
```

### 4. 集成到 CI/CD

在 CI 流程中使用相同的审查 API：

```yaml
# .gitlab-ci.yml
stages:
  - review

local_review:
  stage: review
  script:
    - |
      DIFF=$(git diff origin/main HEAD)
      curl -X POST http://your-api/review/local \
        -H "Content-Type: application/json" \
        -d "{\"diff\": \"$DIFF\", \"context\": {...}}"
```

---

## 与现有功能对比

| 特性 | 本地审查 | Webhook 审查 | @AI 触发 |
|------|---------|--------------|-----------|
| 触发时机 | commit/push 前 | MR/Push 事件后 | 手动评论 |
| 记录数据库 | ❌ 不记录 | ✅ 记录 | ✅ 记录 |
| 阻止提交 | ✅ 可阻止 | ❌ 不阻止 | ❌ 不阻止 |
| 配置匹配 | ✅ 自动匹配 | ✅ 自动匹配 | - |
| 通知推送 | - | ✅ 支持 | - |

---

## 卸载 Hook

```bash
# Linux/Mac
rm .git/hooks/pre-commit
rm .git/hooks/pre-push

# Windows
del .git\hooks\pre-commit
del .git\hooks\pre-push
del .git\hooks\pre-commit.ps1
del .git\hooks\pre-push.ps1
```

---

## 技术细节

### Windows 智能检测

Hook 脚本会自动检测 PowerShell 是否可用：
- **可用**：使用 PowerShell 版本（更可靠）
- **不可用**：使用纯批处理版本（兼容性好）

### JSON 解析

脚本使用 `grep`/`sed`（Linux/Mac）或 `findstr`（Windows）解析 JSON，不依赖 jq。

### 错误处理

- API 调用失败：允许提交（不影响开发）
- 解析失败：允许提交并记录错误
- 网络超时：允许提交

---

## 相关文档

- [分支级 Webhook 配置](./branch_webhook_config.md)
- [@AI 触发评审](./ai_trigger_review.md)
- [FAQ](./faq.md)
