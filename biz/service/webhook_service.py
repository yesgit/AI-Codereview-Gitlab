"""Webhook 配置管理服务：负责项目级 IM webhook 的增删改查。
封装 DB 访问，供 API、通知器调用。
"""
import os
import time
import traceback
from typing import Optional

from sqlalchemy import text

from biz.utils.db import get_engine
from biz.utils.log import logger


class WebhookService:
    @staticmethod
    def init_db():
        try:
            engine = get_engine()
            from sqlalchemy import MetaData, Table, Column, Integer, String, Text, Boolean, UniqueConstraint

            metadata = MetaData()
            Table(
                'project_webhooks', metadata,
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('project_name', String(255), unique=True),
                Column('url_slug', String(255), unique=True),
                Column('gitlab_base_url', String(255)),
                Column('project_slug', String(255)),
                Column('dingtalk_url', Text),
                Column('feishu_url', Text),
                Column('wecom_url', Text),
                Column('custom_prompt_system', Text),
                Column('custom_prompt_user', Text),
                Column('gitlab_token', Text),
                Column('dingtalk_enabled', Boolean, default=True),
                Column('feishu_enabled', Boolean, default=True),
                Column('wecom_enabled', Boolean, default=True),
                Column('review_style', String(50)),
                Column('daily_report_enabled', Boolean, default=True),
                Column('supported_extensions', Text),
                Column('created_at', Integer),
                Column('updated_at', Integer),
            )
            metadata.create_all(engine)
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")

    @staticmethod
    def create_or_update_webhook_mapping(project_name: Optional[str] = None, url_slug: Optional[str] = None,
                                         gitlab_base_url: Optional[str] = None, project_slug: Optional[str] = None,
                                         dingtalk_url: Optional[str] = None, feishu_url: Optional[str] = None,
                                         wecom_url: Optional[str] = None, custom_prompt_system: Optional[str] = None,
                                         custom_prompt_user: Optional[str] = None, gitlab_token: Optional[str] = None,
                                         dingtalk_enabled: Optional[bool] = None, feishu_enabled: Optional[bool] = None,
                                         wecom_enabled: Optional[bool] = None, review_style: Optional[str] = None,
                                         daily_report_enabled: Optional[bool] = None,
                                         supported_extensions: Optional[str] = None):
        try:
            now = int(time.time())
            engine = get_engine()
            # Check duplicates: ensure project_name and url_slug are unique
            sel_by_project = text('SELECT id, project_name, url_slug FROM project_webhooks WHERE project_name = :project_name LIMIT 1')
            sel_by_slug = text('SELECT id, project_name, url_slug FROM project_webhooks WHERE url_slug = :url_slug LIMIT 1')
            sel_by_gitlab = text('SELECT id, project_name, url_slug FROM project_webhooks WHERE gitlab_base_url = :gitlab_base_url AND project_slug = :project_slug LIMIT 1')
            ins = text('''INSERT INTO project_webhooks (project_name, url_slug, gitlab_base_url, project_slug, dingtalk_url, feishu_url, wecom_url, custom_prompt_system, custom_prompt_user, gitlab_token, dingtalk_enabled, feishu_enabled, wecom_enabled, review_style, daily_report_enabled, supported_extensions, created_at, updated_at)
                         VALUES (:project_name, :url_slug, :gitlab_base_url, :project_slug, :dingtalk_url, :feishu_url, :wecom_url, :custom_prompt_system, :custom_prompt_user, :gitlab_token, :dingtalk_enabled, :feishu_enabled, :wecom_enabled, :review_style, :daily_report_enabled, :supported_extensions, :created_at, :updated_at)''')
            upd = text('''UPDATE project_webhooks SET project_name = :project_name, url_slug = :url_slug, gitlab_base_url = :gitlab_base_url, project_slug = :project_slug, dingtalk_url = :dingtalk_url, feishu_url = :feishu_url, wecom_url = :wecom_url, custom_prompt_system = :custom_prompt_system, custom_prompt_user = :custom_prompt_user, gitlab_token = :gitlab_token, dingtalk_enabled = :dingtalk_enabled, feishu_enabled = :feishu_enabled, wecom_enabled = :wecom_enabled, review_style = :review_style, daily_report_enabled = :daily_report_enabled, supported_extensions = :supported_extensions, updated_at = :updated_at WHERE id = :id''')
            sel_by_id = text('SELECT id, project_name, url_slug, gitlab_base_url, project_slug, dingtalk_url, feishu_url, wecom_url, dingtalk_enabled, feishu_enabled, wecom_enabled, custom_prompt_system, custom_prompt_user, review_style, daily_report_enabled, supported_extensions, gitlab_token, created_at, updated_at FROM project_webhooks WHERE id = :id LIMIT 1')
            
            with engine.begin() as conn:
                existing_project = None
                existing_slug = None
                existing_gitlab = None
                
                if project_name:
                    r = conn.execute(sel_by_project, {'project_name': project_name})
                    existing_project = r.mappings().first()
                if url_slug:
                    r = conn.execute(sel_by_slug, {'url_slug': url_slug})
                    existing_slug = r.mappings().first()
                if gitlab_base_url and project_slug:
                    r = conn.execute(sel_by_gitlab, {'gitlab_base_url': gitlab_base_url, 'project_slug': project_slug})
                    existing_gitlab = r.mappings().first()

                # Determine action: update existing (if same record) or insert.
                mapping_id = None
                
                if existing_gitlab:
                    # Found by gitlab_base_url + project_slug
                    # Check for conflicts with other records
                    if (existing_project and existing_project['id'] != existing_gitlab['id']) or \
                       (existing_slug and existing_slug['id'] != existing_gitlab['id']):
                        logger.error("Duplicate mapping exists for project_name or url_slug")
                        return None
                    mapping_id = existing_gitlab['id']
                elif existing_project and existing_slug:
                    # both exist
                    if existing_project['id'] != existing_slug['id']:
                        logger.error("Duplicate mapping exists for project_name or url_slug")
                        return None
                    mapping_id = existing_project['id']
                elif existing_project:
                    # update same record by project
                    mapping_id = existing_project['id']
                elif existing_slug:
                    # update same record by slug
                    mapping_id = existing_slug['id']
                
                if mapping_id:
                    # Update existing record
                    conn.execute(upd, {
                        'project_name': project_name, 'url_slug': url_slug, 'gitlab_base_url': gitlab_base_url,
                        'project_slug': project_slug, 'dingtalk_url': dingtalk_url,
                        'feishu_url': feishu_url, 'wecom_url': wecom_url,
                        'custom_prompt_system': custom_prompt_system, 'custom_prompt_user': custom_prompt_user,
                        'gitlab_token': gitlab_token, 'dingtalk_enabled': dingtalk_enabled, 'feishu_enabled': feishu_enabled,
                        'wecom_enabled': wecom_enabled, 'review_style': review_style, 'daily_report_enabled': daily_report_enabled,
                        'supported_extensions': supported_extensions, 'updated_at': now, 'id': mapping_id
                    })
                else:
                    # safe to insert
                    result = conn.execute(ins, {
                        'project_name': project_name, 'url_slug': url_slug, 'gitlab_base_url': gitlab_base_url,
                        'project_slug': project_slug, 'dingtalk_url': dingtalk_url,
                        'feishu_url': feishu_url, 'wecom_url': wecom_url,
                        'custom_prompt_system': custom_prompt_system, 'custom_prompt_user': custom_prompt_user,
                        'gitlab_token': gitlab_token, 'dingtalk_enabled': dingtalk_enabled, 'feishu_enabled': feishu_enabled,
                        'wecom_enabled': wecom_enabled, 'review_style': review_style, 'daily_report_enabled': daily_report_enabled,
                        'supported_extensions': supported_extensions, 'created_at': now, 'updated_at': now
                    })
                    mapping_id = result.lastrowid

                # 返回刚创建或更新的映射对象
                r = conn.execute(sel_by_id, {'id': mapping_id})
                row = r.mappings().first()
                return dict(row) if row else None
                
        except Exception as e:
            logger.error(f"❌ Error creating/updating webhook mapping: {e}")
            logger.error(f"❌ 完整堆栈跟踪:\n{traceback.format_exc()}")
            return None

    @staticmethod
    def delete_webhook_mapping(mapping_id: int):
        try:
            engine = get_engine()
            sql = text('DELETE FROM project_webhooks WHERE id = :id')
            with engine.begin() as conn:
                conn.execute(sql, {'id': mapping_id})
        except Exception as e:
            logger.error(f"❌ Error deleting webhook mapping: {e}")
            logger.error(f"❌ 完整堆栈跟踪:\n{traceback.format_exc()}")

    @staticmethod
    def get_webhook_mapping(project_name: Optional[str] = None, url_slug: Optional[str] = None):
        try:
            engine = get_engine()
            sql = text('''SELECT id, project_name, url_slug, dingtalk_url, feishu_url, wecom_url, dingtalk_enabled, feishu_enabled, wecom_enabled, custom_prompt_system, custom_prompt_user, review_style, daily_report_enabled, supported_extensions FROM project_webhooks
                          WHERE project_name = :project_name OR url_slug = :url_slug LIMIT 1''')
            with engine.connect() as conn:
                res = conn.execute(sql, {'project_name': project_name, 'url_slug': url_slug})
                row = res.mappings().first()
                if not row:
                    return None
                return dict(row)
        except Exception as e:
            logger.error(f"❌ Error fetching webhook mapping: {e}")
            logger.error(f"❌ 完整堆栈跟踪:\n{traceback.format_exc()}")
            return None

    @staticmethod
    def get_all_webhook_mappings():
        try:
            engine = get_engine()
            sql = text('SELECT id, project_name, url_slug, gitlab_base_url, project_slug, dingtalk_url, feishu_url, wecom_url, dingtalk_enabled, feishu_enabled, wecom_enabled, custom_prompt_system, custom_prompt_user, review_style, daily_report_enabled, supported_extensions, gitlab_token, created_at, updated_at FROM project_webhooks')
            with engine.connect() as conn:
                res = conn.execute(sql)
                rows = [dict(r) for r in res.mappings().all()]
                return rows
        except Exception as e:
            logger.error(f"❌ Error listing webhook mappings: {e}")
            logger.error(f"❌ 完整堆栈跟踪:\n{traceback.format_exc()}")
            return []

    @staticmethod
    def update_webhook_mapping_by_id(mapping_id: int, project_name: Optional[str] = None, url_slug: Optional[str] = None,
                                     gitlab_base_url: Optional[str] = None, project_slug: Optional[str] = None,
                                     dingtalk_url: Optional[str] = None, feishu_url: Optional[str] = None, wecom_url: Optional[str] = None,
                                     custom_prompt_system: Optional[str] = None, custom_prompt_user: Optional[str] = None,
                                     gitlab_token: Optional[str] = None, dingtalk_enabled: Optional[bool] = None,
                                     feishu_enabled: Optional[bool] = None, wecom_enabled: Optional[bool] = None,
                                     review_style: Optional[str] = None, daily_report_enabled: Optional[bool] = None,
                                     supported_extensions: Optional[str] = None):
        try:
            now = int(time.time())
            engine = get_engine()
            sel = text('SELECT id FROM project_webhooks WHERE id = :id LIMIT 1')
            upd = text('''UPDATE project_webhooks SET project_name = :project_name, url_slug = :url_slug,
                         gitlab_base_url = :gitlab_base_url, project_slug = :project_slug,
                         dingtalk_url = :dingtalk_url, feishu_url = :feishu_url, wecom_url = :wecom_url,
                         dingtalk_enabled = :dingtalk_enabled, feishu_enabled = :feishu_enabled, wecom_enabled = :wecom_enabled,
                         custom_prompt_system = :custom_prompt_system, custom_prompt_user = :custom_prompt_user,
                         gitlab_token = :gitlab_token, review_style = :review_style, daily_report_enabled = :daily_report_enabled, supported_extensions = :supported_extensions, updated_at = :updated_at WHERE id = :id''')
            with engine.begin() as conn:
                res = conn.execute(sel, {'id': mapping_id})
                row = res.mappings().first()
                if not row:
                    return False
                conn.execute(upd, {
                    'project_name': project_name, 'url_slug': url_slug,
                    'gitlab_base_url': gitlab_base_url, 'project_slug': project_slug,
                    'dingtalk_url': dingtalk_url, 'feishu_url': feishu_url, 'wecom_url': wecom_url,
                    'dingtalk_enabled': dingtalk_enabled, 'feishu_enabled': feishu_enabled, 'wecom_enabled': wecom_enabled,
                    'custom_prompt_system': custom_prompt_system, 'custom_prompt_user': custom_prompt_user,
                    'gitlab_token': gitlab_token, 'review_style': review_style, 'daily_report_enabled': daily_report_enabled,
                    'supported_extensions': supported_extensions, 'updated_at': now, 'id': mapping_id
                })
                return True
        except Exception as e:
            logger.error(f"❌ Error updating webhook mapping: {e}")
            logger.error(f"❌ 完整堆栈跟踪:\n{traceback.format_exc()}")
            return False

    @staticmethod
    def get_webhook_mapping_by_gitlab_project(gitlab_base_url: str, project_slug: str) -> Optional[dict]:
        """
        通过 GitLab base URL 和 project slug 获取项目级webhook配置
        
        Args:
            gitlab_base_url: GitLab实例地址，如 https://gitlab.com
            project_slug: 项目slug，如 mygroup/myproject
        """
        try:
            # 规范化 URL（去除尾随斜杠）
            gitlab_base_url = gitlab_base_url.rstrip('/')
            
            engine = get_engine()
            sql = text('''SELECT id, project_name, url_slug, gitlab_base_url, project_slug,
                                dingtalk_url, feishu_url, wecom_url,
                                dingtalk_enabled, feishu_enabled, wecom_enabled,
                                custom_prompt_system, custom_prompt_user, review_style, daily_report_enabled, supported_extensions, gitlab_token
                         FROM project_webhooks
                         WHERE gitlab_base_url = :gitlab_base_url
                         AND project_slug = :project_slug
                         LIMIT 1''')
            with engine.connect() as conn:
                res = conn.execute(sql, {
                    'gitlab_base_url': gitlab_base_url,
                    'project_slug': project_slug
                })
                row = res.mappings().first()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ Error fetching webhook mapping by gitlab_base_url and project_slug: {e}")
            logger.error(f"❌ 完整堆栈跟踪:\n{traceback.format_exc()}")
            return None

    @staticmethod
    def is_valid_webhook_config(config: Optional[dict]) -> bool:
        """
        判断配置是否有效（至少有一个webhook URL非空）
        
        Args:
            config: 配置字典
            
        Returns:
            bool: 配置是否有效
        """
        if not config:
            return False
        
        webhook_urls = [
            config.get('dingtalk_url'),
            config.get('feishu_url'),
            config.get('wecom_url')
        ]
        
        return any(url and str(url).strip() for url in webhook_urls)

    @staticmethod
    def get_system_config() -> dict:
        """从环境变量获取系统级配置"""
        return {
            'dingtalk_url': os.environ.get('DINGTALK_WEBHOOK_URL', ''),
            'feishu_url': os.environ.get('FEISHU_WEBHOOK_URL', ''),
            'wecom_url': os.environ.get('WECOM_WEBHOOK_URL', ''),
            'dingtalk_enabled': os.environ.get('DINGTALK_ENABLED', '0') == '1',
            'feishu_enabled': os.environ.get('FEISHU_ENABLED', '0') == '1',
            'wecom_enabled': os.environ.get('WECOM_ENABLED', '0') == '1',
            'custom_prompt_system': os.environ.get('CUSTOM_PROMPT_SYSTEM', ''),
            'custom_prompt_user': os.environ.get('CUSTOM_PROMPT_USER', ''),
            'gitlab_token': os.environ.get('GITLAB_TOKEN', ''),
            'daily_report_enabled': os.environ.get('DAILY_REPORT_ENABLED', '1') == '1'
        }

    @staticmethod
    def get_webhook_config_with_fallback(gitlab_base_url: Optional[str] = None,
                                        project_slug: Optional[str] = None,
                                        branch_name: Optional[str] = None,
                                        project_name: Optional[str] = None,
                                        url_slug: Optional[str] = None) -> dict:
        """
        获取webhook配置，支持三级回退（分支级 -> 项目级 -> 系统级）
        只有配置存在且有有效URL或提示词时才视为有效配置
        
        注意：webhook URL和提示词分别独立回退
        
        Args:
            gitlab_base_url: GitLab实例地址
            project_slug: 项目slug
            branch_name: 分支名称（可选，用于分支级配置）
            project_name: 项目名称（兼容旧方式）
            url_slug: URL slug（兼容旧方式）
            
        Returns:
            dict: 合并后的配置字典（可能来自多个层级）
        """
        result_config = {}
        
        # 规范化 gitlab_base_url（去除尾随斜杠）
        if gitlab_base_url:
            gitlab_base_url = gitlab_base_url.rstrip('/')
        
        # 收集所有层级的配置
        branch_config = None
        project_config = None
        
        # Level 1: 分支级配置
        if branch_name and gitlab_base_url and project_slug:
            try:
                from biz.service.branch_webhook_service import BranchWebhookService
                branch_config = BranchWebhookService.match_branch_webhook(
                    gitlab_base_url, project_slug, branch_name
                )
            except Exception as e:
                logger.debug(f"获取分支级配置失败: {e}")
        
        # Level 2: 项目级配置
        # 优先使用新字段（gitlab_base_url + project_slug）
        if gitlab_base_url and project_slug:
            project_config = WebhookService.get_webhook_mapping_by_gitlab_project(
                gitlab_base_url, project_slug
            )
        
        # 回退到旧字段（url_slug 或 project_name）
        if not project_config and (url_slug or project_name):
            project_config = WebhookService.get_webhook_mapping(
                project_name=project_name, url_slug=url_slug
            )
        
        # Level 3: 系统级配置（环境变量）
        system_config = WebhookService.get_system_config()
        
        # 按优先级获取每个字段的值
        # Webhook URLs: 优先级 分支级 > 项目级 > 系统级
        for url_field in ['dingtalk_url', 'feishu_url', 'wecom_url']:
            value = None
            source = None
            
            # 尝试从分支级获取
            if branch_config and branch_config.get(url_field) and str(branch_config.get(url_field)).strip():
                value = branch_config.get(url_field)
                source = "分支级"
            # 尝试从项目级获取
            elif project_config and project_config.get(url_field) and str(project_config.get(url_field)).strip():
                value = project_config.get(url_field)
                source = "项目级"
            # 尝试从系统级获取
            elif system_config.get(url_field) and str(system_config.get(url_field)).strip():
                value = system_config.get(url_field)
                source = "系统级"
            
            if value:
                result_config[url_field] = value
                if source:
                    logger.debug(f"  {url_field}: 使用{source}配置")
        
        # Custom Prompts: 优先级 分支级 > 项目级 > 系统级
        for prompt_field in ['custom_prompt_system', 'custom_prompt_user']:
            value = None
            source = None
            
            # 尝试从分支级获取
            if branch_config and branch_config.get(prompt_field) and str(branch_config.get(prompt_field)).strip():
                value = branch_config.get(prompt_field)
                source = "分支级"
            # 尝试从项目级获取
            elif project_config and project_config.get(prompt_field) and str(project_config.get(prompt_field)).strip():
                value = project_config.get(prompt_field)
                source = "项目级"
            # 尝试从系统级获取
            elif system_config.get(prompt_field) and str(system_config.get(prompt_field)).strip():
                value = system_config.get(prompt_field)
                source = "系统级"
            
            if value:
                result_config[prompt_field] = value
                if source:
                    logger.debug(f"  {prompt_field}: 使用{source}配置")
        
        # GitLab Token: 优先级 分支级 > 项目级 > 系统级
        gitlab_token = None
        token_source = None
        
        # 尝试从分支级获取
        if branch_config and branch_config.get('gitlab_token') and str(branch_config.get('gitlab_token')).strip():
            gitlab_token = branch_config.get('gitlab_token')
            token_source = "分支级"
        # 尝试从项目级获取
        elif project_config and project_config.get('gitlab_token') and str(project_config.get('gitlab_token')).strip():
            gitlab_token = project_config.get('gitlab_token')
            token_source = "项目级"
        # 尝试从系统级获取
        elif system_config.get('gitlab_token') and str(system_config.get('gitlab_token')).strip():
            gitlab_token = system_config.get('gitlab_token')
            token_source = "系统级"
        
        if gitlab_token:
            result_config['gitlab_token'] = gitlab_token
            if token_source:
                logger.debug(f"  gitlab_token: 使用{token_source}配置")
        
        # Enabled 状态：优先级 分支级 > 项目级 > 系统级
        for enabled_field in ['dingtalk_enabled', 'feishu_enabled', 'wecom_enabled']:
            enabled_value = None
            enabled_source = None
            
            # 尝试从分支级获取
            if branch_config and branch_config.get(enabled_field) is not None:
                enabled_value = branch_config.get(enabled_field)
                enabled_source = "分支级"
            # 尝试从项目级获取
            elif project_config and project_config.get(enabled_field) is not None:
                enabled_value = project_config.get(enabled_field)
                enabled_source = "项目级"
            # 尝试从系统级获取
            elif system_config.get(enabled_field) is not None:
                enabled_value = system_config.get(enabled_field)
                enabled_source = "系统级"
            
            if enabled_value is not None:
                result_config[enabled_field] = enabled_value
                if enabled_source:
                    logger.debug(f"  {enabled_field}: 使用{enabled_source}配置")
        
        # Review Style: 优先级 分支级 > 项目级
        review_style = None
        style_source = None
        
        # 尝试从分支级获取
        if branch_config and branch_config.get('review_style') and str(branch_config.get('review_style')).strip():
            review_style = branch_config.get('review_style')
            style_source = "分支级"
        # 尝试从项目级获取
        elif project_config and project_config.get('review_style') and str(project_config.get('review_style')).strip():
            review_style = project_config.get('review_style')
            style_source = "项目级"
        
        if review_style:
            result_config['review_style'] = review_style
            if style_source:
                logger.debug(f"  review_style: 使用{style_source}配置")
        
        # Daily Report Enabled: 优先级 分支级 > 项目级 > 系统级
        daily_report_enabled = True  # 默认启用
        daily_report_source = None
        
        # 尝试从分支级获取
        if branch_config and branch_config.get('daily_report_enabled') is not None:
            daily_report_enabled = branch_config.get('daily_report_enabled')
            daily_report_source = "分支级"
        # 尝试从项目级获取
        elif project_config and project_config.get('daily_report_enabled') is not None:
            daily_report_enabled = project_config.get('daily_report_enabled')
            daily_report_source = "项目级"
        # 尝试从系统级获取
        elif system_config.get('daily_report_enabled') is not None:
            daily_report_enabled = system_config.get('daily_report_enabled')
            daily_report_source = "系统级"
        
        result_config['daily_report_enabled'] = daily_report_enabled
        if daily_report_source:
            logger.debug(f"  daily_report_enabled: 使用{daily_report_source}配置 ({daily_report_enabled})")
        
        # Supported Extensions: 优先级 分支级 > 项目级
        supported_extensions = None
        extensions_source = None
        
        # 尝试从分支级获取
        if branch_config and branch_config.get('supported_extensions') and str(branch_config.get('supported_extensions')).strip():
            supported_extensions = branch_config.get('supported_extensions')
            extensions_source = "分支级"
        # 尝试从项目级获取
        elif project_config and project_config.get('supported_extensions') and str(project_config.get('supported_extensions')).strip():
            supported_extensions = project_config.get('supported_extensions')
            extensions_source = "项目级"
        
        if supported_extensions:
            result_config['supported_extensions'] = supported_extensions
            if extensions_source:
                logger.debug(f"  supported_extensions: 使用{extensions_source}配置")
        
        # 记录配置来源摘要
        if branch_config and any(branch_config.get(f) and str(branch_config.get(f)).strip() for f in ['dingtalk_url', 'feishu_url', 'wecom_url', 'custom_prompt_system', 'custom_prompt_user']):
            logger.info(f"✅ 包含分支级配置: {gitlab_base_url}/{project_slug}:{branch_name}")
        if project_config and any(project_config.get(f) and str(project_config.get(f)).strip() for f in ['dingtalk_url', 'feishu_url', 'wecom_url', 'custom_prompt_system', 'custom_prompt_user']):
            logger.info(f"✅ 包含项目级配置: {gitlab_base_url}/{project_slug}")
        if any(system_config.get(f) and str(system_config.get(f)).strip() for f in ['dingtalk_url', 'feishu_url', 'wecom_url', 'custom_prompt_system', 'custom_prompt_user']):
            logger.info(f"✅ 包含系统级配置（环境变量）")
        
        return result_config

    @staticmethod
    def get_all_branch_webhook_configs():
        """获取所有分支级webhook配置"""
        try:
            engine = get_engine()
            sql = text('''SELECT id, gitlab_base_url, project_slug, branch_pattern,
                                dingtalk_url, feishu_url, wecom_url,
                                dingtalk_enabled, feishu_enabled, wecom_enabled,
                                custom_prompt_system, custom_prompt_user, review_style, daily_report_enabled, gitlab_token,
                                supported_extensions, created_at, updated_at
                         FROM branch_webhooks
                         ORDER BY gitlab_base_url, project_slug, branch_pattern''')
            with engine.connect() as conn:
                res = conn.execute(sql)
                rows = [dict(r) for r in res.mappings().all()]
                return rows
        except Exception as e:
            logger.error(f"❌ Error listing branch webhook configs: {e}")
            logger.error(f"❌ 完整堆栈跟踪:\n{traceback.format_exc()}")
            return []

    @staticmethod
    def create_branch_webhook_config(gitlab_base_url: str, project_slug: str, branch_pattern: str,
                                    dingtalk_url: Optional[str] = None, feishu_url: Optional[str] = None,
                                    wecom_url: Optional[str] = None, custom_prompt_system: Optional[str] = None,
                                    custom_prompt_user: Optional[str] = None, gitlab_token: Optional[str] = None,
                                    dingtalk_enabled: Optional[bool] = None, feishu_enabled: Optional[bool] = None,
                                    wecom_enabled: Optional[bool] = None, review_style: Optional[str] = None,
                                    daily_report_enabled: Optional[bool] = None, supported_extensions: Optional[str] = None):
        """创建分支级webhook配置"""
        try:
            now = int(time.time())
            engine = get_engine()
            sql = text('''INSERT INTO branch_webhooks
                         (gitlab_base_url, project_slug, branch_pattern,
                          dingtalk_url, feishu_url, wecom_url,
                          dingtalk_enabled, feishu_enabled, wecom_enabled,
                          custom_prompt_system, custom_prompt_user, review_style, daily_report_enabled, gitlab_token,
                          supported_extensions, created_at, updated_at)
                         VALUES (:gitlab_base_url, :project_slug, :branch_pattern,
                                :dingtalk_url, :feishu_url, :wecom_url,
                                :dingtalk_enabled, :feishu_enabled, :wecom_enabled,
                                :custom_prompt_system, :custom_prompt_user, :review_style, :daily_report_enabled, :gitlab_token,
                                :supported_extensions, :created_at, :updated_at)''')
            with engine.begin() as conn:
                conn.execute(sql, {
                    'gitlab_base_url': gitlab_base_url,
                    'project_slug': project_slug,
                    'branch_pattern': branch_pattern,
                    'dingtalk_url': dingtalk_url,
                    'feishu_url': feishu_url,
                    'wecom_url': wecom_url,
                    'dingtalk_enabled': dingtalk_enabled,
                    'feishu_enabled': feishu_enabled,
                    'wecom_enabled': wecom_enabled,
                    'custom_prompt_system': custom_prompt_system,
                    'custom_prompt_user': custom_prompt_user,
                    'review_style': review_style,
                    'daily_report_enabled': daily_report_enabled,
                    'gitlab_token': gitlab_token,
                    'supported_extensions': supported_extensions,
                    'created_at': now,
                    'updated_at': now
                })
            return True
        except Exception as e:
            logger.error(f"❌ Error creating branch webhook config: {e}")
            logger.error(f"❌ 完整堆栈跟踪:\n{traceback.format_exc()}")
            return None

    @staticmethod
    def update_branch_webhook_config_by_id(config_id: int, gitlab_base_url: Optional[str] = None,
                                          project_slug: Optional[str] = None, branch_pattern: Optional[str] = None,
                                          dingtalk_url: Optional[str] = None, feishu_url: Optional[str] = None,
                                          wecom_url: Optional[str] = None, custom_prompt_system: Optional[str] = None,
                                          custom_prompt_user: Optional[str] = None, gitlab_token: Optional[str] = None,
                                          dingtalk_enabled: Optional[bool] = None, feishu_enabled: Optional[bool] = None,
                                          wecom_enabled: Optional[bool] = None, review_style: Optional[str] = None,
                                          daily_report_enabled: Optional[bool] = None, supported_extensions: Optional[str] = None):
        """更新分支级webhook配置"""
        try:
            now = int(time.time())
            engine = get_engine()
            sel = text('SELECT id FROM branch_webhooks WHERE id = :id LIMIT 1')
            upd = text('''UPDATE branch_webhooks
                         SET gitlab_base_url = :gitlab_base_url,
                             project_slug = :project_slug,
                             branch_pattern = :branch_pattern,
                             dingtalk_url = :dingtalk_url,
                             feishu_url = :feishu_url,
                             wecom_url = :wecom_url,
                             dingtalk_enabled = :dingtalk_enabled,
                             feishu_enabled = :feishu_enabled,
                             wecom_enabled = :wecom_enabled,
                             custom_prompt_system = :custom_prompt_system,
                             custom_prompt_user = :custom_prompt_user,
                             review_style = :review_style,
                             daily_report_enabled = :daily_report_enabled,
                             gitlab_token = :gitlab_token,
                             supported_extensions = :supported_extensions,
                             updated_at = :updated_at
                         WHERE id = :id''')
            with engine.begin() as conn:
                res = conn.execute(sel, {'id': config_id})
                row = res.mappings().first()
                if not row:
                    return False
                conn.execute(upd, {
                    'gitlab_base_url': gitlab_base_url,
                    'project_slug': project_slug,
                    'branch_pattern': branch_pattern,
                    'dingtalk_url': dingtalk_url,
                    'feishu_url': feishu_url,
                    'wecom_url': wecom_url,
                    'dingtalk_enabled': dingtalk_enabled,
                    'feishu_enabled': feishu_enabled,
                    'wecom_enabled': wecom_enabled,
                    'custom_prompt_system': custom_prompt_system,
                    'custom_prompt_user': custom_prompt_user,
                    'review_style': review_style,
                    'daily_report_enabled': daily_report_enabled,
                    'gitlab_token': gitlab_token,
                    'supported_extensions': supported_extensions,
                    'updated_at': now,
                    'id': config_id
                })
                return True
        except Exception as e:
            logger.error(f"❌ Error updating branch webhook config: {e}")
            logger.error(f"❌ 完整堆栈跟踪:\n{traceback.format_exc()}")
            return False

    @staticmethod
    def delete_branch_webhook_config(config_id: int):
        """删除分支级webhook配置"""
        try:
            engine = get_engine()
            sql = text('DELETE FROM branch_webhooks WHERE id = :id')
            with engine.begin() as conn:
                conn.execute(sql, {'id': config_id})
        except Exception as e:
            logger.error(f"❌ Error deleting branch webhook config: {e}")
            logger.error(f"❌ 完整堆栈跟踪:\n{traceback.format_exc()}")
