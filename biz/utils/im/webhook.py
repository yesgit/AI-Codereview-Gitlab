import os
import urllib.parse
from biz.utils.log import logger
import requests


class ExtraWebhookNotifier:
    def __init__(self, webhook_url=None):
        """
        初始化ExtraWebhook通知器
        :param webhook_url: 自定义webhook地址
        """
        self.default_webhook_url = webhook_url or os.environ.get('EXTRA_WEBHOOK_URL', '')
        self.enabled = os.environ.get('EXTRA_WEBHOOK_ENABLED', '0') == '1'

    def send_message(self, system_data: dict, webhook_data: dict):
        """
        发送额外自定义webhook消息
        :param system_data: 系统消息内容
        :param webhook_data: github、gitlab的push event、merge event的原始数据
        """
        if not self.enabled:
            logger.info("ExtraWebhook推送未启用")
            return

        try:
            data = {
                "ai_codereview_data": system_data,
                "webhook_data": webhook_data
            }
            response = requests.post(
                url=self.default_webhook_url,
                json=data,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code != 200:
                logger.error(f"ExtraWebhook消息发送失败! webhook_url:{self._mask_url(self.default_webhook_url)}, error_msg:{response.text}")
                return

        except Exception as e:
            logger.error(f"ExtraWebhook消息发送失败! {e}")

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
