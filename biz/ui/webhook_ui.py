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


def render_webhook_management():
    st.header("项目配置管理")

    # 列出当前映射
    mappings = WebhookService.get_all_webhook_mappings()
    if mappings:
        try:
            df = pd.DataFrame(mappings)
            # 显示主要字段
            display_cols = ['id', 'project_name', 'url_slug', 'dingtalk_url', 'feishu_url', 'wecom_url']
            st.dataframe(df[display_cols])
        except Exception:
            st.write(mappings)
    else:
        st.info("目前没有配置任何项目")

    st.markdown("---")

    # 创建新映射的表单
    with st.form("create_webhook_form"):
        st.subheader("新建 / 更新 项目配置（按 project_name 或 url_slug 匹配）")
        project_name = st.text_input("项目名称 (project_name)")
        url_slug = st.text_input("URL Slug (url_slug)")
        
        st.markdown("### Webhook 配置")
        dingtalk_url = st.text_input("DingTalk Webhook URL")
        feishu_url = st.text_input("Feishu Webhook URL")
        wecom_url = st.text_input("WeCom Webhook URL")
        
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
            # 基本校验：必须提供 project_name 或 url_slug
            if not project_name and not url_slug:
                st.error("请至少填写 Project Name 或 URL Slug 中的一个以便匹配项目")
            else:
                # 前端重复检测（避免提交后回退）
                existing = WebhookService.get_all_webhook_mappings()
                dup_errors = []
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
                        project_name=project_name or None,
                        url_slug=url_slug or None,
                        dingtalk_url=dingtalk_url or None,
                        feishu_url=feishu_url or None,
                        wecom_url=wecom_url or None,
                        custom_prompt_system=custom_prompt_system or None,
                        custom_prompt_user=custom_prompt_user or None
                    )
                    if mapping:
                        st.success("保存成功")
                        st.experimental_rerun()
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
            project_name = st.text_input("项目名称 (project_name)", value=curr.get('project_name') or '')
            url_slug = st.text_input("URL Slug (url_slug)", value=curr.get('url_slug') or '')
            
            st.markdown("### Webhook 配置")
            dingtalk_url = st.text_input("DingTalk Webhook URL", value=curr.get('dingtalk_url') or '')
            feishu_url = st.text_input("Feishu Webhook URL", value=curr.get('feishu_url') or '')
            wecom_url = st.text_input("WeCom Webhook URL", value=curr.get('wecom_url') or '')
            
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
                        project_name=project_name or None,
                        url_slug=url_slug or None,
                        dingtalk_url=dingtalk_url or None,
                        feishu_url=feishu_url or None,
                        wecom_url=wecom_url or None,
                        custom_prompt_system=custom_prompt_system or None,
                        custom_prompt_user=custom_prompt_user or None
                    )
                    if ok:
                        st.success("更新成功")
                    else:
                        st.error("更新失败：未找到该配置或数据库错误")
                    st.experimental_rerun()
            if delete_btn:
                # 二次确认删除
                confirm = st.checkbox("确认删除此配置？勾选后点击下面的确认删除按钮")
                if confirm:
                    if st.button("确认删除", key=f"confirm_delete_{selected_id}"):
                        WebhookService.delete_webhook_mapping(selected_id)
                        st.success("删除成功")
                        st.experimental_rerun()
    else:
        st.info("暂无可编辑的配置")
