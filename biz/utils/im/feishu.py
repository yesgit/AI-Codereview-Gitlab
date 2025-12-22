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

    def _get_webhook_url(self, project_name=None, url_slug=None):
        """
        获取项目对应的 Webhook URL
        :param project_name: 项目名称
        :return: Webhook URL
        :raises ValueError: 如果未找到 Webhook URL
        """
<<<<<<< HEAD
        # 如果未提供 project_name，直接返回默认的 Webhook URL
        if not project_name:
            if self.default_webhook_url:
                return self.default_webhook_url
            else:
                raise ValueError("未提供项目名称，且未设置默认的 飞书 Webhook URL。")

        # 构造目标键
        target_key_project = f"FEISHU_WEBHOOK_URL_{project_name.upper()}"
        target_key_url_slug = f"FEISHU_WEBHOOK_URL_{url_slug.upper()}"

        # 遍历环境变量
        for env_key, env_value in os.environ.items():
            env_key_upper = env_key.upper()
            if env_key_upper == target_key_project:
                return env_value  # 找到项目名称对应的 Webhook URL，直接返回
            if env_key_upper == target_key_url_slug:
                return env_value  # 找到 GitLab URL 对应的 Webhook URL，直接返回

        # 如果未找到匹配的环境变量，降级使用全局的 Webhook URL
        if self.default_webhook_url:
            return self.default_webhook_url

        # 如果既未找到匹配项，也没有默认值，抛出异常
        raise ValueError(f"未找到项目 '{project_name}' 对应的 Feishu Webhook URL，且未设置默认的 Webhook URL。")
=======
        # 优先从数据库中读取项目级 webhook 配置
        try:
            mapping = WebhookService.get_webhook_mapping(project_name=project_name, url_slug=url_slug)
            if mapping and mapping.get('feishu_url'):
                return mapping.get('feishu_url')
        except Exception:
            pass

        # 如果未提供 project_name 且未提供 url_slug，直接返回默认的 Webhook URL（或抛错）
        if not project_name and not url_slug:
            if self.default_webhook_url:
                return self.default_webhook_url
            else:
                raise ValueError("未提供项目名称/slug，且未设置默认的 飞书 Webhook URL。")

        def normalize(s: str) -> str:
            if not s:
                return ''
            # 将字符串大写并把非字母数字字符替换为下划线
            return re.sub(r'[^A-Z0-9]+', '_', s.upper())

        norm_project = normalize(project_name)
        norm_slug = normalize(url_slug)

        # 支持的环境变量候选键顺序（优先级从高到低）
        candidates = []
        for key in (norm_project, norm_slug):
            if not key:
                continue
            candidates.extend([
                f"FEISHU_WEBHOOK_URL_{key}",
                f"FEISHU_WEBHOOK_{key}",
            ])

        # 最后再尝试全局配置（保留原有名称兼容）
        candidates.extend(["FEISHU_WEBHOOK_URL", "FEISHU_WEBHOOK_URL_DEFAULT", "FEISHU_WEBHOOK"])

        for cand in candidates:
            val = os.environ.get(cand)
            if val:
                return val

        # 如果都没有找到，抛出异常
        raise ValueError(f"未找到项目 '{project_name or url_slug}' 对应的 Feishu Webhook URL，且未设置默认的 Webhook URL。")
>>>>>>> c85976a (feat(通知): 支持每个项目独立通知 Hook；整理并扁平化测试目录)

    def send_message(self, content, msg_type='text', title=None, is_at_all=False, project_name=None, url_slug=None):
        """
        发送飞书消息
        :param content: 消息内容
        :param msg_type: 消息类型，支持text和markdown
        :param title: 消息标题(markdown类型时使用)
        :param is_at_all: 是否@所有人
        :param project_name: 项目名称
        """
        if not self.enabled:
            logger.info("飞书推送未启用")
            return

        try:
            post_url = self._get_webhook_url(project_name=project_name, url_slug=url_slug)
            if msg_type == 'markdown':
                data = {
                    "msg_type": "interactive",
                    "card": {
                        "schema": "2.0",
                        "config": {
                            "update_multi": True,
                            "style": {
                                "text_size": {
                                    "normal_v2": {
                                        "default": "normal",
                                        "pc": "normal",
                                        "mobile": "heading"
                                    }
                                }
                            }
                        },
                        "body": {
                            "direction": "vertical",
                            "padding": "12px 12px 12px 12px",
                            "elements": [
                                {
                                    "tag": "markdown",
                                    "content": content,
                                    "text_align": "left",
                                    "text_size": "normal_v2",
                                    "margin": "0px 0px 0px 0px"
                                }
                            ]
                        },
                        "header": {
                            "title": {
                                "tag": "plain_text",
                                "content": title
                            },
                            "template": "blue",
                            "padding": "12px 12px 12px 12px"
                        }
                    }
                }
            else:
                data = {
                    "msg_type": "text",
                    "content": {
                        "text": content
                    },
                }

            response = requests.post(
                url=post_url,
                json=data,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code != 200:
<<<<<<< HEAD
                logger.error(f"飞书消息发送失败! webhook_url:{post_url}, error_msg:{response.text}")
=======
                logger.error(f"飞书消息发送失败! webhook_url:{self._mask_url(post_url)}, error_msg:{response.text}")
>>>>>>> c85976a (feat(通知): 支持每个项目独立通知 Hook；整理并扁平化测试目录)
                return

            result = response.json()
            if result.get('msg') != "success":
<<<<<<< HEAD
                logger.error(f"发送飞书消息失败! webhook_url:{post_url},errmsg:{result}")
            else:
                logger.info(f"飞书消息发送成功! webhook_url:{post_url}")

        except Exception as e:
            logger.error(f"飞书消息发送失败! ", e)
=======
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
                # build querystring preserving literal stars (avoid urlencode turning '*' into '%2A')
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
>>>>>>> c85976a (feat(通知): 支持每个项目独立通知 Hook；整理并扁平化测试目录)
