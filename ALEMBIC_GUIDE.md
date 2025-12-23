# Alembic 数据库迁移指南

## 📍 Alembic 命令位置

```bash
# Alembic 已安装在
/Users/hedawei/.pyenv/shims/alembic

# 可以直接使用
alembic --version
```

---

## 📁 项目中的 Alembic 结构

```
AI-Codereview-Gitlab/
├── alembic.ini              # Alembic 配置文件
└── alembic/
    ├── env.py               # 环境配置
    └── versions/            # 迁移脚本目录
        ├── 20251222_initial_schema.py
        ├── 20251223_add_branch_webhooks.py
        └── 20251223_add_gitlab_token.py
```

---

## 🚀 常用 Alembic 命令

### 1. 查看当前数据库版本

```bash
cd /Users/hedawei/Projects/AI-Codereview-Gitlab
alembic current
```

### 2. 查看迁移历史

```bash
alembic history --verbose
```

### 3. 升级到最新版本

```bash
# 升级到最新版本（head）
alembic upgrade head

# 升级一个版本
alembic upgrade +1

# 升级到指定版本
alembic upgrade 20251223_add_gitlab_token
```

### 4. 降级数据库版本

```bash
# 降级一个版本
alembic downgrade -1

# 降级到指定版本
alembic downgrade 20251222_initial_schema

# 降级到初始状态
alembic downgrade base
```

### 5. 创建新的迁移脚本

```bash
# 自动生成迁移脚本（基于模型变更）
alembic revision --autogenerate -m "描述信息"

# 手动创建空的迁移脚本
alembic revision -m "add_new_column"
```

### 6. 查看 SQL 语句（不执行）

```bash
# 查看升级的 SQL
alembic upgrade head --sql

# 查看降级的 SQL
alembic downgrade -1 --sql
```

---

## 📋 当前项目的迁移版本

### 版本 1: 20251222_initial_schema.py
**创建时间**: 2024-12-22
**功能**: 初始数据库模式
- 创建 webhook_mappings 表
- 创建 mr_review_logs 表
- 创建 push_review_logs 表

### 版本 2: 20251223_add_branch_webhooks.py
**创建时间**: 2024-12-23
**功能**: 添加分支级 Webhook 支持
- 创建 branch_webhook_configs 表

### 版本 3: 20251223_add_gitlab_token.py
**创建时间**: 2024-12-23
**功能**: 添加 GitLab Token 字段
- 在 webhook_mappings 表添加 gitlab_token 列
- 在 branch_webhook_configs 表添加 gitlab_token 列

---

## 🔧 实际操作示例

### 场景 1: 初始化数据库

```bash
cd /Users/hedawei/Projects/AI-Codereview-Gitlab

# 查看当前版本
alembic current

# 如果显示 "No current revision"，则需要升级
alembic upgrade head

# 验证
alembic current
# 应该显示: 20251223_add_gitlab_token (head)
```

### 场景 2: 查看迁移历史

```bash
alembic history --verbose
```

输出示例：
```
Rev: 20251223_add_gitlab_token (head)
Parent: 20251223_add_branch_webhooks
Path: alembic/versions/20251223_add_gitlab_token.py

    Add gitlab_token column

Rev: 20251223_add_branch_webhooks
Parent: 20251222_initial_schema
Path: alembic/versions/20251223_add_branch_webhooks.py

    Add branch webhook configs

Rev: 20251222_initial_schema
Parent: <base>
Path: alembic/versions/20251222_initial_schema.py

    Initial schema
```

### 场景 3: 添加新字段

假设您想给 `webhook_mappings` 表添加一个新字段 `priority`：

```bash
# 1. 修改 biz/utils/db.py 中的模型定义
# 添加: priority = Column(Integer, default=0)

# 2. 生成迁移脚本
alembic revision --autogenerate -m "add_priority_field"

# 3. 检查生成的迁移脚本
# 编辑 alembic/versions/新生成的文件.py

# 4. 应用迁移
alembic upgrade head
```

### 场景 4: 回滚到之前的版本

```bash
# 查看当前版本
alembic current

# 降级到上一个版本
alembic downgrade -1

# 或者指定版本
alembic downgrade 20251223_add_branch_webhooks

# 再次升级
alembic upgrade head
```

---

## ⚙️ Alembic 配置说明

### alembic.ini 配置

```ini
[alembic]
script_location = alembic  # 迁移脚本位置
```

### alembic/env.py 配置

这个文件定义了数据库连接方式。项目中通常从 `biz.utils.db` 获取数据库引擎。

---

## 🐛 常见问题

### Q1: 提示 "Can't locate revision identified by..."
**A**: 数据库版本与迁移文件不一致
```bash
# 解决方案1：重新初始化
alembic stamp head

# 解决方案2：降级到 base 再升级
alembic downgrade base
alembic upgrade head
```

### Q2: 提示 "Target database is not up to date"
**A**: 需要执行迁移
```bash
alembic upgrade head
```

### Q3: 提示 "FAILED: Multiple head revisions are present"
**A**: 有多个 head，需要合并
```bash
# 查看所有 head
alembic heads

# 合并 heads
alembic merge -m "merge_heads" [revision1] [revision2]
```

### Q4: 如何查看某个版本的详细信息？
```bash
alembic show 20251223_add_gitlab_token
```

### Q5: 如何删除一个迁移版本？
```bash
# 1. 先降级到该版本之前
alembic downgrade [previous_revision]

# 2. 删除迁移文件
rm alembic/versions/unwanted_revision.py

# 3. 重新升级
alembic upgrade head
```

---

## 📊 数据库表结构

### webhook_mappings (项目配置)
- id (主键)
- gitlab_base_url
- project_slug
- project_name
- url_slug
- dingtalk_url
- feishu_url
- wecom_url
- custom_prompt_system
- custom_prompt_user
- gitlab_token (新增)

### branch_webhook_configs (分支配置)
- id (主键)
- gitlab_base_url
- project_slug
- branch_pattern
- dingtalk_url
- feishu_url
- wecom_url
- custom_prompt_system
- custom_prompt_user
- gitlab_token (新增)

### mr_review_logs (MR 审查记录)
- id (主键)
- project_name
- author
- source_branch
- target_branch
- updated_at
- commit_messages
- score
- url
- additions
- deletions

### push_review_logs (Push 审查记录)
- id (主键)
- project_name
- author
- branch
- updated_at
- commit_messages
- score
- additions
- deletions

---

## 💡 最佳实践

1. **总是备份数据库**：在执行迁移前备份
   ```bash
   # SQLite 备份
   cp data/code_review.db data/code_review.db.backup
   ```

2. **先在开发环境测试**：确认迁移无误后再应用到生产

3. **保持迁移脚本简洁**：一个迁移文件只做一件事

4. **编写可逆的迁移**：确保 upgrade 和 downgrade 都能工作

5. **版本控制**：所有迁移文件都应该提交到 Git

6. **文档记录**：在迁移文件中写清楚变更原因

---

## 🔗 相关文档

- Alembic 官方文档：https://alembic.sqlalchemy.org/
- SQLAlchemy 文档：https://www.sqlalchemy.org/
- 项目数据库工具：`biz/utils/db.py`

---

## 📞 需要帮助？

如有问题，可以：
1. 查看 `alembic --help`
2. 查看具体命令帮助：`alembic upgrade --help`
3. 查看项目中的迁移文件源码
4. 联系开发团队

---

**祝您数据库迁移顺利！🎉**
