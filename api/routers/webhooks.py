"""
项目配置 Webhook API
"""
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
import pandas as pd

from biz.service.webhook_service import WebhookService
from biz.service.branch_webhook_service import BranchWebhookService
from biz.service.review_service import ReviewService
from biz.api import push_review_enabled
from biz.utils.im.dingtalk import DingTalkNotifier
from biz.utils.im.feishu import FeishuNotifier
from biz.utils.im.wecom import WeComNotifier
from biz.utils.im import notifier
from biz.utils.log import logger
from biz.utils.reporter import Reporter
from api.routers.auth import get_current_user

router = APIRouter()


class WebhookCreate(BaseModel):
    project_name: Optional[str] = None
    url_slug: Optional[str] = None
    gitlab_base_url: Optional[str] = None
    project_slug: Optional[str] = None
    dingtalk_url: Optional[str] = None
    feishu_url: Optional[str] = None
    wecom_url: Optional[str] = None
    dingtalk_enabled: Optional[bool] = None
    feishu_enabled: Optional[bool] = None
    wecom_enabled: Optional[bool] = None
    custom_prompt_system: Optional[str] = None
    custom_prompt_user: Optional[str] = None
    gitlab_token: Optional[str] = None
    review_style: Optional[str] = None
    daily_report_enabled: Optional[bool] = None
    supported_extensions: Optional[str] = None
    comment_enabled: Optional[bool] = None
    comment_url: Optional[str] = None
    comment_token: Optional[str] = None
    comment_project_path: Optional[str] = None
    review_strategy: Optional[str] = None


class WebhookUpdate(BaseModel):
    project_name: Optional[str] = None
    url_slug: Optional[str] = None
    gitlab_base_url: Optional[str] = None
    project_slug: Optional[str] = None
    dingtalk_url: Optional[str] = None
    feishu_url: Optional[str] = None
    wecom_url: Optional[str] = None
    dingtalk_enabled: Optional[bool] = None
    feishu_enabled: Optional[bool] = None
    wecom_enabled: Optional[bool] = None
    custom_prompt_system: Optional[str] = None
    custom_prompt_user: Optional[str] = None
    gitlab_token: Optional[str] = None
    review_style: Optional[str] = None
    daily_report_enabled: Optional[bool] = None
    supported_extensions: Optional[str] = None
    comment_enabled: Optional[bool] = None
    comment_url: Optional[str] = None
    comment_token: Optional[str] = None
    comment_project_path: Optional[str] = None
    review_strategy: Optional[str] = None


class WebhookResponse(BaseModel):
    id: int
    project_name: Optional[str] = None
    url_slug: Optional[str] = None
    gitlab_base_url: Optional[str] = None
    project_slug: Optional[str] = None
    dingtalk_url: Optional[str] = None
    feishu_url: Optional[str] = None
    wecom_url: Optional[str] = None
    dingtalk_enabled: Optional[bool] = None
    feishu_enabled: Optional[bool] = None
    wecom_enabled: Optional[bool] = None
    custom_prompt_system: Optional[str] = None
    custom_prompt_user: Optional[str] = None
    gitlab_token: Optional[str] = None
    review_style: Optional[str] = None
    daily_report_enabled: Optional[bool] = None
    supported_extensions: Optional[str] = None
    comment_enabled: Optional[bool] = None
    comment_url: Optional[str] = None
    comment_token: Optional[str] = None
    comment_project_path: Optional[str] = None
    review_strategy: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


@router.get("", response_model=List[WebhookResponse])
async def get_all_webhooks(current_user: str = Depends(get_current_user)):
    """获取所有项目配置"""
    mappings = WebhookService.get_all_webhook_mappings()
    return mappings


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(webhook: WebhookCreate, current_user: str = Depends(get_current_user)):
    """创建项目配置"""
    # 基本校验：项目名称必须填写
    if not webhook.project_name or not webhook.project_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="项目名称不能为空"
        )
    
    if (webhook.gitlab_base_url and not webhook.project_slug) or (not webhook.gitlab_base_url and webhook.project_slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="gitlab_base_url 和 project_slug 必须同时填写"
        )
    
    # 检查重复
    existing = WebhookService.get_all_webhook_mappings()
    dup_errors = []
    
    if webhook.gitlab_base_url and webhook.project_slug:
        for m in existing:
            if m.get('gitlab_base_url') == webhook.gitlab_base_url and m.get('project_slug') == webhook.project_slug:
                dup_errors.append(f"已存在相同的 gitlab_base_url + project_slug")
                break
    
    if webhook.project_name:
        for m in existing:
            if m.get('project_name') == webhook.project_name:
                dup_errors.append(f"已存在相同的 project_name")
                break
    
    if webhook.url_slug:
        for m in existing:
            if m.get('url_slug') == webhook.url_slug:
                dup_errors.append(f"已存在相同的 url_slug")
                break
    
    if dup_errors:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=dup_errors
        )
    
    result = WebhookService.create_or_update_webhook_mapping(
        gitlab_base_url=webhook.gitlab_base_url,
        project_slug=webhook.project_slug,
        project_name=webhook.project_name,
        url_slug=webhook.url_slug,
        dingtalk_url=webhook.dingtalk_url,
        feishu_url=webhook.feishu_url,
        wecom_url=webhook.wecom_url,
        dingtalk_enabled=webhook.dingtalk_enabled,
        feishu_enabled=webhook.feishu_enabled,
        wecom_enabled=webhook.wecom_enabled,
        custom_prompt_system=webhook.custom_prompt_system,
        custom_prompt_user=webhook.custom_prompt_user,
        gitlab_token=webhook.gitlab_token,
        review_style=webhook.review_style,
        daily_report_enabled=webhook.daily_report_enabled,
        supported_extensions=webhook.supported_extensions,
        comment_enabled=webhook.comment_enabled,
        comment_url=webhook.comment_url,
        comment_token=webhook.comment_token,
        comment_project_path=webhook.comment_project_path,
        review_strategy=webhook.review_strategy
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建配置失败"
        )
    
    return result


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(webhook_id: int, webhook: WebhookUpdate, current_user: str = Depends(get_current_user)):
    """更新项目配置"""
    # 检查冲突
    conflicts = []
    all_m = WebhookService.get_all_webhook_mappings()
    
    for m in all_m:
        if m.get('id') == webhook_id:
            continue
        if webhook.gitlab_base_url and webhook.project_slug and m.get('gitlab_base_url') == webhook.gitlab_base_url and m.get('project_slug') == webhook.project_slug:
            conflicts.append("冲突: 存在相同 gitlab_base_url + project_slug")
        if webhook.project_name and m.get('project_name') == webhook.project_name:
            conflicts.append("冲突: 存在相同 project_name")
        if webhook.url_slug and m.get('url_slug') == webhook.url_slug:
            conflicts.append("冲突: 存在相同 url_slug")
    
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=conflicts
        )
    
    result = WebhookService.update_webhook_mapping_by_id(
        webhook_id,
        gitlab_base_url=webhook.gitlab_base_url,
        project_slug=webhook.project_slug,
        project_name=webhook.project_name,
        url_slug=webhook.url_slug,
        dingtalk_url=webhook.dingtalk_url,
        feishu_url=webhook.feishu_url,
        wecom_url=webhook.wecom_url,
        dingtalk_enabled=webhook.dingtalk_enabled,
        feishu_enabled=webhook.feishu_enabled,
        wecom_enabled=webhook.wecom_enabled,
        custom_prompt_system=webhook.custom_prompt_system,
        custom_prompt_user=webhook.custom_prompt_user,
        gitlab_token=webhook.gitlab_token,
        review_style=webhook.review_style,
        daily_report_enabled=webhook.daily_report_enabled,
        supported_extensions=webhook.supported_extensions,
        comment_enabled=webhook.comment_enabled,
        comment_url=webhook.comment_url,
        comment_token=webhook.comment_token,
        review_strategy=webhook.review_strategy
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"配置 {webhook_id} 不存在或更新失败"
        )
    
    # 返回更新后的数据
    updated = WebhookService.get_all_webhook_mappings()
    for item in updated:
        if item.get('id') == webhook_id:
            return item
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"配置 {webhook_id} 不存在"
    )


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(webhook_id: int, current_user: str = Depends(get_current_user)):
    """删除项目配置"""
    WebhookService.delete_webhook_mapping(webhook_id)
    return None


@router.post("/{webhook_id}/send-daily-report", status_code=status.HTTP_200_OK)
async def send_webhook_daily_report(webhook_id: int, current_user: str = Depends(get_current_user)):
    """为指定项目配置发送日报"""
    logger.info(f"📋 开始为项目配置 {webhook_id} 发送日报")
    
    # 获取项目配置
    all_configs = WebhookService.get_all_webhook_mappings()
    config = None
    for c in all_configs:
        if c.get('id') == webhook_id:
            config = c
            break
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目配置 {webhook_id} 不存在"
        )
    
    # 获取当前日期0点和23点59分59秒的时间戳（使用 UTC 时间）
    start_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    end_time = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=0).timestamp()
    
    logger.info(f"📋 时间范围: {datetime.fromtimestamp(start_time, tz=timezone.utc)} ~ {datetime.fromtimestamp(end_time, tz=timezone.utc)}")
    
    # 获取当日审查日志
    if push_review_enabled:
        df = ReviewService().get_push_review_logs(updated_at_gte=start_time, updated_at_lte=end_time)
    else:
        df = ReviewService().get_mr_review_logs(updated_at_gte=start_time, updated_at_lte=end_time)
    
    if df.empty:
        logger.info("⚠️ 当日无审查数据")
        return {"message": "当日无审查数据", "count": 0}
    
    # 筛选属于该项目的日志
    logs = df.to_dict(orient="records")
    
    # 根据 gitlab_base_url 和 project_slug 或 project_name 筛选
    filtered_logs = []
    gitlab_base_url = config.get('gitlab_base_url')
    project_slug = config.get('project_slug')
    project_name = config.get('project_name')
    
    for log in logs:
        # 优先使用 gitlab_base_url + project_slug 匹配
        if gitlab_base_url and project_slug:
            if log.get('gitlab_base_url') == gitlab_base_url and log.get('project_slug') == project_slug:
                filtered_logs.append(log)
        elif project_name:
            if log.get('project_name') == project_name:
                filtered_logs.append(log)
    
    logger.info(f"📋 筛选后共有 {len(filtered_logs)} 条记录")
    
    if not filtered_logs:
        logger.info("⚠️ 该项目当日无审查数据")
        return {"message": "该项目当日无审查数据", "count": 0}
    
    # 检查配置的日报开关
    if config.get('daily_report_enabled') is not True:
        logger.info(f"⏭️ 该项目未启用日报 (daily_report_enabled={config.get('daily_report_enabled')})")
    
    # 去重：基于 (author, message) 组合
    df_filtered = pd.DataFrame(filtered_logs)
    df_unique = df_filtered.drop_duplicates(subset=["author", "commit_messages"])
    df_sorted = df_unique.sort_values(by="author")
    commits = df_sorted.to_dict(orient="records")
    
    # 生成日报内容
    title_prefix = f"项目:{project_name or f'{gitlab_base_url}/{project_slug}'}"
    import json
    report_txt = Reporter().generate_report(json.dumps(commits), title_prefix=title_prefix)
    
    # 发送通知
    if config.get('dingtalk_url'):
        dt_notifier = DingTalkNotifier(config=config)
        dt_notifier.send_message(
            content=report_txt, 
            msg_type="markdown", 
            title=f"代码提交日报 - {title_prefix}"
        )
    if config.get('feishu_url'):
        fs_notifier = FeishuNotifier(config=config)
        fs_notifier.send_message(
            content=report_txt, 
            msg_type="markdown", 
            title=f"代码提交日报 - {title_prefix}"
        )
    if config.get('wecom_url'):
        wc_notifier = WeComNotifier(config=config)
        wc_notifier.send_message(
            content=report_txt, 
            msg_type="markdown", 
            title=f"代码提交日报 - {title_prefix}"
        )
    
    # 如果配置无效，使用默认通知方式
    if not any(config.get(f) for f in ['dingtalk_url', 'feishu_url', 'wecom_url']):
        notifier.send_notification(
            content=report_txt, 
            msg_type="markdown", 
            title=f"代码提交日报 - {title_prefix}"
        )
    
    logger.info(f"✅ 日报发送成功，共 {len(commits)} 条记录")
    return {"message": "日报发送成功", "count": len(commits)}
