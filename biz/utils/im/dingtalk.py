import base64
import hashlib
import hmac
import json
import requests
import os
import re
import time
import urllib.parse
from typing import Optional
from biz.utils.log import logger
from biz.service.webhook_service import WebhookService


class DingTalkNotifier:
    """干净的钉钉机器人通知器实现，支持 URL 掩码与可选签名。"""

    def __init__(self, webhook_url: Optional[str] = None):
        self.default_webhook_url = webhook_url or os.environ.get('DINGTALK_WEBHOOK_URL', '')
        self.enabled = os.environ.get('DINGTALK_ENABLED', '0') == '1'
        self.secret = os.environ.get('DINGTALK_SECRET')

    def _get_webhook_url(self, project_name: Optional[str] = None, url_slug: Optional[str] = None) -> str:
        try:
            mapping = WebhookService.get_webhook_mapping(project_name=project_name, url_slug=url_slug)
            if mapping and mapping.get('dingtalk_url'):
                return mapping.get('dingtalk_url')
        except Exception:
            pass

        if not project_name and not url_slug:
            if self.default_webhook_url:
                return self.default_webhook_url
            raise ValueError("未提供项目名称/slug，且未设置默认的钉钉 Webhook URL。")

        def normalize(s: Optional[str]) -> str:
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
                f"DINGTALK_WEBHOOK_URL_{key}",
                f"DINGTALK_WEBHOOK_{key}",
            ])
        candidates.extend(["DINGTALK_WEBHOOK_URL", "DINGTALK_WEBHOOK_URL_DEFAULT", "DINGTALK_WEBHOOK"])

        for cand in candidates:
            val = os.environ.get(cand)
            if val:
                return val

        raise ValueError(f"未找到项目 '{project_name or url_slug}' 对应的钉钉 Webhook URL，且未设置默认的 WebHook URL。")

    def _sign_url(self, url: str) -> str:
        if not self.secret:
            return url
        try:
            timestamp = str(int(time.time() * 1000))
            secret_enc = self.secret.encode('utf-8')
            string_to_sign = f"{timestamp}\n{self.secret}"
            string_to_sign_enc = string_to_sign.encode('utf-8')
            hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
            sep = '&' if '?' in url else '?'
            return f"{url}{sep}timestamp={timestamp}&sign={sign}"
        except Exception:
            return url

    def send_message(self, content: str, msg_type: str = 'text', title: str = '通知', is_at_all: bool = False,
                     project_name: Optional[str] = None, url_slug: Optional[str] = None):
        if not self.enabled:
            logger.info("钉钉推送未启用")
            return
        try:
            post_url = self._get_webhook_url(project_name=project_name, url_slug=url_slug)
            post_url = self._sign_url(post_url)

            headers = {"Content-Type": "application/json; charset=utf-8"}
            if msg_type == 'markdown':
                payload = {"msgtype": "markdown", "markdown": {"title": title, "text": content}, "at": {"isAtAll": is_at_all}}
            else:
                payload = {"msgtype": "text", "text": {"content": content}, "at": {"isAtAll": is_at_all}}

            logger.debug(f"发送钉钉消息: url={self._mask_url(post_url)}, payload={payload}")
            resp = requests.post(post_url, json=payload, headers=headers, timeout=10)
            try:
                result = resp.json()
            except ValueError:
                result = {"errmsg": resp.text}

            if result.get('errmsg') in ('ok', 'success') or result.get('errcode') == 0:
                logger.info(f"钉钉消息发送成功! webhook_url:{self._mask_url(post_url)}")
            else:
                logger.error(f"钉钉消息发送失败! webhook_url:{self._mask_url(post_url)}, errmsg:{result}")
        except Exception as e:
            logger.error(f"钉钉消息发送失败! {e}")

    @staticmethod
    def _mask_url(u: str) -> str:
        if not u:
            return u
        try:
            p = urllib.parse.urlparse(u)
            qs = urllib.parse.parse_qsl(p.query, keep_blank_values=True)
            if qs:
                masked_qs = [(k, '***') for k, v in qs]
                new_query = urllib.parse.urlencode(masked_qs)
                return urllib.parse.urlunparse((p.scheme, p.netloc, p.path, p.params, new_query, p.fragment))
            parts = p.path.rstrip('/').split('/')
            if parts and len(parts[-1]) > 3:
                parts[-1] = '***'
                new_path = '/'.join(parts)
                return urllib.parse.urlunparse((p.scheme, p.netloc, new_path, p.params, p.query, p.fragment))
            return u
        except Exception:
            return '***'
