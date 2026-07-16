"""
Webhook 事件处理路由 - 保持与原系统兼容
"""
import os
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Header
from urllib.parse import urlparse

from biz.gitlab.webhook_handler import slugify_url
from biz.service.webhook_service import WebhookService
from biz.queue.worker import (
    handle_merge_request_event,
    handle_push_event,
    handle_github_pull_request_event,
    handle_github_push_event,
    handle_gitea_pull_request_event,
    handle_gitea_push_event,
    handle_note_event
)
from biz.utils.log import logger
from biz.utils.queue import handle_queue

router = APIRouter()


@router.post("/review/webhook")
async def handle_webhook(request: Request):
    """
    处理 Webhook 请求的主路由（兼容原系统）
    """
    try:
        data = await request.json()
        if not data:
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        # 判断webhook来源
        github_event = request.headers.get('X-GitHub-Event')
        gitea_event = request.headers.get('X-Gitea-Event')

        if gitea_event:
            return await handle_gitea_webhook(gitea_event, data, request)
        elif github_event:
            return await handle_github_webhook(github_event, data, request)
        else:
            return await handle_gitlab_webhook(data, request)
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=400, detail="Invalid request")


async def handle_github_webhook(event_type: str, data: dict, request: Request):
    """处理 GitHub Webhook"""
    github_token = os.getenv('GITHUB_ACCESS_TOKEN') or request.headers.get('X-GitHub-Token')
    if not github_token:
        return {"message": "Missing GitHub access token"}, 400

    github_url = os.getenv('GITHUB_URL') or 'https://github.com'
    github_url_slug = slugify_url(github_url)

    logger.info(f'Received GitHub event: {event_type}')
    logger.info(f'Payload: {data}')

    if event_type == "pull_request":
        handle_queue(handle_github_pull_request_event, data, github_token, github_url, github_url_slug)
        return {"message": f'GitHub request received(event_type={event_type}), will process asynchronously.'}, 200
    elif event_type == "push":
        handle_queue(handle_github_push_event, data, github_token, github_url, github_url_slug)
        return {"message": f'GitHub request received(event_type={event_type}), will process asynchronously.'}, 200
    else:
        error_message = f'Only pull_request and push events are supported for GitHub webhook, but received: {event_type}.'
        logger.error(error_message)
        return {"error": error_message}, 400


async def handle_gitlab_webhook(data: dict, request: Request):
    """处理 GitLab Webhook"""
    object_kind = data.get("object_kind")

    gitlab_url = os.getenv('GITLAB_URL') or request.headers.get('X-Gitlab-Instance')
    if not gitlab_url:
        repository = data.get('repository')
        if not repository:
            return {"message": "Missing GitLab URL"}, 400
        homepage = repository.get("homepage")
        if not homepage:
            return {"message": "Missing GitLab URL"}, 400
        try:
            parsed_url = urlparse(homepage)
            gitlab_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        except Exception as e:
            return {"error": f"Failed to parse homepage URL: {str(e)}"}, 400

    gitlab_token = os.getenv('GITLAB_ACCESS_TOKEN') or request.headers.get('X-Gitlab-Token')
    if not gitlab_token:
        return {"message": "Missing GitLab access token"}, 400

    gitlab_url_slug = slugify_url(gitlab_url)

    # 查项目配置，获取评论目标和审查策略
    project_slug = data.get('project', {}).get('path_with_namespace', '')
    project_name = data.get('project', {}).get('name', '')
    url_slug = gitlab_url_slug
    comment_url = gitlab_url
    comment_token = gitlab_token
    comment_project_path = project_slug  # 默认用源库路径
    comment_project_id = None
    review_strategy = os.getenv('REVIEW_STRATEGY', 'diff_only')
    if project_slug:
        # 先尝试用 gitlab_base_url + project_slug 精确匹配
        config = WebhookService.get_webhook_mapping_by_gitlab_project(
            gitlab_url.rstrip('/'), project_slug
        )
        # 如果精确匹配失败，回退到 url_slug 或 project_name 查找
        if not config and (url_slug or project_name):
            config = WebhookService.get_webhook_mapping(
                project_name=project_name, url_slug=url_slug
            )
        if config:
            if config.get('comment_enabled') and config.get('comment_url'):
                comment_url = config.get('comment_url')
                comment_token = config.get('comment_token') or gitlab_token
                if config.get('comment_project_path'):
                    comment_project_path = config['comment_project_path']
                if config.get('comment_project_id'):
                    comment_project_id = config['comment_project_id']
            if config.get('review_strategy') and config['review_strategy'].strip():
                review_strategy = config['review_strategy'].strip()

    logger.info(f'Comment config resolved: comment_url={comment_url}, comment_project_path={comment_project_path}, comment_project_id={comment_project_id}, comment_enabled={bool(comment_url != gitlab_url)}')

    logger.info(f'Received event: {object_kind}')
    logger.info(f'Payload: {data}')

    if object_kind == "merge_request":
        handle_queue(handle_merge_request_event, data, gitlab_token, gitlab_url, gitlab_url_slug, comment_url, comment_token, review_strategy, comment_project_path, comment_project_id)
        return {"message": f'Request received(object_kind={object_kind}), will process asynchronously.'}, 200
    elif object_kind == "push":
        handle_queue(handle_push_event, data, gitlab_token, gitlab_url, gitlab_url_slug, comment_url, comment_token, review_strategy, comment_project_path, comment_project_id)
        return {"message": f'Request received(object_kind={object_kind}), will process asynchronously.'}, 200
    elif object_kind == "note":
        handle_queue(handle_note_event, data, gitlab_token, gitlab_url, gitlab_url_slug, comment_url, comment_token, review_strategy, comment_project_path, comment_project_id)
        return {"message": f'Request received(object_kind={object_kind}), will process asynchronously.'}, 200
    else:
        error_message = f'Only merge_request, push and note events are supported (both Webhook and System Hook), but received: {object_kind}.'
        logger.error(error_message)
        return {"error": error_message}, 400


async def handle_gitea_webhook(event_type: str, data: dict, request: Request):
    """处理 Gitea Webhook"""
    gitea_token = os.getenv('GITEA_ACCESS_TOKEN') or request.headers.get('X-Gitea-Token')
    if not gitea_token:
        return {"message": "Missing Gitea access token"}, 400

    gitea_url = os.getenv('GITEA_URL') or 'https://gitea.com'
    gitea_url_slug = slugify_url(gitea_url)

    logger.info(f'Received Gitea event: {event_type}')
    logger.info(f'Payload: {data}')

    if event_type == "pull_request":
        handle_queue(handle_gitea_pull_request_event, data, gitea_token, gitea_url, gitea_url_slug)
        return {"message": f'Gitea request received(event_type={event_type}), will process asynchronously.'}, 200
    elif event_type == "push":
        handle_queue(handle_gitea_push_event, data, gitea_token, gitea_url, gitea_url_slug)
        return {"message": f'Gitea request received(event_type={event_type}), will process asynchronously.'}, 200
    else:
        error_message = f'Only pull_request and push events are supported for Gitea webhook, but received: {event_type}.'
        logger.error(error_message)
        return {"error": error_message}, 400
