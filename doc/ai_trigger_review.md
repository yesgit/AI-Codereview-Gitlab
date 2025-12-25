# @AI 触发评审功能说明

## 版本说明

- **新增功能版本**: v1.4.3
- **功能**: 支持通过 @AI 评论主动触发代码评审

## 功能概述

通过在 commit 或 Merge Request 的评论中使用 `@AI` 主动触发代码评审。

## Webhook 配置

**重要**: 此功能复用现有的 Webhook 地址，无需新增配置！

- Webhook URL: `{your-api-url}/review/webhook`
- 需要订阅的事件类型：
  - ✅ Push events（已有）
  - ✅ Merge Request events（已有）
  - ✅ **Comment events**（新增，需要勾选）

注意：只需在现有 Webhook 中额外勾选 "Comment events" 即可。

## 使用方法

### 在 Commit 上触发评审

1. 进入 GitLab 项目
2. 打开任意一个 commit 页面
3. 在评论框中输入 `@AI` 或相关指令，例如：
   - `@AI`
   - `@AI 请帮我审查`
   - `@ai review`
   - `@Ai 帮忙检查一下`
4. 提交评论，AI 将自动评审该 commit 的代码变更

### 在 Merge Request 上触发评审

1. 进入 GitLab 项目
2. 打开任意一个 Merge Request 页面
3. 在评论框中输入 `@AI` 或相关指令
4. 提交评论，AI 将自动评审整个 MR 的代码变更

## 触发词格式

支持以下变体（大小写不敏感）：
- `@AI`
- `@ai`
- `@Ai`

## AI 评审结果格式

AI 的评审结果会自动添加到评论中，格式如下：

```
[Triggered by @AI comment by username on commit abc12345]

🤖 AI Code Review Result

评分：85/100

主要问题：
1. 问题1的描述
2. 问题2的描述

建议：
1. 建议的内容
2. 更多建议
```

## 防止死循环机制

为了避免 AI 评审结果再次触发评审（死循环），系统会自动识别并跳过包含以下标记的评论：
- `🤖 AI Code Review Result`
- `[Triggered by @AI`
- `[AI-REVIEW-RESULT]`

## 支持的场景

1. **Commit 评审**：评审单个 commit 的代码变更
2. **MR 评审**：评审整个 Merge Request 的所有代码变更

## 数据记录

评审结果会记录到现有的数据库表中：
- Commit 评审：记录到 `push_review_log` 表
- MR 评审：记录到 `mr_review_log` 表

在 `review_result` 字段中会包含 `[Triggered by @AI ...]` 标识，表明是通过 @AI 触发的评审。

## 注意事项

1. 确保项目已配置 Webhook
2. Webhook 需要订阅 "Comment events"
3. 只有包含支持的文件类型（.java, .py, .php 等）的变更才会被评审
4. 如果获取不到代码变更或变更不支持的文件类型，AI 会返回提示信息

## 错误处理

如果在评审过程中出现错误，系统会：
1. 在原评论位置返回错误信息
2. 记录详细的错误日志
3. 对于可重试的错误（如网络超时），会自动重试

## 示例

### 示例 1：简单的 commit 评审

```
@AI
```

### 示例 2：带指令的 commit 评审

```
@AI 请重点关注安全性问题
```

### 示例 3：MR 评审

```
@ai 帮我看看这个 MR 有什么问题
```

## 技术实现

- **触发词识别**：`biz/gitlab/ai_trigger_utils.py`
- **事件处理器**：`biz/gitlab/webhook_handler.py` 中的 `NoteHandler` 类
- **业务逻辑**：`biz/queue/worker.py` 中的 `handle_note_event` 函数
- **路由**：`api/routers/webhook_handler.py` 添加了 note 事件路由

## 测试

运行单元测试：

```bash
# 测试触发词识别
python -m pytest tests/test_ai_trigger_utils.py -v

# 测试 NoteHandler
python -m pytest tests/test_note_event_handler.py -v

# 运行所有测试
python -m pytest tests/ -v
