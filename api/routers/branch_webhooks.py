"""
分支配置 Webhook API
"""
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
import pandas as pd
import fnmatch

from biz.service.webhook_service import WebhookService
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


class BranchWebhookCreate(BaseModel):
    gitlab_base_url: str
    project_slug: str
    branch_pattern: str
    dingtalk_url: Optional[str] = None
    feishu_url: Optional[str] = None
    wecom_url: Optional[str] = None
    dingtalk_enabled: Optional[bool] = None
    feishu_enabled: Optional[bool] = None
    wecom_enabled: Optional[bool] = None
    custom_prompt_system: Optional[str] = None
    custom_prompt_user: Optional[str] = None
    review_style: Optional[str] = None
    gitlab_token: Optional[str] = None
    daily_report_enabled: Optional[bool] = None
    supported_extensions: Optional[str] = None


class BranchWebhookUpdate(BaseModel):
    gitlab_base_url: Optional[str] = None
    project_slug: Optional[str] = None
    branch_pattern: Optional[str] = None
    dingtalk_url: Optional[str] = None
    feishu_url: Optional[str] = None
    wecom_url: Optional[str] = None
    dingtalk_enabled: Optional[bool] = None
    feishu_enabled: Optional[bool] = None
    wecom_enabled: Optional[bool] = None
    custom_prompt_system: Optional[str] = None
    custom_prompt_user: Optional[str] = None
    review_style: Optional[str] = None
    gitlab_token: Optional[str] = None
    daily_report_enabled: Optional[bool] = None
    supported_extensions: Optional[str] = None


class BranchWebhookResponse(BaseModel):
    id: int
    gitlab_base_url: str
    project_slug: str
    branch_pattern: str
    dingtalk_url: Optional[str] = None
    feishu_url: Optional[str] = None
    wecom_url: Optional[str] = None
    dingtalk_enabled: Optional[bool] = None
    feishu_enabled: Optional[bool] = None
    wecom_enabled: Optional[bool] = None
    custom_prompt_system: Optional[str] = None
    custom_prompt_user: Optional[str] = None
    review_style: Optional[str] = None
    gitlab_token: Optional[str] = None
    daily_report_enabled: Optional[bool] = None
    supported_extensions: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


@router.get("", response_model=List[BranchWebhookResponse])
async def get_all_branch_webhooks(current_user: str = Depends(get_current_user)):
    """获取所有分支配置"""
    configs = WebhookService.get_all_branch_webhook_configs()
    return configs


@router.post("", response_model=BranchWebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_branch_webhook(webhook: BranchWebhookCreate, current_user: str = Depends(get_current_user)):
    """创建分支配置"""
    # 基本校验
    if not webhook.gitlab_base_url or not webhook.project_slug or not webhook.branch_pattern:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="gitlab_base_url、project_slug 和 branch_pattern 都是必填项"
        )
    
    # 检查重复
    existing = WebhookService.get_all_branch_webhook_configs()
    dup_found = False
    
    for m in existing:
        if (m.get('gitlab_base_url') == webhook.gitlab_base_url and 
            m.get('project_slug') == webhook.project_slug and 
            m.get('branch_pattern') == webhook.branch_pattern):
            dup_found = True
            break
    
    if dup_found:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"已存在相同的分支配置: {webhook.gitlab_base_url} / {webhook.project_slug} / {webhook.branch_pattern}"
        )
    
    result = WebhookService.create_branch_webhook_config(
        gitlab_base_url=webhook.gitlab_base_url,
        project_slug=webhook.project_slug,
        branch_pattern=webhook.branch_pattern,
        dingtalk_url=webhook.dingtalk_url,
        feishu_url=webhook.feishu_url,
        wecom_url=webhook.wecom_url,
        dingtalk_enabled=webhook.dingtalk_enabled,
        feishu_enabled=webhook.feishu_enabled,
        wecom_enabled=webhook.wecom_enabled,
        custom_prompt_system=webhook.custom_prompt_system,
        custom_prompt_user=webhook.custom_prompt_user,
        review_style=webhook.review_style,
        gitlab_token=webhook.gitlab_token,
        daily_report_enabled=webhook.daily_report_enabled,
        supported_extensions=webhook.supported_extensions
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建配置失败"
        )
    
    # 返回刚创建的配置
    configs = WebhookService.get_all_branch_webhook_configs()
    for item in configs:
        if (item.get('gitlab_base_url') == webhook.gitlab_base_url and 
            item.get('project_slug') == webhook.project_slug and 
            item.get('branch_pattern') == webhook.branch_pattern):
            return item
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="创建配置失败"
    )


@router.put("/{config_id}", response_model=BranchWebhookResponse)
async def update_branch_webhook(config_id: int, webhook: BranchWebhookUpdate, current_user: str = Depends(get_current_user)):
    """更新分支配置"""
    # 检查冲突
    conflicts = []
    all_m = WebhookService.get_all_branch_webhook_configs()
    
    for m in all_m:
        if m.get('id') == config_id:
            continue
        if (webhook.gitlab_base_url and webhook.project_slug and webhook.branch_pattern and
            m.get('gitlab_base_url') == webhook.gitlab_base_url and 
            m.get('project_slug') == webhook.project_slug and 
            m.get('branch_pattern') == webhook.branch_pattern):
            conflicts.append("冲突: 存在相同的分支配置")
    
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=conflicts
        )
    
    result = WebhookService.update_branch_webhook_config_by_id(
        config_id,
        gitlab_base_url=webhook.gitlab_base_url,
        project_slug=webhook.project_slug,
        branch_pattern=webhook.branch_pattern,
        dingtalk_url=webhook.dingtalk_url,
        feishu_url=webhook.feishu_url,
        wecom_url=webhook.wecom_url,
        dingtalk_enabled=webhook.dingtalk_enabled,
        feishu_enabled=webhook.feishu_enabled,
        wecom_enabled=webhook.wecom_enabled,
        custom_prompt_system=webhook.custom_prompt_system,
        custom_prompt_user=webhook.custom_prompt_user,
        review_style=webhook.review_style,
        gitlab_token=webhook.gitlab_token,
        daily_report_enabled=webhook.daily_report_enabled,
        supported_extensions=webhook.supported_extensions
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"配置 {config_id} 不存在或更新失败"
        )
    
    # 返回更新后的数据
    updated = WebhookService.get_all_branch_webhook_configs()
    for item in updated:
        if item.get('id') == config_id:
            return item
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"配置 {config_id} 不存在"
    )


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branch_webhook(config_id: int, current_user: str = Depends(get_current_user)):
    """删除分支配置"""
    WebhookService.delete_branch_webhook_config(config_id)
    return None


def get_branch_for_log(log: dict) -> str:
    """从日志中获取分支名称"""
    if 'source_branch' in log and log['source_branch']:
        return log['source_branch']  # MR log
    elif 'branch' in log and log['branch']:
        return log['branch']  # Push log
    return None


@router.post("/{config_id}/send-daily-report", status_code=status.HTTP_200_OK)
async def send_branch_daily_report(config_id: int, current_user: str = Depends(get_current_user)):
    """为指定分支配置发送日报"""
    logger.info(f"📋 开始为分支配置 {config_id} 发送日报")
    
    # 获取分支配置
    all_configs = WebhookService.get_all_branch_webhook_configs()
    config = None
    for c in all_configs:
        if c.get('id') == config_id:
            config = c
            break
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"分支配置 {config_id} 不存在"
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
    
    gitlab_base_url = config.get('gitlab_base_url')
    project_slug = config.get('project_slug')
    branch_pattern = config.get('branch_pattern')
    
    # 筛选项目日志
    filtered_logs = []
    for log in logs:
        if log.get('gitlab_base_url') == gitlab_base_url and log.get('project_slug') == project_slug:
            branch_name = get_branch_for_log(log)
            if branch_name:
                # 检查分支是否匹配模式
                if fnmatch.fnmatch(branch_name, branch_pattern):
                    filtered_logs.append(log)
    
    logger.info(f"📋 筛选后共有 {len(filtered_logs)} 条记录")
    
    if not filtered_logs:
        logger.info("⚠️ 该分支当日无审查数据")
        return {"message": "该分支当日无审查数据", "count": 0}
    
    # 检查配置的日报开关
    if config.get('daily_report_enabled') is not True:
        logger.info(f"⏭️ 该分支未启用日报 (daily_report_enabled={config.get('daily_report_enabled')})")
    
    # 去重：基于 (author, message) 组合
    df_filtered = pd.DataFrame(filtered_logs)
    df_unique = df_filtered.drop_duplicates(subset=["author", "commit_messages"])
    df_sorted = df_unique.sort_values(by="author")
    commits = df_sorted.to_dict(orient="records")
    
    # 生成日报内容
    title_prefix = f"项目:{project_slug} 分支:{branch_pattern}"
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
