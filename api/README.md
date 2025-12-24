# AI Code Review API - FastAPI

FastAPI 后端服务，提供 RESTful API 接口。

## 技术栈
- FastAPI
- Pydantic v2
- Uvicorn
- 复用 `biz/` 业务逻辑层

## API 端点

### 认证
- `POST /api/v1/auth/login` - 用户登录

### 项目配置
- `GET /api/v1/webhooks` - 获取所有项目配置
- `POST /api/v1/webhooks` - 创建项目配置
- `PUT /api/v1/webhooks/{id}` - 更新项目配置
- `DELETE /api/v1/webhooks/{id}` - 删除项目配置

### 分支配置
- `GET /api/v1/branch-webhooks` - 获取所有分支配置
- `POST /api/v1/branch-webhooks` - 创建分支配置
- `PUT /api/v1/branch-webhooks/{id}` - 更新分支配置
- `DELETE /api/v1/branch-webhooks/{id}` - 删除分支配置

### 查询统计
- `GET /api/v1/reviews/mr` - 获取 MR 审查记录
- `GET /api/v1/reviews/push` - 获取 Push 审查记录
- `GET /api/v1/reviews/stats` - 获取统计数据

## 运行

```bash
# 开发模式
uvicorn api_new.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn api_new.main:app --host 0.0.0.0 --port 8000 --workers 4
