"""
项目配置 Webhook API
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from biz.service.webhook_service import WebhookService
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
        gitlab_token=webhook.gitlab_token
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
        gitlab_token=webhook.gitlab_token
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
