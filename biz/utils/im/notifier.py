from biz.utils.im.dingtalk import DingTalkNotifier
from biz.utils.im.feishu import FeishuNotifier
from biz.utils.im.webhook import ExtraWebhookNotifier
from biz.utils.im.wecom import WeComNotifier


def send_notification(content, msg_type='text', title="通知", is_at_all=False, 
                      gitlab_base_url=None, project_slug=None, branch_name=None,
                      project_name=None, url_slug=None, webhook_data: dict={}):
    """
    发送通知消息到配置的平台(钉钉、飞书和企业微信)
    
    Args:
        content: 消息内容
        msg_type: 消息类型，支持text和markdown
        title: 消息标题(markdown类型时使用)
        is_at_all: 是否@所有人
        gitlab_base_url: GitLab实例地址，如 https://gitlab.com
        project_slug: 项目slug，如 mygroup/myproject
        branch_name: 分支名称
        project_name: 项目名称（兼容旧方式）
        url_slug: URL slug（兼容旧方式）
        webhook_data: push event、merge event的数据内容
    """
    # 钉钉推送
    dingtalk_notifier = DingTalkNotifier()
    dingtalk_notifier.send_message(
        content=content, msg_type=msg_type, title=title, is_at_all=is_at_all,
        gitlab_base_url=gitlab_base_url, project_slug=project_slug, branch_name=branch_name,
        project_name=project_name, url_slug=url_slug
    )

    # 企业微信推送
    wecom_notifier = WeComNotifier()
    wecom_notifier.send_message(
        content=content, msg_type=msg_type, title=title, is_at_all=is_at_all,
        gitlab_base_url=gitlab_base_url, project_slug=project_slug, branch_name=branch_name,
        project_name=project_name, url_slug=url_slug
    )

    # 飞书推送
    feishu_notifier = FeishuNotifier()
    feishu_notifier.send_message(
        content=content, msg_type=msg_type, title=title, is_at_all=is_at_all,
        gitlab_base_url=gitlab_base_url, project_slug=project_slug, branch_name=branch_name,
        project_name=project_name, url_slug=url_slug
    )

    # 额外自定义webhook通知
    extra_webhook_notifier = ExtraWebhookNotifier()
    system_data = {
        "content": content,
        "msg_type": msg_type,
        "title": title,
        "is_at_all": is_at_all,
        "gitlab_base_url": gitlab_base_url,
        "project_slug": project_slug,
        "branch_name": branch_name,
        "project_name": project_name,
        "url_slug": url_slug
    }
    extra_webhook_notifier.send_message(system_data=system_data, webhook_data=webhook_data)
