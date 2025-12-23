from flask import Blueprint, request, jsonify
import os
from functools import wraps

from biz.service.webhook_service import WebhookService
from biz.service.branch_webhook_service import BranchWebhookService
from biz.utils.log import logger

admin_bp = Blueprint('admin', __name__)


def require_basic_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        username = os.environ.get('DASHBOARD_USER', 'admin')
        password = os.environ.get('DASHBOARD_PASSWORD', 'admin')
        if not auth or auth.username != username or auth.password != password:
            return jsonify({'message': 'Authentication required'}), 401, {'WWW-Authenticate': 'Basic realm="Login Required"'}
        return f(*args, **kwargs)

    return decorated


@admin_bp.route('/admin/webhooks', methods=['GET'])
@require_basic_auth
def list_webhooks():
    mappings = WebhookService.get_all_webhook_mappings()
    return jsonify({'data': mappings})


@admin_bp.route('/admin/webhooks', methods=['POST'])
@require_basic_auth
def create_webhook():
    data = request.get_json() or {}
    project_name = data.get('project_name')
    url_slug = data.get('url_slug')
    dingtalk_url = data.get('dingtalk_url')
    feishu_url = data.get('feishu_url')
    wecom_url = data.get('wecom_url')
    mapping = WebhookService.create_or_update_webhook_mapping(project_name=project_name, url_slug=url_slug,
                                                   dingtalk_url=dingtalk_url, feishu_url=feishu_url, wecom_url=wecom_url)
    if mapping:
        return jsonify({'message': 'ok', 'data': mapping}), 201
    else:
        return jsonify({'message': 'error creating mapping'}), 500


@admin_bp.route('/admin/webhooks/<int:mapping_id>', methods=['PUT'])
@require_basic_auth
def update_webhook(mapping_id):
    data = request.get_json() or {}
    project_name = data.get('project_name')
    url_slug = data.get('url_slug')
    dingtalk_url = data.get('dingtalk_url')
    feishu_url = data.get('feishu_url')
    wecom_url = data.get('wecom_url')
    ok = WebhookService.update_webhook_mapping_by_id(mapping_id, project_name=project_name, url_slug=url_slug,
                                                   dingtalk_url=dingtalk_url, feishu_url=feishu_url, wecom_url=wecom_url)
    if not ok:
        return jsonify({'message': 'not found'}), 404
    return jsonify({'message': 'ok'})


@admin_bp.route('/admin/webhooks/<int:mapping_id>', methods=['DELETE'])
@require_basic_auth
def delete_webhook(mapping_id):
    WebhookService.delete_webhook_mapping(mapping_id)
    return jsonify({'message': 'ok'})


# ==================== 分支级 Webhook 配置 API ====================

@admin_bp.route('/admin/branch-webhooks', methods=['GET'])
@require_basic_auth
def list_branch_webhooks():
    """获取所有分支级webhook配置"""
    gitlab_base_url = request.args.get('gitlab_base_url')
    project_slug = request.args.get('project_slug')
    
    mappings = BranchWebhookService.get_all_branch_webhooks(
        gitlab_base_url=gitlab_base_url,
        project_slug=project_slug
    )
    return jsonify({'data': mappings})


@admin_bp.route('/admin/branch-webhooks', methods=['POST'])
@require_basic_auth
def create_branch_webhook():
    """创建或更新分支级webhook配置"""
    data = request.get_json() or {}
    gitlab_base_url = data.get('gitlab_base_url')
    project_slug = data.get('project_slug')
    branch_pattern = data.get('branch_pattern')
    dingtalk_url = data.get('dingtalk_url')
    feishu_url = data.get('feishu_url')
    wecom_url = data.get('wecom_url')
    custom_prompt_system = data.get('custom_prompt_system')
    custom_prompt_user = data.get('custom_prompt_user')
    
    if not gitlab_base_url or not project_slug or not branch_pattern:
        return jsonify({'message': 'gitlab_base_url, project_slug, and branch_pattern are required'}), 400
    
    mapping = BranchWebhookService.create_or_update_branch_webhook(
        gitlab_base_url=gitlab_base_url,
        project_slug=project_slug,
        branch_pattern=branch_pattern,
        dingtalk_url=dingtalk_url,
        feishu_url=feishu_url,
        wecom_url=wecom_url,
        custom_prompt_system=custom_prompt_system,
        custom_prompt_user=custom_prompt_user
    )
    
    if mapping:
        return jsonify({'message': 'ok', 'data': mapping}), 201
    else:
        return jsonify({'message': 'error creating branch webhook mapping'}), 500


@admin_bp.route('/admin/branch-webhooks/<int:webhook_id>', methods=['PUT'])
@require_basic_auth
def update_branch_webhook(webhook_id):
    """更新指定的分支级webhook配置"""
    data = request.get_json() or {}
    gitlab_base_url = data.get('gitlab_base_url')
    project_slug = data.get('project_slug')
    branch_pattern = data.get('branch_pattern')
    dingtalk_url = data.get('dingtalk_url')
    feishu_url = data.get('feishu_url')
    wecom_url = data.get('wecom_url')
    custom_prompt_system = data.get('custom_prompt_system')
    custom_prompt_user = data.get('custom_prompt_user')
    
    ok = BranchWebhookService.update_branch_webhook_by_id(
        webhook_id=webhook_id,
        gitlab_base_url=gitlab_base_url,
        project_slug=project_slug,
        branch_pattern=branch_pattern,
        dingtalk_url=dingtalk_url,
        feishu_url=feishu_url,
        wecom_url=wecom_url,
        custom_prompt_system=custom_prompt_system,
        custom_prompt_user=custom_prompt_user
    )
    
    if not ok:
        return jsonify({'message': 'not found'}), 404
    return jsonify({'message': 'ok'})


@admin_bp.route('/admin/branch-webhooks/<int:webhook_id>', methods=['DELETE'])
@require_basic_auth
def delete_branch_webhook(webhook_id):
    """删除指定的分支级webhook配置"""
    BranchWebhookService.delete_branch_webhook(webhook_id)
    return jsonify({'message': 'ok'})
