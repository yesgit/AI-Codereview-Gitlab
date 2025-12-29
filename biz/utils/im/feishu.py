import requests
import os
import re
import urllib.parse
from biz.utils.log import logger
from biz.service.webhook_service import WebhookService


class FeishuNotifier:
    def __init__(self, config=None):
        """
        初始化飞书通知器
        :param config: 飞书机器人webhook地址或配置字典
        """
        self.default_webhook_url = ''
        self.enabled = os.environ.get('FEISHU_ENABLED', '0') == '1'
        self.config = config or {}
        
        # 支持传入 webhook_url 或 config 字典
        if isinstance(config, str):
            self.default_webhook_url = config
        elif config and isinstance(config, dict):
            self.default_webhook_url = config.get('feishu_webhook') or config.get('feishu_url', '')
        else:
            self.default_webhook_url = os.environ.get('FEISHU_WEBHOOK_URL', '')

    def _get_webhook_url(self, gitlab_base_url=None, project_slug=None, branch_name=None,
                        project_name=None, url_slug=None):
        """
        获取飞书webhook URL，支持三级回退
        
        Args:
            gitlab_base_url: GitLab实例地址
            project_slug: 项目slug
            branch_name: 分支名称
            project_name: 项目名称（兼容旧方式）
            url_slug: URL slug（兼容旧方式）
        """
        try:
            # 优先使用构造函数传入的配置
            if self.config and self.config.get('feishu_enabled') is not None:
                if not self.config.get('feishu_enabled'):
                    logger.info("飞书通知已禁用（配置级别）")
                    return None
                if self.config.get('feishu_webhook') or self.config.get('feishu_url'):
                    return self.config.get('feishu_webhook') or self.config.get('feishu_url')
            
            # 使用统一的配置获取方法，支持三级回退
            config = WebhookService.get_webhook_config_with_fallback(
                gitlab_base_url=gitlab_base_url,
                project_slug=project_slug,
                branch_name=branch_name,
                project_name=project_name,
                url_slug=url_slug
            )
            
            # 检查是否启用飞书通知
            if config and config.get('feishu_enabled') is not None:
                if not config.get('feishu_enabled'):
                    logger.info("飞书通知已禁用（配置级别）")
                    return None
            
            # 从配置中获取飞书URL
            if config and config.get('feishu_url'):
                return config.get('feishu_url')
        except Exception as e:
            logger.debug(f"获取配置失败: {e}")

        # 兼容旧的环境变量查找逻辑（用于向后兼容）
        if not gitlab_base_url and not project_slug and (project_name or url_slug):
            def normalize(s: str) -> str:
                if not s:
                    return ''
                return re.sub(r'[^A-Z0-9]+', '_', s.upper())

            norm_project = normalize(project_name)
            norm_slug = normalize(url_slug)

            candidates = []
            for key in (norm_project, norm_slug):
                if not key:
                    continue
                candidates.extend([
                    f"FEISHU_WEBHOOK_URL_{key}",
                    f"FEISHU_WEBHOOK_{key}",
                ])
            candidates.extend(["FEISHU_WEBHOOK_URL", "FEISHU_WEBHOOK_URL_DEFAULT", "FEISHU_WEBHOOK"])

            for cand in candidates:
                val = os.environ.get(cand)
                if val:
                    return val

        # 最终回退：使用默认URL
        if self.default_webhook_url:
            return self.default_webhook_url

        raise ValueError("未找到飞书 Webhook URL，请检查配置。")

    def send_message(self, content, msg_type='text', title=None, is_at_all=False,
                     gitlab_base_url=None, project_slug=None, branch_name=None,
                     project_name=None, url_slug=None):
        """
        发送飞书消息
        
        Args:
            content: 消息内容
            msg_type: 消息类型，支持text和markdown
            title: 消息标题(markdown类型时使用)
            is_at_all: 是否@所有人
            gitlab_base_url: GitLab实例地址
            project_slug: 项目slug
            branch_name: 分支名称
            project_name: 项目名称（兼容旧方式）
            url_slug: URL slug（兼容旧方式）
        """
        try:
            post_url = self._get_webhook_url(
                gitlab_base_url=gitlab_base_url,
                project_slug=project_slug,
                branch_name=branch_name,
                project_name=project_name,
                url_slug=url_slug
            )
            
            # 如果 webhook URL 为 None（已禁用），直接返回
            if post_url is None:
                return

            if msg_type == 'markdown':
                # 构建结构化的飞书卡片，避免 Markdown 解析问题
                data = {
                    "msg_type": "interactive",
                    "card": {
                        "schema": "2.0",
                        "config": {
                            "wide_screen_mode": True,
                        },
                        "header": {
                            "title": {
                                "tag": "plain_text",
                                "content": title or "AI Code Review"
                            },
                            "template": "blue",
                        },
                        "body": {
                            "elements": self._build_card_elements(content)
                        }
                    }
                }
            else:
                data = {
                    "msg_type": "text",
                    "content": {"text": content},
                }

            response = requests.post(
                url=post_url,
                json=data,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code != 200:
                logger.error(f"飞书消息发送失败! webhook_url:{self._mask_url(post_url)}, error_msg:{response.text}")
                return

            result = response.json()
            if result.get('msg') != "success":
                logger.error(f"发送飞书消息失败! webhook_url:{self._mask_url(post_url)},errmsg:{result}")
            else:
                logger.info(f"飞书消息发送成功! webhook_url:{self._mask_url(post_url)}")

        except Exception as e:
            logger.error(f"飞书消息发送失败! {e}")

    def _build_card_elements(self, content):
        """
        将 Markdown 内容转换为飞书卡片元素列表
        
        Args:
            content: Markdown 格式的消息内容
        
        Returns:
            飞书卡片元素列表
        """
        elements = []
        
        # 按段落分割内容
        paragraphs = self._split_content_paragraphs(content)
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # 添加分割线（分隔不同部分）
            if elements and self._should_add_separator(paragraph):
                elements.append({"tag": "hr"})
            
            # 根据段落内容决定使用什么格式
            element = self._create_element_from_paragraph(paragraph)
            if element:
                elements.append(element)
        
        return elements
    
    def _split_content_paragraphs(self, content):
        """
        将内容按段落分割
        保留 AI Review 结果作为一个整体
        """
        paragraphs = []
        current_lines = []
        
        for line in content.split('\n'):
            stripped = line.strip()
            
            # AI Review 结果标记
            if 'AI Review 结果' in stripped or 'Review 结果' in stripped:
                # 保存之前的内容
                if current_lines:
                    paragraphs.append('\n'.join(current_lines))
                    current_lines = []
                # 添加当前标记行
                current_lines.append(line)
                continue
            
            # 代码块开始
            if line.strip().startswith('```'):
                current_lines.append(line)
                continue
            
            current_lines.append(line)
        
        # 添加剩余内容
        if current_lines:
            paragraphs.append('\n'.join(current_lines))
        
        return paragraphs
    
    def _should_add_separator(self, paragraph):
        """
        判断是否需要在当前段落前添加分割线
        """
        # 主标题（### 开头）或副标题（#### 开头）前添加分割线
        if paragraph.startswith('### ') or paragraph.startswith('#### '):
            return True
        # 包含特定标记的段落前添加分割线
        if any(marker in paragraph for marker in ['AI Review 结果', 'Review 结果', '提交记录', '合并请求信息']):
            return True
        return False
    
    def _create_element_from_paragraph(self, paragraph):
        """
        根据段落内容创建飞书卡片元素
        
        所有内容统一使用 lark_md 格式，确保 markdown 语法能正确渲染
        """
        # 所有内容都使用 lark_md 格式，确保 markdown 语法能正确渲染
        return {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": paragraph
            }
        }
    
    def _has_markdown_syntax(self, text):
        """
        检查文本是否包含 Markdown 特殊语法
        如果包含表格、代码块、链接等，返回 True
        """
        # 检查表格
        if re.search(r'\|.*\|', text):
            return True
        
        # 检查代码块
        if re.search(r'```[\s\S]*?```', text):
            return True
        
        # 检查 Markdown 链接 [text](url)
        if re.search(r'\[.*?\]\(.*?\)', text):
            return True
        
        # 检查加粗 **text**
        if re.search(r'\*\*.*?\*\*', text):
            return True
        
        # 检查标题 # ## ### 等
        if re.match(r'^#+\s', text, re.MULTILINE):
            return True
        
        # 检查列表项 - 或 *
        if re.search(r'^[\-\*]\s', text, re.MULTILINE):
            return True
        
        return False

    @staticmethod
    def _mask_url(u: str) -> str:
        """掩码 webhook URL，隐藏 query 参数或最后的 path token。"""
        if not u:
            return u
        try:
            p = urllib.parse.urlparse(u)
            qs = urllib.parse.parse_qsl(p.query, keep_blank_values=True)
            if qs:
                masked_items = [f"{k}=***" for k, _ in qs]
                new_query = '&'.join(masked_items)
                return urllib.parse.urlunparse((p.scheme, p.netloc, p.path, p.params, new_query, p.fragment))
            parts = p.path.rstrip('/').split('/')
            if parts and len(parts[-1]) > 3:
                parts[-1] = '***'
                new_path = '/'.join(parts)
                return urllib.parse.urlunparse((p.scheme, p.netloc, new_path, p.params, p.query, p.fragment))
            return u
        except Exception:
            return '***'
