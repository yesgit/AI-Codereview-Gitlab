![Push图片](doc/img/open/ai-codereview-cartoon.png)

## 项目简介

本项目是一个基于大模型的自动化代码审查工具，帮助开发团队在代码合并或提交时，快速进行智能化的审查(Code Review)，提升代码质量和开发效率。

## 功能

- 🚀 多模型支持
  - 兼容 DeepSeek、ZhipuAI、OpenAI、Anthropic、通义千问 和 Ollama，想用哪个就用哪个。
- 📢 消息即时推送
  - 审查结果一键直达 钉钉、企业微信 或 飞书，代码问题无处可藏！
- 📅 自动化日报生成
  - 基于 GitLab & GitHub & Gitea Commit 记录，自动整理每日开发进展，谁在摸鱼、谁在卷，一目了然 😼。
- 📊 可视化 Dashboard
  - 集中展示所有 Code Review 记录，项目统计、开发者统计，数据说话，甩锅无门！
  - � **新增 Reflex 现代化界面**：Material Design 风格，响应式设计，更美观更流畅！
- �🎭 Review Style 任你选
  - 专业型 🤵：严谨细致，正式专业。 
  - 讽刺型 😈：毒舌吐槽，专治不服（"这代码是用脚写的吗？"） 
  - 绅士型 🌸：温柔建议，如沐春风（"或许这里可以再优化一下呢~"） 
  - 幽默型 🤪：搞笑点评，快乐改码（"这段 if-else 比我的相亲经历还曲折！"）

**效果图:**

![MR图片](doc/img/open/mr.png)

![Note图片](doc/img/open/note.jpg)

![Dashboard图片](doc/img/open/dashboard.jpg)

## 原理

当用户在 GitLab 上提交代码（如 Merge Request 或 Push 操作）时，GitLab 将自动触发 webhook
事件，调用本系统的接口。系统随后通过第三方大模型对代码进行审查，并将审查结果直接反馈到对应的 Merge Request 或 Commit 的
Note 中，便于团队查看和处理。

![流程图](doc/img/open/process.png)

## 部署

### 方案一：Docker 部署

**1. 准备环境文件**

- 克隆项目仓库：
```aiignore
git clone https://github.com/sunmh207/AI-Codereview-Gitlab.git
cd AI-Codereview-Gitlab
```

- 创建配置文件：
```aiignore
cp conf/.env.dist conf/.env
```

- 编辑 conf/.env 文件，配置以下关键参数：

```bash
#大模型供应商配置,支持 zhipuai , openai , deepseek 和 ollama
LLM_PROVIDER=deepseek

#DeepSeek
DEEPSEEK_API_KEY={YOUR_DEEPSEEK_API_KEY}

#支持review的文件类型(未配置的文件类型不会被审查)
SUPPORTED_EXTENSIONS=.java,.py,.php,.yml,.vue,.go,.c,.cpp,.h,.js,.css,.md,.sql

#钉钉消息推送: 0不发送钉钉消息,1发送钉钉消息
DINGTALK_ENABLED=0
DINGTALK_WEBHOOK_URL={YOUR_WDINGTALK_WEBHOOK_URL}

#Gitlab配置
GITLAB_ACCESS_TOKEN={YOUR_GITLAB_ACCESS_TOKEN}
```

**2. 启动服务**

```bash
docker-compose up -d
```

**3. 验证部署**

- 主服务验证：
  - 访问 http://your-server-ip:5001
  - 显示 "The code review server is running." 说明服务启动成功。
- Dashboard 验证：
  - 访问 http://your-server-ip:5002
  - 看到一个审查日志页面，说明 Dashboard 启动成功。

### 方案二：本地Python环境部署

**1. 获取源码**

```bash
git clone https://github.com/sunmh207/AI-Codereview-Gitlab.git
cd AI-Codereview-Gitlab
```

**2. 安装依赖**

使用 Python 环境（建议使用虚拟环境 venv）安装项目依赖(Python 版本：3.10+):

```bash
pip install -r requirements.txt
```

**3. 配置环境变量**

同 Docker 部署方案中的.env 文件配置。

**4. 启动服务**

- 启动API服务：

```bash
python api.py
```

- 启动Dashboard服务：

```bash
streamlit run ui.py --server.port=5002 --server.address=0.0.0.0
```

### 配置 GitLab Webhook

#### 1. 创建Access Token

方法一：在 GitLab 个人设置中，创建一个 Personal Access Token。

方法二：在 GitLab 项目设置中，创建Project Access Token

#### 2. 配置 Webhook

在 GitLab 项目设置中，配置 Webhook：

- URL：http://your-server-ip:5001/review/webhook
- Trigger Events：勾选 Push Events 和 Merge Request Events (不要勾选其它Event)
- Secret Token：上面配置的 Access Token(可选)

**备注**

1. Token使用优先级
  - 系统优先使用 .env 文件中的 GITLAB_ACCESS_TOKEN。
  - 如果 .env 文件中没有配置 GITLAB_ACCESS_TOKEN，则使用 Webhook 传递的Secret Token。
2. 网络访问要求
  - 请确保 GitLab 能够访问本系统。
  - 若内网环境受限，建议将系统部署在外网服务器上。

### 配置 Gitea Webhook

#### 1. 创建 Access Token
- 在 Gitea 个人设置中创建 Access Token，并确保具备 `repo` 权限。

#### 2. 配置 Webhook
- 打开仓库 `Settings -> Webhooks -> Add Webhook`
- URL：`http://your-server-ip:5001/review/webhook`
- Header：`X-Gitea-Token` 设置为 `.env` 中的 `GITEA_ACCESS_TOKEN`（可选）
- 触发事件：勾选 `Push events` 与 `Pull Request events`
- Content Type：`application/json`

### 配置消息推送

#### 1.配置钉钉推送

- 在钉钉群中添加一个自定义机器人，获取 Webhook URL。
- 更新 .env 中的配置：
  ```
  #钉钉配置
  DINGTALK_ENABLED=1  #0不发送钉钉消息，1发送钉钉消息
  DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx #替换为你的Webhook URL
  ```

企业微信和飞书推送配置类似，具体参见 [常见问题](doc/faq.md)

### 按项目配置独立通知 Hook

如果你希望不同项目将消息推送到不同的群（或不同的机器人），可以为每个项目单独配置通知 Hook。系统选择 webhook 的优先级如下：

1. 按仓库/项目名匹配的专用 Hook（优先级最高，建议使用仓库的 slug 或短名称）
2. 按 Git 服务器（域名）匹配的 Hook
3. 全局默认 Hook（`.env` 中的默认 `*_WEBHOOK_URL`）

命名约定示例（以钉钉为例）：

```
DINGTALK_ENABLED=1
# 默认（fallback）Webhook
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=DEFAULT_TOKEN

# 针对仓库名为 `my-repo` 的项目（仓库名小写，下划线替代特殊字符）
DINGTALK_WEBHOOK_my_repo=https://oapi.dingtalk.com/robot/send?access_token=TOKEN_FOR_MY_REPO

# 针对 GitLab 服务 host 为 example.gitlab.com（点替换为下划线）
DINGTALK_WEBHOOK_example_gitlab_com=https://oapi.dingtalk.com/robot/send?access_token=TOKEN_FOR_HOST
```

飞书和企业微信同理：把前缀改为 `FEISHU_` 或 `WECOM_`，并使用同样的命名规则（仓库名优先，主机名其次，最后使用默认 URL）。

注意事项：
- 环境变量名的匹配通常为小写仓库名或 host，将点（`.`）替换为下划线（`_`），并去掉或替换特殊字符以保证环境变量合法。
- 修改 `.env` 后需要重启服务（Docker 容器或本地进程）以使配置生效。
- 在本地验证：可以用一个真实的 Push / Merge Request 触发一次 webhook，或者使用单元测试和模拟请求来校验通知逻辑。

#### 通过管理界面配置（推荐）

为了方便运维和非技术人员管理，每个项目的通知 Hook 也可以通过系统的管理后台（Dashboard / 管理界面）进行配置：

- 访问 Dashboard 管理地址（示例：`http://your-server-ip:5002`），并使用管理员账号登录。
- 在管理界面中打开 **项目管理 / 通知设置 / Webhook 管理**（不同版本界面位置可能略有差异），选择或搜索到目标项目。
- 点击 **新增/编辑 通知 Hook**，填写必要信息：
  - 平台：钉钉、飞书、企业微信或自定义 webhook
  - 名称（可选）：便于识别该 Hook 的用途
  - Webhook URL：机器人或通知接收地址
  - 启用开关：开启或禁用该 Hook
  - 可选：设置匹配规则（按仓库名或 Git 主机匹配）或优先级
- 保存后配置通常会立即生效；若未生效，可重启服务或清理缓存后重试。

优势：
- 更直观：非开发人员可以直接在后台管理通知目标，无需改 `.env` 或重启服务。
- 更灵活：可以为同一 Git 主机或不同仓库快速配置多套 Hook，并随时启停。

优先级说明：管理界面中设置的项目级 Hook 优先于环境变量中的同类配置（即：UI > 仓库名匹配 > 主机匹配 > 全局默认）。如果你同时使用 UI 和 `.env`，建议将稳定的生产配置放在 UI 中管理。


## 🎨 Reflex 现代化界面（新增）

我们为平台开发了**全新的 Reflex 现代化界面**，提供更优雅的用户体验！

### 特性

- ✨ Material Design 风格设计
- 🚀 响应式布局，完美适配移动端
- 🎨 渐变色彩和流畅动画
- ⚡ 更快的响应速度（React 渲染）
- 💡 直观的用户操作体验

### 快速开始

**1. 安装依赖**

```bash
pip install -r requirements.txt
```

**2. 初始化 Reflex**

```bash
reflex init
```

**3. 启动 Reflex 界面**

```bash
# 方式一：使用 reflex 命令（推荐）
reflex run

# 方式二：使用启动脚本
python run_reflex.py
```

**4. 访问界面**

打开浏览器访问：**http://localhost:3000**

默认登录账号：`admin` / `admin`

### 界面对比

| 版本 | 端口 | 技术栈 | 启动命令 |
|------|------|--------|----------|
| Streamlit 版本 | 5002 | Streamlit | `streamlit run ui.py` |
| Reflex 版本 (新) | 3000 | Reflex + React | `reflex run` |

两个版本可以**同时运行**，互不干扰！

### 详细文档

查看完整使用指南：[Reflex UI 使用指南](doc/reflex_ui_guide.md)

---

## 其它

### 运行单元测试

- 在项目根目录，激活虚拟环境后运行：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

- 如果只想运行单个测试文件或用例，例如运行飞书掩码测试：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_notifier_masking.py::test_mask_querystring -q
```

- 说明：本项目在本地可能会被安装的第三方 pytest 插件影响（例如某些插件在导入时会触发对外部包的导入），出现类似 "ImportError: cannot import name 'OpenAI'" 之类的问题时，请使用 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 来禁止自动加载 pytest 插件，或在干净的虚拟环境中运行测试。

- 我在本地运行测试得到的结果：`8 passed in 1.00s`（运行时间会因机器差异略有不同）。

- 分支说明：当前本地开发分支为 `develop`（本地历史已合并为单提交），如果需要推送到远程请先确认远程策略，必要时可使用强制推送（`git push --force`）。


**1.如何对整个代码库进行Review?**

可以通过命令行工具对整个代码库进行审查。当前功能仍在不断完善中，欢迎试用并反馈宝贵意见！具体操作如下：

```bash
python -m biz.cmd.review
```

运行后，请按照命令行中的提示进行操作即可。

**2.其它问题**

参见 [常见问题](doc/faq.md)

## 交流

若本项目对您有帮助，欢迎 Star ⭐️ 或 Fork。 有任何问题或建议，欢迎提交 Issue 或 PR。

也欢迎加微信/微信群，一起交流学习。

<p float="left">
  <img src="doc/img/open/wechat.jpg" width="400" />
  <img src="doc/img/open/wechat_group.jpg" width="400" /> 
</p>

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=sunmh207/AI-Codereview-Gitlab&type=Timeline)](https://www.star-history.com/#sunmh207/AI-Codereview-Gitlab&Timeline)
