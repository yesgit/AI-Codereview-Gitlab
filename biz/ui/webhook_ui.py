import streamlit as st
import pandas as pd
import urllib.parse
import yaml
import os

from biz.service.webhook_service import WebhookService


def _load_default_prompts():
    """加载默认的 prompt 模板"""
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'conf', 'prompt_templates.yml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            code_review = config.get('code_review_prompt', {})
            return {
                'system': code_review.get('system_prompt', ''),
                'user': code_review.get('user_prompt', '')
            }
    except Exception as e:
        st.error(f"加载默认提示词失败: {e}")
        return {'system': '', 'user': ''}


def _is_valid_url(u: str) -> bool:
    if not u:
        return False
    try:
        p = urllib.parse.urlparse(u)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


def _mask_token(token: str) -> str:
    """掩码显示 token，只显示前4位和后4位"""
    if not token or len(token) <= 8:
        return "****"
    return f"{token[:4]}{'*' * (len(token) - 8)}{token[-4:]}"


def render_webhook_management():
    st.header("项目配置管理")

    # 列出当前映射
    mappings = WebhookService.get_all_webhook_mappings()
    if mappings:
        try:
            df = pd.DataFrame(mappings)
            # 显示主要字段
            display_cols = ['id', 'gitlab_base_url', 'project_slug', 'project_name', 'url_slug', 'dingtalk_url', 'feishu_url', 'wecom_url']
            # 只显示存在的列
            available_cols = [col for col in display_cols if col in df.columns]
            st.dataframe(df[available_cols])
        except Exception:
            st.write(mappings)
    else:
        st.info("目前没有配置任何项目")

    st.markdown("---")

    # 创建新映射的表单
    with st.form("create_webhook_form"):
        st.subheader("新建项目配置")
        
        st.markdown("### 项目标识")
        gitlab_base_url = st.text_input("GitLab Base URL (例如: https://gitlab.example.com)")
        project_slug = st.text_input("项目 Slug (例如: group/project)")
        project_name = st.text_input("项目名称 (project_name，可选)")
        url_slug = st.text_input("URL Slug (url_slug，可选)")
        
        st.markdown("### Webhook 配置")
        dingtalk_url = st.text_input("DingTalk Webhook URL")
        feishu_url = st.text_input("Feishu Webhook URL")
        wecom_url = st.text_input("WeCom Webhook URL")
        
        st.markdown("### GitLab 访问令牌（可选）")
        st.info("💡 提示：配置项目专属的 GitLab Token，用于访问私有仓库。留空则使用系统级配置。")
        gitlab_token = st.text_input("GitLab Token", type="password", placeholder="glpat-xxxxxxxxxxxxxxxxxxxx")
        
        st.markdown("### 自定义 Prompt 配置（可选）")
        st.info("💡 提示：下方显示的是系统默认提示词，您可以修改后保存为项目专属提示词。留空则使用默认配置。")
        
        # 加载默认提示词
        default_prompts = _load_default_prompts()
        
        custom_prompt_system = st.text_area(
            "System Prompt (系统提示词)",
            value=default_prompts['system'],
            height=200
        )
        custom_prompt_user = st.text_area(
            "User Prompt (用户提示词)",
            value=default_prompts['user'],
            height=200
        )
        
        submitted = st.form_submit_button("保存配置")
        if submitted:
            # 基本校验：必须提供 gitlab_base_url + project_slug，或者 project_name，或者 url_slug
            if not gitlab_base_url and not project_slug and not project_name and not url_slug:
                st.error("请至少填写以下之一：\n- GitLab Base URL + 项目 Slug\n- Project Name\n- URL Slug")
            elif (gitlab_base_url and not project_slug) or (not gitlab_base_url and project_slug):
                st.error("GitLab Base URL 和项目 Slug 必须同时填写")
            else:
                # 前端重复检测
                existing = WebhookService.get_all_webhook_mappings()
                dup_errors = []
                if gitlab_base_url and project_slug:
                    for m in existing:
                        if m.get('gitlab_base_url') == gitlab_base_url and m.get('project_slug') == project_slug:
                            dup_errors.append(f"已存在相同的 gitlab_base_url + project_slug: {gitlab_base_url} / {project_slug} (id={m.get('id')})")
                            break
                if project_name:
                    for m in existing:
                        if m.get('project_name') == project_name:
                            dup_errors.append(f"已存在相同的 project_name: {project_name} (id={m.get('id')})")
                            break
                if url_slug:
                    for m in existing:
                        if m.get('url_slug') == url_slug:
                            dup_errors.append(f"已存在相同的 url_slug: {url_slug} (id={m.get('id')})")
                            break
                if dup_errors:
                    for e in dup_errors:
                        st.error(e)
                    st.info("如确实要更新该配置，请在 编辑 区选择对应 ID 并使用 更新 操作；或先删除旧的配置。")
                    st.stop()
                # 校验 URL 格式
                bad_urls = []
                for name, val in (('DingTalk', dingtalk_url), ('Feishu', feishu_url), ('WeCom', wecom_url)):
                    if val and not _is_valid_url(val):
                        bad_urls.append(f"{name} URL 无效")
                if bad_urls:
                    for m in bad_urls:
                        st.error(m)
                else:
                    mapping = WebhookService.create_or_update_webhook_mapping(
                        gitlab_base_url=gitlab_base_url or None,
                        project_slug=project_slug or None,
                        project_name=project_name or None,
                        url_slug=url_slug or None,
                        dingtalk_url=dingtalk_url or None,
                        feishu_url=feishu_url or None,
                        wecom_url=wecom_url or None,
                        custom_prompt_system=custom_prompt_system or None,
                        custom_prompt_user=custom_prompt_user or None,
                        gitlab_token=gitlab_token or None
                    )
                    if mapping:
                        st.success("保存成功")
                        st.rerun()
                    else:
                        st.error("保存失败：可能存在冲突或数据库约束。请查看日志或使用 编辑 区进行更新/删除操作。")

    st.markdown("---")

    # 编辑 / 删除 已有映射
    st.subheader("编辑 / 删除 项目配置")
    mappings = WebhookService.get_all_webhook_mappings()
    id_map = {m.get('id') if isinstance(m, dict) else m[0]: m for m in mappings} if mappings else {}
    if id_map:
        selected_id = st.selectbox("选择配置 ID", options=sorted(list(id_map.keys())))
        mapping = id_map.get(selected_id)
        # 支持 dict 或 tuple 映射
        if isinstance(mapping, dict):
            curr = mapping
        else:
            # tuple/list
            curr = {
                'id': mapping[0],
                'project_name': mapping[1],
                'url_slug': mapping[2],
                'dingtalk_url': mapping[3],
                'feishu_url': mapping[4],
                'wecom_url': mapping[5]
            }

        with st.form("edit_webhook_form"):
            st.markdown("### 项目标识")
            gitlab_base_url = st.text_input("GitLab Base URL", value=curr.get('gitlab_base_url') or '')
            project_slug = st.text_input("项目 Slug", value=curr.get('project_slug') or '')
            project_name = st.text_input("项目名称 (project_name，可选)", value=curr.get('project_name') or '')
            url_slug = st.text_input("URL Slug (url_slug，可选)", value=curr.get('url_slug') or '')
            
            st.markdown("### Webhook 配置")
            dingtalk_url = st.text_input("DingTalk Webhook URL", value=curr.get('dingtalk_url') or '')
            feishu_url = st.text_input("Feishu Webhook URL", value=curr.get('feishu_url') or '')
            wecom_url = st.text_input("WeCom Webhook URL", value=curr.get('wecom_url') or '')
            
            st.markdown("### GitLab 访问令牌（可选）")
            current_token = curr.get('gitlab_token') or ''
            if current_token:
                st.info(f"当前 Token: {_mask_token(current_token)}")
            st.info("💡 提示：留空保持不变，输入新值则更新，如需清空请输入单个空格")
            gitlab_token_input = st.text_input("GitLab Token", type="password", placeholder="留空保持不变")
            # 处理 token 输入：如果是单个空格则清空，如果留空则保持原值，否则使用新值
            if gitlab_token_input == ' ':
                gitlab_token = None
            elif gitlab_token_input:
                gitlab_token = gitlab_token_input
            else:
                gitlab_token = current_token
            
            st.markdown("### 自定义 Prompt 配置（可选）")
            st.info("💡 提示：如未配置自定义提示词，下方将显示系统默认提示词。您可以修改后保存为项目专属提示词。")
            
            # 加载默认提示词，如果数据库中没有自定义提示词，则使用默认值
            default_prompts = _load_default_prompts()
            
            custom_prompt_system = st.text_area(
                "System Prompt (系统提示词)",
                value=curr.get('custom_prompt_system') or default_prompts['system'],
                height=200
            )
            custom_prompt_user = st.text_area(
                "User Prompt (用户提示词)",
                value=curr.get('custom_prompt_user') or default_prompts['user'],
                height=200
            )
            
            update_btn, delete_btn = st.form_submit_button("更新配置"), st.form_submit_button("删除配置")
            if update_btn:
                # 更新前检查冲突（除当前记录外）
                conflicts = []
                all_m = WebhookService.get_all_webhook_mappings()
                for m in all_m:
                    if m.get('id') == selected_id:
                        continue
                    if gitlab_base_url and project_slug and m.get('gitlab_base_url') == gitlab_base_url and m.get('project_slug') == project_slug:
                        conflicts.append(f"冲突: 存在相同 gitlab_base_url + project_slug (id={m.get('id')})")
                    if project_name and m.get('project_name') == project_name:
                        conflicts.append(f"冲突: 存在相同 project_name (id={m.get('id')})")
                    if url_slug and m.get('url_slug') == url_slug:
                        conflicts.append(f"冲突: 存在相同 url_slug (id={m.get('id')})")
                if conflicts:
                    for c in conflicts:
                        st.error(c)
                    st.info("解决冲突后重试，或先删除冲突的记录。")
                else:
                    ok = WebhookService.update_webhook_mapping_by_id(
                        selected_id,
                        gitlab_base_url=gitlab_base_url or None,
                        project_slug=project_slug or None,
                        project_name=project_name or None,
                        url_slug=url_slug or None,
                        dingtalk_url=dingtalk_url or None,
                        feishu_url=feishu_url or None,
                        wecom_url=wecom_url or None,
                        custom_prompt_system=custom_prompt_system or None,
                        custom_prompt_user=custom_prompt_user or None,
                        gitlab_token=gitlab_token or None
                    )
                    if ok:
                        st.success("更新成功")
                    else:
                        st.error("更新失败：未找到该配置或数据库错误")
                    st.rerun()
            if delete_btn:
                # 二次确认删除
                confirm = st.checkbox("确认删除此配置？勾选后点击下面的确认删除按钮")
                if confirm:
                    if st.button("确认删除", key=f"confirm_delete_{selected_id}"):
                        WebhookService.delete_webhook_mapping(selected_id)
                        st.success("删除成功")
                        st.rerun()
    else:
        st.info("暂无可编辑的配置")


def render_branch_webhook_management():
    """分支级配置管理界面"""
    st.header("分支配置管理")
    
    from biz.service.webhook_service import WebhookService
    
    # 列出当前分支配置
    branch_configs = WebhookService.get_all_branch_webhook_configs()
    if branch_configs:
        try:
            df = pd.DataFrame(branch_configs)
            display_cols = ['id', 'gitlab_base_url', 'project_slug', 'branch_pattern', 'dingtalk_url', 'feishu_url', 'wecom_url']
            available_cols = [col for col in display_cols if col in df.columns]
            st.dataframe(df[available_cols])
        except Exception:
            st.write(branch_configs)
    else:
        st.info("目前没有配置任何分支规则")
    
    st.markdown("---")
    
    # 创建新分支配置
    with st.form("create_branch_webhook_form"):
        st.subheader("新建分支配置")
        
        st.markdown("### 分支匹配规则")
        st.info("💡 提示：branch_pattern 支持通配符，例如 `feature/*`、`main`、`release/*` 等")
        
        gitlab_base_url = st.text_input("GitLab Base URL (必填)", placeholder="https://gitlab.example.com")
        project_slug = st.text_input("项目 Slug (必填)", placeholder="group/project")
        branch_pattern = st.text_input("分支模式 (必填)", placeholder="feature/* 或 main")
        
        st.markdown("### Webhook 配置")
        dingtalk_url = st.text_input("DingTalk Webhook URL")
        feishu_url = st.text_input("Feishu Webhook URL")
        wecom_url = st.text_input("WeCom Webhook URL")
        
        st.markdown("### GitLab 访问令牌（可选）")
        st.info("💡 提示：配置分支专属的 GitLab Token。留空则使用项目级或系统级配置。")
        gitlab_token = st.text_input("GitLab Token", type="password", placeholder="glpat-xxxxxxxxxxxxxxxxxxxx", key="branch_create_token")
        
        st.markdown("### 自定义 Prompt 配置（可选）")
        st.info("💡 提示：下方显示的是系统默认提示词，您可以修改后保存为分支专属提示词。留空则使用项目级或系统级配置。")
        
        default_prompts = _load_default_prompts()
        
        custom_prompt_system = st.text_area(
            "System Prompt (系统提示词)",
            value=default_prompts['system'],
            height=200
        )
        custom_prompt_user = st.text_area(
            "User Prompt (用户提示词)",
            value=default_prompts['user'],
            height=200
        )
        
        submitted = st.form_submit_button("保存配置")
        if submitted:
            # 基本校验
            if not gitlab_base_url or not project_slug or not branch_pattern:
                st.error("GitLab Base URL、项目 Slug 和分支模式都是必填项")
            else:
                # 检查是否已存在相同配置
                existing = WebhookService.get_all_branch_webhook_configs()
                dup_found = False
                for m in existing:
                    if (m.get('gitlab_base_url') == gitlab_base_url and 
                        m.get('project_slug') == project_slug and 
                        m.get('branch_pattern') == branch_pattern):
                        st.error(f"已存在相同的分支配置: {gitlab_base_url} / {project_slug} / {branch_pattern} (id={m.get('id')})")
                        dup_found = True
                        break
                
                if not dup_found:
                    # 校验 URL 格式
                    bad_urls = []
                    for name, val in (('DingTalk', dingtalk_url), ('Feishu', feishu_url), ('WeCom', wecom_url)):
                        if val and not _is_valid_url(val):
                            bad_urls.append(f"{name} URL 无效")
                    
                    if bad_urls:
                        for m in bad_urls:
                            st.error(m)
                    else:
                        mapping = WebhookService.create_branch_webhook_config(
                            gitlab_base_url=gitlab_base_url,
                            project_slug=project_slug,
                            branch_pattern=branch_pattern,
                            dingtalk_url=dingtalk_url or None,
                            feishu_url=feishu_url or None,
                            wecom_url=wecom_url or None,
                            custom_prompt_system=custom_prompt_system or None,
                            custom_prompt_user=custom_prompt_user or None,
                            gitlab_token=gitlab_token or None
                        )
                        if mapping:
                            st.success("保存成功")
                            st.rerun()
                        else:
                            st.error("保存失败，请查看日志")
    
    st.markdown("---")
    
    # 编辑 / 删除分支配置
    st.subheader("编辑 / 删除 分支配置")
    branch_configs = WebhookService.get_all_branch_webhook_configs()
    id_map = {m.get('id') if isinstance(m, dict) else m[0]: m for m in branch_configs} if branch_configs else {}
    
    if id_map:
        selected_id = st.selectbox("选择配置 ID", options=sorted(list(id_map.keys())))
        mapping = id_map.get(selected_id)
        
        if isinstance(mapping, dict):
            curr = mapping
        else:
            curr = {
                'id': mapping[0],
                'gitlab_base_url': mapping[1],
                'project_slug': mapping[2],
                'branch_pattern': mapping[3],
                'dingtalk_url': mapping[4],
                'feishu_url': mapping[5],
                'wecom_url': mapping[6]
            }
        
        with st.form("edit_branch_webhook_form"):
            st.markdown("### 分支匹配规则")
            gitlab_base_url = st.text_input("GitLab Base URL", value=curr.get('gitlab_base_url') or '')
            project_slug = st.text_input("项目 Slug", value=curr.get('project_slug') or '')
            branch_pattern = st.text_input("分支模式", value=curr.get('branch_pattern') or '')
            
            st.markdown("### Webhook 配置")
            dingtalk_url = st.text_input("DingTalk Webhook URL", value=curr.get('dingtalk_url') or '')
            feishu_url = st.text_input("Feishu Webhook URL", value=curr.get('feishu_url') or '')
            wecom_url = st.text_input("WeCom Webhook URL", value=curr.get('wecom_url') or '')
            
            st.markdown("### GitLab 访问令牌（可选）")
            current_token = curr.get('gitlab_token') or ''
            if current_token:
                st.info(f"当前 Token: {_mask_token(current_token)}")
            st.info("💡 提示：留空保持不变，输入新值则更新，如需清空请输入单个空格")
            gitlab_token_input = st.text_input("GitLab Token", type="password", placeholder="留空保持不变", key="branch_edit_token")
            # 处理 token 输入
            if gitlab_token_input == ' ':
                gitlab_token = None
            elif gitlab_token_input:
                gitlab_token = gitlab_token_input
            else:
                gitlab_token = current_token
            
            st.markdown("### 自定义 Prompt 配置（可选）")
            st.info("💡 提示：如未配置自定义提示词，下方将显示系统默认提示词。")
            
            default_prompts = _load_default_prompts()
            
            custom_prompt_system = st.text_area(
                "System Prompt (系统提示词)",
                value=curr.get('custom_prompt_system') or default_prompts['system'],
                height=200
            )
            custom_prompt_user = st.text_area(
                "User Prompt (用户提示词)",
                value=curr.get('custom_prompt_user') or default_prompts['user'],
                height=200
            )
            
            update_btn, delete_btn = st.form_submit_button("更新配置"), st.form_submit_button("删除配置")
            
            if update_btn:
                # 检查冲突
                conflicts = []
                all_m = WebhookService.get_all_branch_webhook_configs()
                for m in all_m:
                    if m.get('id') == selected_id:
                        continue
                    if (m.get('gitlab_base_url') == gitlab_base_url and 
                        m.get('project_slug') == project_slug and 
                        m.get('branch_pattern') == branch_pattern):
                        conflicts.append(f"冲突: 存在相同的分支配置 (id={m.get('id')})")
                
                if conflicts:
                    for c in conflicts:
                        st.error(c)
                else:
                    ok = WebhookService.update_branch_webhook_config_by_id(
                        selected_id,
                        gitlab_base_url=gitlab_base_url or None,
                        project_slug=project_slug or None,
                        branch_pattern=branch_pattern or None,
                        dingtalk_url=dingtalk_url or None,
                        feishu_url=feishu_url or None,
                        wecom_url=wecom_url or None,
                        custom_prompt_system=custom_prompt_system or None,
                        custom_prompt_user=custom_prompt_user or None,
                        gitlab_token=gitlab_token or None
                    )
                    if ok:
                        st.success("更新成功")
                    else:
                        st.error("更新失败")
                    st.rerun()
            
            if delete_btn:
                confirm = st.checkbox("确认删除此配置？勾选后点击下面的确认删除按钮")
                if confirm:
                    if st.button("确认删除", key=f"confirm_delete_branch_{selected_id}"):
                        WebhookService.delete_branch_webhook_config(selected_id)
                        st.success("删除成功")
                        st.rerun()
    else:
        st.info("暂无可编辑的配置")
