import json
import requests
import os
import json
import requests
import os
import re
import urllib.parse
from biz.utils.log import logger
from biz.service.webhook_service import WebhookService


class WeComNotifier:
    def __init__(self, webhook_url=None):
        """
        初始化企业微信通知器
        :param webhook_url: 企业微信机器人webhook地址
        """
        self.default_webhook_url = webhook_url or os.environ.get('WECOM_WEBHOOK_URL', '')
        self.enabled = os.environ.get('WECOM_ENABLED', '0') == '1'

    def _get_webhook_url(self, project_name=None, url_slug=None):
        """
        获取项目对应的 Webhook URL
        :param project_name: 项目名称
        :return: Webhook URL
        :raises ValueError: 如果未找到 Webhook URL
        """
        # 优先从数据库中读取项目级 webhook 配置
        try:
            mapping = WebhookService.get_webhook_mapping(project_name=project_name, url_slug=url_slug)
            if mapping and mapping.get('wecom_url'):
                return mapping.get('wecom_url')
        except Exception:
            pass

        # 如果未提供 project_name 且未提供 url_slug，直接返回默认的 Webhook URL（或抛错）
        if not project_name and not url_slug:
            if self.default_webhook_url:
                return self.default_webhook_url
            else:
                raise ValueError("未提供项目名称/slug，且未设置默认的企业微信 Webhook URL。")

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
                f"WECOM_WEBHOOK_URL_{key}",
                f"WECOM_WEBHOOK_{key}",
            ])

        # 最后再尝试全局配置（保留原有名称兼容）
        candidates.extend(["WECOM_WEBHOOK_URL", "WECOM_WEBHOOK_URL_DEFAULT", "WECOM_WEBHOOK"])

        for cand in candidates:
            val = os.environ.get(cand)
            if val:
                return val

        # 如果都没有找到，抛出异常
        raise ValueError(f"未找到项目 '{project_name or url_slug}' 对应的企业微信 Webhook URL，且未设置默认的 WebHook URL。")

    def format_markdown_content(self, content, title=None):
        """
        格式化markdown内容以适配企业微信
        """
        # 处理标题
        formatted_content = f"## {title}\n\n" if title else ""

        # 将内容中的5级以上标题转为4级
        content = re.sub(r'#{5,}\s', '#### ', content)

        # 处理链接格式
        content = re.sub(r'\[(.*?)\]\((.*?)\)', r'[链接]\2', content)

        # 移除HTML标签
        content = re.sub(r'<[^>]+>', '', content)

        formatted_content += content
        return formatted_content

    def send_message(self, content, msg_type='text', title=None, is_at_all=False, project_name=None,
                     url_slug=None):
        """
        发送企业微信消息
        :param content: 消息内容
        :param msg_type: 消息类型，支持 text 和 markdown
        :param title: 消息标题 (markdown 类型时使用)
        :param is_at_all: 是否 @所有人
        :param project_name: 关联项目名称
        :param url_slug: GitLab URL Slug
        """
        if not self.enabled:
            logger.info("企业微信推送未启用")
            return

        try:
            post_url = self._get_webhook_url(project_name=project_name, url_slug=url_slug)
            # 企业微信消息内容最大长度限制
            # text类型最大2048字节
            # https://developer.work.weixin.qq.com/document/path/91770#%E6%96%87%E6%9C%AC%E7%B1%BB%E5%9E%8B
            # markdown类型最大4096字节
            # https://developer.work.weixin.qq.com/document/path/91770#markdown%E7%B1%BB%E5%9E%8B
            MAX_CONTENT_BYTES = 4096 if msg_type == 'markdown' else 2048

            # 检查内容长度
            content_length = len(content.encode('utf-8'))

            if content_length <= MAX_CONTENT_BYTES:
                # 内容长度在限制范围内，直接发送
                data = self._build_message(content, title, msg_type, is_at_all)
                self._send_message(post_url, data)
            else:
                # 内容超过限制，需要分割发送
                logger.warning(f"消息内容超过{MAX_CONTENT_BYTES}字节限制，将分割发送。总长度: {content_length}字节")
                self._send_message_in_chunks(content, title, post_url, msg_type, is_at_all, MAX_CONTENT_BYTES)

        except Exception as e:
            logger.error(f"企业微信消息发送失败! {e}")

    def _send_message_in_chunks(self, content, title, post_url, msg_type, is_at_all, max_bytes):
        """
        将内容分割成多个部分并分别发送
        """
        chunks = self._split_content(content, max_bytes)
        for i, chunk in enumerate(chunks):
            chunk_title = f"{title} (第{i + 1}/{len(chunks)}部分)" if title else f"消息 (第{i + 1}/{len(chunks)}部分)"
            data = self._build_message(chunk, chunk_title, msg_type, is_at_all)
            self._send_message(post_url, data, chunk_num=i + 1, total_chunks=len(chunks))

    def _split_content(self, content, max_bytes):
        """
        将内容按最大字节长度分割成多个部分
        """
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
        """ 发送请求并返回响应 """
        try:
            logger.debug(
                f"发送企业微信消息{'分块' if chunk_num else ''} {chunk_num}/{total_chunks if chunk_num else ''}: url={self._mask_url(post_url)}, data={data}")
            response = self._send_request(post_url, data)

            if response and response.get('errcode') != 0:
                logger.error(f"企业微信消息发送失败! webhook_url:{self._mask_url(post_url)}, errmsg:{response}")
            else:
                logger.info(f"企业微信消息{'分块' if chunk_num else ''}发送成功! webhook_url:{self._mask_url(post_url)}")

            if response and response.get('errcode') != 0:
                logger.error(f"企业微信消息发送失败! webhook_url:{self._mask_url(post_url)}, errmsg:{response}")
            else:
                logger.info(f"企业微信消息{'分块' if chunk_num else ''}发送成功! webhook_url:{self._mask_url(post_url)}")
>>>>>>> c85976a (feat(通知): 支持每个项目独立通知 Hook；整理并扁平化测试目录)

        except Exception as e:
            logger.error(f"企业微信消息{'分块' if chunk_num else ''}发送失败! {e}")

    def _send_request(self, url, data):
        """ 发送请求并返回 JSON 响应 """
        try:
            response = requests.post(url, json=data, headers={'Content-Type': 'application/json'})
            response.raise_for_status()  # 触发 HTTP 错误
            return response.json()
        except requests.RequestException as e:
<<<<<<< HEAD
            logger.error(f"企业微信消息发送请求失败! url:{url}, error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"企业微信返回的 JSON 解析失败! url:{url}, error: {e}")
        return None

=======
            logger.error(f"企业微信消息发送请求失败! url:{self._mask_url(url)}, error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"企业微信返回的 JSON 解析失败! url:{self._mask_url(url)}, error: {e}")
        return None

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
            parts = p.path.rstrip('/').split('/')
            if parts and len(parts[-1]) > 3:
                parts[-1] = '***'
                new_path = '/'.join(parts)
                return urllib.parse.urlunparse((p.scheme, p.netloc, new_path, p.params, p.query, p.fragment))
            return u
        except Exception:
            return '***'

>>>>>>> c85976a (feat(通知): 支持每个项目独立通知 Hook；整理并扁平化测试目录)
    def _build_message(self, content, title, msg_type, is_at_all):
        """ 构造消息 """
        if msg_type == 'text':
            return self._build_text_message(content, is_at_all)
        elif msg_type =='markdown':
            return self._build_markdown_message(content, title)
        else:
            raise ValueError(f"不支持的消息类型: {msg_type}")

    def _build_text_message(self, content, is_at_all):
        """ 构造纯文本消息 """
        return {
            "msgtype": "text",
            "text": {
                "content": content,
                "mentioned_list": ["@all"] if is_at_all else []
            }
        }

    def _build_markdown_message(self, content, title):
        """ 构造 Markdown 消息 """
        formatted_content = self.format_markdown_content(content, title)
        return {
            "msgtype": "markdown",
            "markdown": {
                "content": formatted_content
            }
        }
