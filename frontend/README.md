# AI Code Review Frontend

基于 Vite + React + TypeScript + Ant Design 的前端应用。

## 技术栈

- React 18.3
- TypeScript
- Vite
- Ant Design 5
- React Router 6
- Axios

## 项目结构

```
frontend/
├── src/
│   ├── api/           # API 调用模块
│   ├── components/     # 组件
│   ├── pages/         # 页面组件
│   ├── types/         # TypeScript 类型定义
│   ├── utils/         # 工具函数
│   ├── App.tsx        # 根组件
│   ├── main.tsx       # 入口文件
│   └── index.css      # 全局样式
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── Dockerfile
└── nginx.conf
```

## 开发

```bash
# 安装依赖
cd frontend
npm install

# 启动开发服务器（端口 3000）
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## 页面说明

| 路由 | 说明 |
|--------|------|
| `/login` | 登录页面 |
| `/reviews` | 查询审查记录 |
| `/stats` | 统计分析 |
| `/webhooks` | 项目配置 |
| `/branch-webhooks` | 分支配置 |

## 默认登录凭据

- 用户名: `admin`
- 密码: `admin`

可通过环境变量 `DASHBOARD_USER` 和 `DASHBOARD_PASSWORD` 配置。
