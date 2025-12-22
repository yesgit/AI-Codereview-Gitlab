import json
import requests
import os
import json
import requests
import os
import re
import urllib.parse
from biz.utils.log import logger
import json
import requests
import os
import re
import urllib.parse
from biz.utils.log import logger
from biz.service.webhook_service import WebhookService


class WeComNotifier:
    def __init__(self, webhook_url=None):
        """初始化企业微信通知器
        :param webhook_url: 企业微信机器人 webhook 地址"""
        self.default_webhook_url = webhook_url or os.environ.get('WECOM_WEBHOOK_URL', '')
        self.enabled = os.environ.get('WECOM_ENABLED', '0') == '1'

    def _get_webhook_url(self, project_name=None, url_slug=None):
        """优先从 DB 获取项目级 webhook 配置，回退到环境变量。"""
        try:
            mapping = WebhookService.get_webhook_mapping(project_name=project_name, url_slug=url_slug)
            if mapping and mapping.get('wecom_url'):
                return mapping.get('wecom_url')
        except Exception:
            pass

        if not project_name and not url_slug:
            if self.default_webhook_url:
                return self.default_webhook_url
            raise ValueError("未提供项目名称/slug，且未设置默认的企业微信 Webhook URL。")

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
                f"WECOM_WEBHOOK_URL_{key}",
                f"WECOM_WEBHOOK_{key}",
            ])
        candidates.extend(["WECOM_WEBHOOK_URL", "WECOM_WEBHOOK_URL_DEFAULT", "WECOM_WEBHOOK"])

        for cand in candidates:
            val = os.environ.get(cand)
            if val:
                return val

        raise ValueError(f"未找到项目 '{project_name or url_slug}' 对应的企业微信 Webhook URL，且未设置默认的 WebHook URL。")

    def format_markdown_content(self, content, title=None):
        formatted_content = f"## {title}\n\n" if title else ""
        content = re.sub(r'#{5,}\s', '#### ', content)
        content = re.sub(r'\[(.*?)\]\((.*?)\)', r'[链接]\2', content)
        content = re.sub(r'<[^>]+>', '', content)
        formatted_content += content
        return formatted_content

    def send_message(self, content, msg_type='text', title=None, is_at_all=False, project_name=None, url_slug=None):
        if not self.enabled:
            logger.info("企业微信推送未启用")
            return
        try:
            post_url = self._get_webhook_url(project_name=project_name, url_slug=url_slug)
            MAX_CONTENT_BYTES = 4096 if msg_type == 'markdown' else 2048
            content_length = len(content.encode('utf-8'))
            if content_length <= MAX_CONTENT_BYTES:
                data = self._build_message(content, title, msg_type, is_at_all)
                self._send_message(post_url, data)
            else:
                logger.warning(f"消息内容超过{MAX_CONTENT_BYTES}字节限制，将分割发送。总长度: {content_length}字节")
                self._send_message_in_chunks(content, title, post_url, msg_type, is_at_all, MAX_CONTENT_BYTES)
        except Exception as e:
            logger.error(f"企业微信消息发送失败! {e}")

    def _send_message_in_chunks(self, content, title, post_url, msg_type, is_at_all, max_bytes):
        chunks = self._split_content(content, max_bytes)
        for i, chunk in enumerate(chunks):
            chunk_title = f"{title} (第{i + 1}/{len(chunks)}部分)" if title else f"消息 (第{i + 1}/{len(chunks)}部分)"
            data = self._build_message(chunk, chunk_title, msg_type, is_at_all)
            self._send_message(post_url, data, chunk_num=i + 1, total_chunks=len(chunks))

    def _split_content(self, content, max_bytes):
        chunks = []
        start_pos = 0
        content_bytes = content.encode('utf-8')
        content_length = len(content_bytes)
        while start_pos < content_length:
            end_pos = start_pos + max_bytes
            if end_pos >= content_length:
                chunk = content_bytes[start_pos:].decode('utf-8', errors='ignore')
                chunks.append(chunk)
                break
            while end_pos > start_pos:
                if content_bytes[end_pos - 1:end_pos] == b'\n':
                    break
                end_pos -= 1
            chunk = content_bytes[start_pos:end_pos].decode('utf-8', errors='ignore')
            chunks.append(chunk)
            start_pos = end_pos
        return chunks

    def _send_message(self, post_url, data, chunk_num=None, total_chunks=None):
        try:
            logger.debug(f"发送企业微信消息{'分块' if chunk_num else ''} {chunk_num}/{total_chunks if chunk_num else ''}: url={self._mask_url(post_url)}, data={data}")
            response = self._send_request(post_url, data)
            if response and response.get('errcode') != 0:
                logger.error(f"企业微信消息发送失败! webhook_url:{self._mask_url(post_url)}, errmsg:{response}")
            else:
                logger.info(f"企业微信消息{'分块' if chunk_num else ''}发送成功! webhook_url:{self._mask_url(post_url)}")
        except Exception as e:
            logger.error(f"企业微信消息{'分块' if chunk_num else ''}发送失败! {e}")

    def _send_request(self, url, data):
        try:
            response = requests.post(url, json=data, headers={'Content-Type': 'application/json'})
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"企业微信消息发送请求失败! url:{self._mask_url(url)}, error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"企业微信返回的 JSON 解析失败! url:{self._mask_url(url)}, error: {e}")
        return None

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

    def _build_message(self, content, title, msg_type, is_at_all):
        if msg_type == 'text':
            return self._build_text_message(content, is_at_all)
        elif msg_type == 'markdown':
            return self._build_markdown_message(content, title)
        else:
            raise ValueError(f"不支持的消息类型: {msg_type}")

    def _build_text_message(self, content, is_at_all):
        return {
            "msgtype": "text",
            "text": {
                "content": content,
                "mentioned_list": ["@all"] if is_at_all else []
            }
        }

    def _build_markdown_message(self, content, title):
        formatted_content = self.format_markdown_content(content, title)
        return {
            "msgtype": "markdown",
            "markdown": {"content": formatted_content}
        }
