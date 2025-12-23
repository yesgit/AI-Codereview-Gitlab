# 分支级 Webhook 配置功能

## 功能概述

支持为不同分支配置独立的通知webhook，实现更精细化的消息推送控制。

### 主要特性

1. **三级配置优先级**：分支级 → 项目级 → 系统级
2. **通配符支持**：支持 `feature/*`、`release/*` 等模式匹配
3. **精确匹配优先**：精确匹配 > 最长通配符匹配
4. **新标识方式**：使用 `gitlab_base_url` + `project_slug` 替代 `project_name`

## 配置层级

### 1. 系统级配置（环境变量）
```bash
DINGTALK_WEBHOOK_URL=https://系统级钉钉webhook
FEISHU_WEBHOOK_URL=https://系统级飞书webhook
WECOM_WEBHOOK_URL=https://系统级企微webhook
```

### 2. 项目级配置

通过API或数据库配置：

```json
{
  "gitlab_base_url": "https://gitlab.com",
  "project_slug": "mygroup/myproject",
  "dingtalk_url": "https://项目级钉钉webhook",
  "feishu_url": "https://项目级飞书webhook",
  "wecom_url": "https://项目级企微webhook"
}
```

### 3. 分支级配置

支持通配符模式：

```json
{
  "gitlab_base_url": "https://gitlab.com",
  "project_slug": "mygroup/myproject",
  "branch_pattern": "main",
  "dingtalk_url": "https://主分支专用webhook"
}
```

```json
{
  "gitlab_base_url": "https://gitlab.com",
  "project_slug": "mygroup/myproject",
  "branch_pattern": "feature/*",
  "dingtalk_url": "https://功能分支专用webhook"
}
```

## API 接口

### 分支级 Webhook 管理

#### 1. 获取所有分支级配置

```bash
GET /admin/branch-webhooks
Authorization: Basic admin:password
Query Parameters:
  - gitlab_base_url (可选): 按GitLab实例过滤
  - project_slug (可选): 按项目过滤
```

响应示例：
```json
{
  "data": [
    {
      "id": 1,
      "gitlab_base_url": "https://gitlab.com",
      "project_slug": "mygroup/myproject",
      "branch_pattern": "main",
      "dingtalk_url": "https://...",
      "feishu_url": null,
      "wecom_url": null,
      "created_at": 1234567890,
      "updated_at": 1234567890
    }
  ]
}
```

#### 2. 创建分支级配置

```bash
POST /admin/branch-webhooks
Authorization: Basic admin:password
Content-Type: application/json

{
  "gitlab_base_url": "https://gitlab.com",
  "project_slug": "mygroup/myproject",
  "branch_pattern": "feature/*",
  "dingtalk_url": "https://...",
  "feishu_url": "https://...",
  "wecom_url": "https://..."
}
```

#### 3. 更新分支级配置

```bash
PUT /admin/branch-webhooks/{webhook_id}
Authorization: Basic admin:password
Content-Type: application/json

{
  "gitlab_base_url": "https://gitlab.com",
  "project_slug": "mygroup/myproject",
  "branch_pattern": "feature/*",
  "dingtalk_url": "https://new-url"
}
```

#### 4. 删除分支级配置

```bash
DELETE /admin/branch-webhooks/{webhook_id}
Authorization: Basic admin:password
```

## 使用示例

### 场景1：主分支和开发分支使用不同的webhook

```bash
# 主分支配置
curl -X POST http://localhost:5000/admin/branch-webhooks \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{
    "gitlab_base_url": "https://gitlab.com",
    "project_slug": "myteam/backend",
    "branch_pattern": "main",
    "dingtalk_url": "https://钉钉生产环境群webhook"
  }'

# 开发分支配置
curl -X POST http://localhost:5000/admin/branch-webhooks \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{
    "gitlab_base_url": "https://gitlab.com",
    "project_slug": "myteam/backend",
    "branch_pattern": "develop",
    "dingtalk_url": "https://钉钉开发环境群webhook"
  }'
```

### 场景2：功能分支统一配置

```bash
curl -X POST http://localhost:5000/admin/branch-webhooks \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{
    "gitlab_base_url": "https://gitlab.com",
    "project_slug": "myteam/backend",
    "branch_pattern": "feature/*",
    "dingtalk_url": "https://钉钉功能开发群webhook"
  }'
```

### 场景3：多层级通配符

```bash
# 最具体的模式优先匹配
curl -X POST http://localhost:5000/admin/branch-webhooks \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{
    "gitlab_base_url": "https://gitlab.com",
    "project_slug": "myteam/backend",
    "branch_pattern": "feature/user/*",
    "dingtalk_url": "https://用户功能专用webhook"
  }'

curl -X POST http://localhost:5000/admin/branch-webhooks \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{
    "gitlab_base_url": "https://gitlab.com",
    "project_slug": "myteam/backend",
    "branch_pattern": "feature/*",
    "dingtalk_url": "https://通用功能webhook"
  }'
```

## 匹配规则说明

### 优先级顺序

1. **精确匹配**：`branch_pattern == branch_name`
2. **最长通配符匹配**：按模式长度降序匹配
3. **项目级配置**：如果没有匹配的分支配置
4. **系统级配置**：最终回退

### 通配符语法

- `*`：匹配任意字符（不包括 `/`）
- `?`：匹配单个字符
- 示例：
  - `feature/*` 匹配 `feature/login`、`feature/payment`
  - `release/v?.?` 匹配 `release/v1.0`、`release/v2.3`

### 匹配示例

假设配置如下：
```
1. branch_pattern: "main" (精确)
2. branch_pattern: "feature/user/*" (长度15)
3. branch_pattern: "feature/*" (长度8)
```

匹配结果：
- `main` → 配置1（精确匹配）
- `feature/user/login` → 配置2（最长通配符）
- `feature/payment` → 配置3（短通配符）
- `hotfix/bug` → 项目级配置（无匹配）

## 配置有效性判断

配置被视为"有效"需要满足：
- **记录存在** AND **至少有一个webhook URL非空**

即使数据库中存在配置记录，但所有webhook URL都为空，系统会自动回退到下一级配置。

## 数据库表结构

### branch_webhooks 表

```sql
CREATE TABLE branch_webhooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gitlab_base_url VARCHAR(255) NOT NULL,
    project_slug VARCHAR(255) NOT NULL,
    branch_pattern VARCHAR(255) NOT NULL,
    dingtalk_url TEXT,
    feishu_url TEXT,
    wecom_url TEXT,
    custom_prompt_system TEXT,
    custom_prompt_user TEXT,
    created_at INTEGER,
    updated_at INTEGER,
    UNIQUE(gitlab_base_url, project_slug, branch_pattern)
);
```

### project_webhooks 表（已扩展）

新增字段：
- `gitlab_base_url`: GitLab实例地址
- `project_slug`: 项目slug（path_with_namespace）

保留旧字段以兼容：
- `project_name`: 项目名称（已弃用）
- `url_slug`: URL slug（已弃用）

## 数据库迁移

执行迁移：
```bash
# 升级数据库
alembic upgrade head

# 查看当前版本
alembic current

# 回滚（如需要）
alembic downgrade -1
```

## 向后兼容性

系统完全兼容旧的配置方式：
1. 优先使用新字段 (`gitlab_base_url` + `project_slug`)
2. 如果新字段为空，回退到旧字段 (`url_slug` 或 `project_name`)
3. 环境变量查找逻辑保持不变

## 日志与调试

系统会记录详细的配置匹配日志：

```
✅ 使用分支级配置: https://gitlab.com/mygroup/myproject:feature/login
✅ 精确匹配分支配置: https://gitlab.com/mygroup/myproject:main
✅ 通配符匹配分支配置: https://gitlab.com/mygroup/myproject:feature/payment -> feature/*
⏭️ 分支级配置存在但无有效URL，回退到项目级
✅ 使用项目级配置（新字段）: https://gitlab.com/mygroup/myproject
✅ 使用系统级配置（环境变量）
```

## 注意事项

1. **重复配置**：同一项目的同一分支模式只能有一个配置
2. **通配符顺序**：创建时注意通配符的具体程度，避免被不期望的规则匹配
3. **配置测试**：建议先创建测试配置，验证匹配逻辑后再应用到生产
4. **URL有效性**：确保配置的webhook URL可访问且有效

## 故障排查

### 问题：配置了分支级webhook但没有生效

**检查步骤：**
1. 确认webhook URL是否为空
2. 查看日志中的匹配信息
3. 验证branch_pattern是否正确
4. 检查gitlab_base_url和project_slug是否匹配

### 问题：通配符匹配不符合预期

**解决方案：**
1. 检查是否有更长的模式优先匹配
2. 验证通配符语法是否正确
3. 使用GET接口查看所有配置，检查冲突
