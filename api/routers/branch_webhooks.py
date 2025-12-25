"""
分支配置 Webhook API
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from biz.service.webhook_service import WebhookService
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
    gitlab_token: Optional[str] = None


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
    gitlab_token: Optional[str] = None


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
    gitlab_token: Optional[str] = None
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
        gitlab_token=webhook.gitlab_token
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
        gitlab_token=webhook.gitlab_token
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
