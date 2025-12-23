import requests
import os
import re
import urllib.parse
from biz.utils.log import logger
from biz.service.webhook_service import WebhookService


class FeishuNotifier:
    def __init__(self, webhook_url=None):
        """
        初始化飞书通知器
        :param webhook_url: 飞书机器人webhook地址
        """
        self.default_webhook_url = webhook_url or os.environ.get('FEISHU_WEBHOOK_URL', '')
        self.enabled = os.environ.get('FEISHU_ENABLED', '0') == '1'

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
            # 使用统一的配置获取方法，支持三级回退
            config = WebhookService.get_webhook_config_with_fallback(
                gitlab_base_url=gitlab_base_url,
                project_slug=project_slug,
                branch_name=branch_name,
                project_name=project_name,
                url_slug=url_slug
            )
            
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
        if not self.enabled:
            logger.info("飞书推送未启用")
            return

        try:
            post_url = self._get_webhook_url(
                gitlab_base_url=gitlab_base_url,
                project_slug=project_slug,
                branch_name=branch_name,
                project_name=project_name,
                url_slug=url_slug
            )
            if msg_type == 'markdown':
                data = {
                    "msg_type": "interactive",
                    "card": {
                        "schema": "2.0",
                        "config": {
                            "update_multi": True,
                        },
                        "body": {
                            "direction": "vertical",
                            "padding": "12px 12px 12px 12px",
                            "elements": [
                                {
                                    "tag": "markdown",
                                    "content": content,
                                }
                            ]
                        },
                        "header": {
                            "title": {
                                "tag": "plain_text",
                                "content": title
                            },
                            "template": "blue",
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
