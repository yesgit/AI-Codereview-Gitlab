import base64
import hashlib
import hmac
import json
import os
import re
import time
import urllib.parse

import requests

from biz.utils.log import logger
from biz.service.webhook_service import WebhookService


class DingTalkNotifier:
    def __init__(self, webhook_url=None):
        self.enabled = os.environ.get('DINGTALK_ENABLED', '0') == '1'
        self.default_webhook_url = webhook_url or os.environ.get('DINGTALK_WEBHOOK_URL')

    def _get_webhook_url(self, project_name=None, url_slug=None):
        """
        获取项目对应的 Webhook URL
        :param project_name: 项目名称
        :param url_slug: 由 gitlab 项目的 url 转换而来的 slug
        :return: Webhook URL
        :raises ValueError: 如果未找到 Webhook URL
        """
<<<<<<< HEAD
        # 如果未提供 project_name，直接返回默认的 Webhook URL
        if not project_name:
            if self.default_webhook_url:
                return self.default_webhook_url
            else:
                raise ValueError("未提供项目名称，且未设置默认的钉钉 Webhook URL。")

        # 构造目标键
        target_key_project = f"DINGTALK_WEBHOOK_URL_{project_name.upper()}"
        target_key_url_slug = f"DINGTALK_WEBHOOK_URL_{url_slug.upper()}"

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
        raise ValueError(f"未找到项目 '{project_name}' 对应的钉钉Webhook URL，且未设置默认的 Webhook URL。")
=======
        # 优先从数据库中读取项目级 webhook 配置
        try:
            mapping = WebhookService.get_webhook_mapping(project_name=project_name, url_slug=url_slug)
            if mapping and mapping.get('dingtalk_url'):
                return mapping.get('dingtalk_url')
        except Exception:
            # 不要因为 DB 查询失败影响后续回退逻辑
            pass

        # 如果未提供 project_name 且未提供 url_slug，直接返回默认的 Webhook URL（或抛错）
        if not project_name and not url_slug:
            if self.default_webhook_url:
                return self.default_webhook_url
            else:
                raise ValueError("未提供项目名称/slug，且未设置默认的 钉钉 Webhook URL。")

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
                f"DINGTALK_WEBHOOK_URL_{key}",
                f"DINGTALK_WEBHOOK_{key}",
            ])

        # 最后再尝试全局配置（保留原有名称兼容）
        candidates.extend(["DINGTALK_WEBHOOK_URL", "DINGTALK_WEBHOOK_URL_DEFAULT", "DINGTALK_WEBHOOK"])

        for cand in candidates:
            val = os.environ.get(cand)
            if val:
                return val

        # 如果都没有找到，抛出异常
        raise ValueError(f"未找到项目 '{project_name or url_slug}' 对应的钉钉Webhook URL，且未设置默认的 Webhook URL。")
>>>>>>> c85976a (feat(通知): 支持每个项目独立通知 Hook；整理并扁平化测试目录)

    def send_message(self, content: str, msg_type='text', title='通知', is_at_all=False, project_name=None, url_slug = None):
        if not self.enabled:
            logger.info("钉钉推送未启用")
            return

        try:
            post_url = self._get_webhook_url(project_name=project_name, url_slug=url_slug)
            headers = {
                "Content-Type": "application/json",
                "Charset": "UTF-8"
            }
            if msg_type == 'markdown':
                message = {
                    "msgtype": "markdown",
                    "markdown": {
                        "title": title,  # Customize as needed
                        "text": content
                    },
                    "at": {
                        "isAtAll": is_at_all
                    }
                }
            else:
                message = {
                    "msgtype": "text",
                    "text": {
                        "content": content
                    },
                    "at": {
                        "isAtAll": is_at_all
                    }
                }
            response = requests.post(url=post_url, data=json.dumps(message), headers=headers)
            response_data = response.json()
            if response_data.get('errmsg') == 'ok':
<<<<<<< HEAD
                logger.info(f"钉钉消息发送成功! webhook_url:{post_url}")
            else:
                logger.error(f"钉钉消息发送失败! webhook_url:{post_url},errmsg:{response_data.get('errmsg')}")
        except Exception as e:
            logger.error(f"钉钉消息发送失败! ", e)
=======
                logger.info(f"钉钉消息发送成功! webhook_url:{self._mask_url(post_url)}")
            else:
                logger.error(f"钉钉消息发送失败! webhook_url:{self._mask_url(post_url)},errmsg:{response_data.get('errmsg')}")
        except Exception as e:
            logger.error(f"钉钉消息发送失败! {e}")

    @staticmethod
    def _mask_url(u: str) -> str:
        """掩码 webhook URL，隐藏 query 参数或最后的 path token。"""
        if not u:
            return u
        try:
            p = urllib.parse.urlparse(u)
            qs = urllib.parse.parse_qsl(p.query, keep_blank_values=True)
            if qs:
                masked_qs = [(k, '***') for k, v in qs]
                new_query = urllib.parse.urlencode(masked_qs)
                return urllib.parse.urlunparse((p.scheme, p.netloc, p.path, p.params, new_query, p.fragment))
            # mask last path segment
            parts = p.path.rstrip('/').split('/')
            if parts and len(parts[-1]) > 3:
                parts[-1] = '***'
                new_path = '/'.join(parts)
                return urllib.parse.urlunparse((p.scheme, p.netloc, new_path, p.params, p.query, p.fragment))
            return u
        except Exception:
            return '***'
>>>>>>> c85976a (feat(通知): 支持每个项目独立通知 Hook；整理并扁平化测试目录)
