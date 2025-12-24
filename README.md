# AI Code Review for GitLab

AI 代码审查平台，支持 GitLab、GitHub、Gitea，通过 Webhook 自动审查代码。

## 功能特性

- 🤖 **AI 驱动代码审查**：支持多种 LLM（OpenAI、DeepSeek、Qwen 等）
- 🎯 **多种触发场景**：MR/Push 代码提交、定时每日报告
- 📊 **可视化 Dashboard**：查看审查记录、统计数据
- ⚙️ **灵活配置**：支持项目和分支级别的自定义配置
- 🔔 **多渠道通知**：钉钉、飞书、企业微信、自定义 Webhook
- 🎨 **现代化 UI**：使用 Ant Design 组件库，Modal 弹窗表单
- 🔐 **用户认证**：基于 JWT 的安全认证系统

## 技术栈

### 后端
- **FastAPI** - 高性能 Python Web 框架
- **Pydantic v2** - 数据验证
- **SQLAlchemy** - ORM

### 前端
- **React 18** + TypeScript
- **Vite** - 快速构建工具
- **Ant Design** - 企业级 UI 组件库

### 原有组件
- `biz/` - 业务逻辑层
- `conf/` - 配置文件
- 数据库和 LLM 集成

## 快速开始

### 使用 Docker Compose

```bash
# 1. 复制环境变量配置
cp conf/.env.dist .env

# 2. 根据需要修改 .env 文件
# vi .env

# 3. 启动服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f

# 5. 停止服务
docker-compose down
```

服务启动后访问：
- Dashboard: http://localhost:8080
- API 文档: http://localhost:8000/docs

### 本地开发

**后端:**
```bash
# 安装依赖
pip install -r requirements.txt

# 启动后端
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**前端:**
```bash
cd frontend

# 安装依赖
npm install

# 启动前端
npm run dev
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DASHBOARD_USER` | Dashboard 登录用户名 | `admin` |
| `DASHBOARD_PASSWORD` | Dashboard 登录密码 | `admin` |
| `DASHBOARD_SECRET_KEY` | Token 签名密钥 | 自动生成 |
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `ANTHROPIC_API_KEY` | Anthropic API Key | - |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | - |
| `QWEN_API_KEY` | 通义千问 API Key | - |
| `ZHIPUAI_API_KEY` | 智谱 AI API Key | - |
| `OLLAMA_API_BASE_URL` | Ollama API 地址 | `http://host.docker.internal:11434` |
| `OLLAMA_API_MODEL` | Ollama 模型名称 | `deepseek-r1:latest` |
| `DEFAULT_LLM_PROVIDER` | 默认 LLM 提供商 | `deepseek` |
| `DB_DRIVER` | 数据库类型 (sqlite/mysql) | `sqlite` |

### 数据库配置

**SQLite (默认):**
```bash
DB_DRIVER=sqlite
DB_FILE=data/data.db
```

**MySQL:**
```bash
DB_DRIVER=mysql
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=ai_codereview
```

## Webhook 配置

### GitLab

在项目设置中添加 Webhook：

1. 进入 `Settings` > `Webhooks`
2. 填写 URL: `http://your-domain/api/v1/webhooks/gitlab`
3. 选择触发事件：`Merge request events`
4. 添加 Token（可选，用于验证）
5. 点击保存

### GitHub

在项目设置中添加 Webhook：

1. 进入 `Settings` > `Webhooks` > `Add webhook`
2. Payload URL: `http://your-domain/api/v1/webhooks/github`
3. Content type: `application/json`
4. 选择触发事件：`Pull requests`
5. 点击保存

### Gitea

在项目设置中添加 Webhook：

1. 进入 `Settings` > `Webhooks` > `Add webhook`
2. Target URL: `http://your-domain/api/v1/webhooks/gitea`
3. 选择触发事件：`Pull Request`
4. 点击保存

## LLM 配置

### OpenAI
```bash
OPENAI_API_KEY=sk-xxx
OPENAI_API_BASE_URL=https://api.openai.com/v1
OPENAI_API_MODEL=gpt-4o-mini
DEFAULT_LLM_PROVIDER=openai
```

### DeepSeek
```bash
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_API_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_MODEL=deepseek-chat
DEFAULT_LLM_PROVIDER=deepseek
```

### 通义千问
```bash
QWEN_API_KEY=sk-xxx
QWEN_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_API_MODEL=qwen-coder-plus
DEFAULT_LLM_PROVIDER=qwen
```

### Ollama
```bash
OLLAMA_API_BASE_URL=http://host.docker.internal:11434
OLLAMA_API_MODEL=deepseek-r1:latest
DEFAULT_LLM_PROVIDER=ollama
```

### Anthropic Claude
```bash
ANTHROPIC_API_KEY=sk-xxx
ANTHROPIC_API_BASE_URL=https://api.anthropic.com
ANTHROPIC_API_MODEL=claude-sonnet-4-5-20250929
DEFAULT_LLM_PROVIDER=anthropic
```

## API 端点

### 认证
- `POST /api/v1/auth/login` - 用户登录
- `GET /api/v1/auth/me` - 获取当前用户

### 项目配置
- `GET /api/v1/webhooks` - 获取所有配置
- `POST /api/v1/webhooks` - 创建配置
- `PUT /api/v1/webhooks/{id}` - 更新配置
- `DELETE /api/v1/webhooks/{id}` - 删除配置

### 分支配置
- `GET /api/v1/branch-webhooks` - 获取所有配置
- `POST /api/v1/branch-webhooks` - 创建配置
- `PUT /api/v1/branch-webhooks/{id}` - 更新配置
- `DELETE /api/v1/branch-webhooks/{id}` - 删除配置

### 查询统计
- `GET /api/v1/reviews/mr` - MR 审查记录
- `GET /api/v1/reviews/push` - Push 审查记录
- `GET /api/v1/reviews/stats` - 统计数据

### Webhook 接收
- `POST /api/v1/webhooks/gitlab` - GitLab Webhook
- `POST /api/v1/webhooks/github` - GitHub Webhook
- `POST /api/v1/webhooks/gitea` - Gitea Webhook

## 项目结构

```
.
├── api/                 # FastAPI 后端
│   ├── main.py         # 主入口
│   └── routers/        # 路由模块
│       ├── auth.py      # 认证
│       ├── webhooks.py  # 项目配置
│       ├── branch_webhooks.py  # 分支配置
│       └── reviews.py   # 查询统计
├── frontend/           # React 前端
│   ├── src/
│   │   ├── pages/      # 页面组件
│   │   ├── components/ # 公共组件
│   │   ├── api/        # API 调用
│   │   ├── types/      # 类型定义
│   │   └── utils/      # 工具函数
│   ├── Dockerfile
│   └── nginx.conf
├── biz/               # 业务逻辑
│   ├── llm/          # LLM 客户端
│   ├── service/      # 服务层
│   ├── platforms/    # 平台适配
│   └── utils/       # 工具函数
├── alembic/         # 数据库迁移
├── conf/            # 配置文件
│   ├── .env.dist   # 环境变量模板
│   ├── prompt_templates.yml
│   └── supervisord.conf
└── docker-compose.yml
```

## UI 改进

### Modal 弹窗表单

新版本使用 Ant Design Modal 组件，确保新建/编辑表单正常弹出：

| 特性 | Streamlit 版本 | 新版本 |
|--------|----------------|--------|
| 表单弹出 | ❌ 在页面展开 | ✅ Modal 弹窗 |
| 现代化 UI | ❌ Streamlit 风格 | ✅ Ant Design |
| 前后端分离 | ❌ 一体化 | ✅ 分离架构 |
| 开发体验 | ❌ 重载慢 | ✅ HMR 快速 |
| 类型安全 | ❌ 无类型检查 | ✅ TypeScript |

## Dashboard 功能

### 1. 认证系统
- 基于 JWT 的用户认证
- Token 有效期管理（30天）
- 安全的密码存储和验证

### 2. 项目配置管理
- 支持通过 GitLab URL + Slug 配置项目
- 支持传统方式（project_name、url_slug）
- 钉钉、飞书、企业微信 Webhook 配置
- 自定义 Prompt 配置
- GitLab Token 配置

### 3. 分支配置管理
- 按分支模式配置通知（如 `feature/*`）
- 支持通配符匹配（`*` 和 `?`）
- 完整的 Webhook 和 Prompt 配置

### 4. 查询统计
- MR 和 Push 审查记录查询
- 按作者、项目、时间筛选
- 统计分析图表
- 代码行数统计

## Docker 部署

### 构建镜像

```bash
# 构建后端
docker build -t ai-codereview-api .

# 构建前端
cd frontend && docker build -t ai-codereview-frontend .
```

### 使用 Docker Compose

```bash
# 后台启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止
docker-compose down

# 重新构建并启动
docker-compose up -d --build
```

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
