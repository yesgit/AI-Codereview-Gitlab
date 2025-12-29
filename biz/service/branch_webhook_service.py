"""分支级 Webhook 配置管理服务
支持通配符匹配和优先级排序
"""
import time
import fnmatch
from typing import Optional, List

from sqlalchemy import text

from biz.utils.db import get_engine
from biz.utils.log import logger


class BranchWebhookService:
    @staticmethod
    def init_db():
        """初始化分支级webhook配置表"""
        try:
            engine = get_engine()
            from sqlalchemy import MetaData, Table, Column, Integer, String, Text, Boolean, UniqueConstraint

            metadata = MetaData()
            Table(
                'branch_webhooks', metadata,
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('gitlab_base_url', String(255), nullable=False),
                Column('project_slug', String(255), nullable=False),
                Column('branch_pattern', String(255), nullable=False),
                Column('dingtalk_url', Text),
                Column('feishu_url', Text),
                Column('wecom_url', Text),
                Column('dingtalk_enabled', Boolean),
                Column('feishu_enabled', Boolean),
                Column('wecom_enabled', Boolean),
                Column('custom_prompt_system', Text),
                Column('custom_prompt_user', Text),
                Column('review_style', String(50)),
                Column('daily_report_enabled', Boolean),
                Column('supported_extensions', Text),
                Column('created_at', Integer),
                Column('updated_at', Integer),
                UniqueConstraint('gitlab_base_url', 'project_slug', 'branch_pattern',
                               name='uq_branch_webhooks_gitlab_project_branch')
            )
            metadata.create_all(engine)
        except Exception as e:
            logger.error(f"❌ Branch webhooks table initialization failed: {e}")

    @staticmethod
    def create_or_update_branch_webhook(gitlab_base_url: str, project_slug: str, branch_pattern: str,
                                       dingtalk_url: Optional[str] = None, feishu_url: Optional[str] = None,
                                       wecom_url: Optional[str] = None, custom_prompt_system: Optional[str] = None,
                                       custom_prompt_user: Optional[str] = None, dingtalk_enabled: Optional[bool] = None,
                                       feishu_enabled: Optional[bool] = None, wecom_enabled: Optional[bool] = None,
                                       review_style: Optional[str] = None, daily_report_enabled: Optional[bool] = None,
                                       supported_extensions: Optional[str] = None):
        """
        创建或更新分支级webhook配置
        
        Args:
            gitlab_base_url: GitLab实例地址，如 https://gitlab.com
            project_slug: 项目slug，如 mygroup/myproject
            branch_pattern: 分支模式，支持通配符，如 feature/*, main
            dingtalk_url: 钉钉webhook URL
            feishu_url: 飞书webhook URL
            wecom_url: 企业微信webhook URL
            custom_prompt_system: 自定义系统提示词
            custom_prompt_user: 自定义用户提示词
            dingtalk_enabled: 是否启用钉钉通知
            feishu_enabled: 是否启用飞书通知
            wecom_enabled: 是否启用企业微信通知
            review_style: 评审风格，可选值: professional, sarcastic, gentle, humorous
        """
        try:
            now = int(time.time())
            engine = get_engine()
            
            sel = text('''SELECT id FROM branch_webhooks 
                         WHERE gitlab_base_url = :gitlab_base_url 
                         AND project_slug = :project_slug 
                         AND branch_pattern = :branch_pattern 
                         LIMIT 1''')
            
            ins = text('''INSERT INTO branch_webhooks
                         (gitlab_base_url, project_slug, branch_pattern, dingtalk_url, feishu_url, wecom_url,
                          dingtalk_enabled, feishu_enabled, wecom_enabled,
                          custom_prompt_system, custom_prompt_user, review_style, daily_report_enabled, supported_extensions, created_at, updated_at)
                         VALUES (:gitlab_base_url, :project_slug, :branch_pattern, :dingtalk_url, :feishu_url,
                                :wecom_url, :dingtalk_enabled, :feishu_enabled, :wecom_enabled,
                                :custom_prompt_system, :custom_prompt_user, :review_style, :daily_report_enabled, :supported_extensions, :created_at, :updated_at)''')
            
            upd = text('''UPDATE branch_webhooks
                         SET dingtalk_url = :dingtalk_url, feishu_url = :feishu_url, wecom_url = :wecom_url,
                             dingtalk_enabled = :dingtalk_enabled, feishu_enabled = :feishu_enabled, wecom_enabled = :wecom_enabled,
                             custom_prompt_system = :custom_prompt_system, custom_prompt_user = :custom_prompt_user,
                             review_style = :review_style, daily_report_enabled = :daily_report_enabled, supported_extensions = :supported_extensions, updated_at = :updated_at
                         WHERE id = :id''')
            
            with engine.begin() as conn:
                r = conn.execute(sel, {
                    'gitlab_base_url': gitlab_base_url,
                    'project_slug': project_slug,
                    'branch_pattern': branch_pattern
                })
                row = r.mappings().first()
                
                params = {
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
                    'supported_extensions': supported_extensions,
                    'updated_at': now
                }
                
                if row:
                    # 更新现有记录
                    params['id'] = row['id']
                    conn.execute(upd, params)
                    logger.info(f"✅ Updated branch webhook: {gitlab_base_url}/{project_slug}:{branch_pattern}")
                else:
                    # 创建新记录
                    params['created_at'] = now
                    conn.execute(ins, params)
                    logger.info(f"✅ Created branch webhook: {gitlab_base_url}/{project_slug}:{branch_pattern}")
                    
            return BranchWebhookService.get_branch_webhook(gitlab_base_url, project_slug, branch_pattern)
        except Exception as e:
            logger.error(f"❌ Error creating/updating branch webhook: {e}")
            return None

    @staticmethod
    def delete_branch_webhook(webhook_id: int):
        """删除分支级webhook配置"""
        try:
            engine = get_engine()
            sql = text('DELETE FROM branch_webhooks WHERE id = :id')
            with engine.begin() as conn:
                conn.execute(sql, {'id': webhook_id})
            logger.info(f"✅ Deleted branch webhook: id={webhook_id}")
        except Exception as e:
            logger.error(f"❌ Error deleting branch webhook: {e}")

    @staticmethod
    def get_branch_webhook(gitlab_base_url: str, project_slug: str, branch_pattern: str) -> Optional[dict]:
        """获取指定的分支级webhook配置"""
        try:
            engine = get_engine()
            sql = text('''SELECT id, gitlab_base_url, project_slug, branch_pattern,
                                dingtalk_url, feishu_url, wecom_url,
                                dingtalk_enabled, feishu_enabled, wecom_enabled,
                                custom_prompt_system, custom_prompt_user, review_style, daily_report_enabled, supported_extensions,
                                created_at, updated_at
                         FROM branch_webhooks
                         WHERE gitlab_base_url = :gitlab_base_url
                         AND project_slug = :project_slug
                         AND branch_pattern = :branch_pattern
                         LIMIT 1''')
            with engine.connect() as conn:
                res = conn.execute(sql, {
                    'gitlab_base_url': gitlab_base_url,
                    'project_slug': project_slug,
                    'branch_pattern': branch_pattern
                })
                row = res.mappings().first()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ Error fetching branch webhook: {e}")
            return None

    @staticmethod
    def get_all_branch_webhooks(gitlab_base_url: Optional[str] = None, 
                                project_slug: Optional[str] = None) -> List[dict]:
        """
        获取所有分支级webhook配置，可选按GitLab实例或项目过滤
        
        Args:
            gitlab_base_url: 可选，按GitLab实例过滤
            project_slug: 可选，按项目过滤
        """
        try:
            # 规范化 URL（去除尾随斜杠）
            if gitlab_base_url:
                gitlab_base_url = gitlab_base_url.rstrip('/')
            
            engine = get_engine()
            
            where_clauses = []
            params = {}
            
            if gitlab_base_url:
                where_clauses.append('gitlab_base_url = :gitlab_base_url')
                params['gitlab_base_url'] = gitlab_base_url
            
            if project_slug:
                where_clauses.append('project_slug = :project_slug')
                params['project_slug'] = project_slug
            
            where_clause = ' AND '.join(where_clauses) if where_clauses else '1=1'
            
            sql = text(f'''SELECT id, gitlab_base_url, project_slug, branch_pattern,
                                 dingtalk_url, feishu_url, wecom_url,
                                 dingtalk_enabled, feishu_enabled, wecom_enabled,
                                 custom_prompt_system, custom_prompt_user, review_style, daily_report_enabled, supported_extensions,
                                 created_at, updated_at
                          FROM branch_webhooks
                          WHERE {where_clause}
                          ORDER BY gitlab_base_url, project_slug, branch_pattern''')
            
            with engine.connect() as conn:
                res = conn.execute(sql, params)
                rows = [dict(r) for r in res.mappings().all()]
                return rows
        except Exception as e:
            logger.error(f"❌ Error listing branch webhooks: {e}")
            return []

    @staticmethod
    def match_branch_webhook(gitlab_base_url: str, project_slug: str, branch_name: str) -> Optional[dict]:
        """
        匹配分支webhook配置，支持通配符
        
        优先级规则：
        1. 精确匹配优先（branch_pattern == branch_name）
        2. 通配符匹配按模式长度排序，最长的优先
        
        Args:
            gitlab_base_url: GitLab实例地址
            project_slug: 项目slug
            branch_name: 实际的分支名称
            
        Returns:
            匹配到的配置字典，如果没有匹配则返回 None
        """
        try:
            # 规范化 URL（去除尾随斜杠）
            gitlab_base_url = gitlab_base_url.rstrip('/')
            
            # 获取该项目的所有分支配置
            all_configs = BranchWebhookService.get_all_branch_webhooks(gitlab_base_url, project_slug)
            
            if not all_configs:
                return None
            
            # 先检查精确匹配
            for config in all_configs:
                if config['branch_pattern'] == branch_name:
                    logger.info(f"✅ 精确匹配分支配置: {gitlab_base_url}/{project_slug}:{branch_name}")
                    return config
            
            # 再检查通配符匹配，按模式长度排序（最长优先）
            wildcard_configs = [
                config for config in all_configs 
                if '*' in config['branch_pattern'] or '?' in config['branch_pattern']
            ]
            
            # 按模式长度降序排序（越长越具体）
            wildcard_configs.sort(key=lambda x: len(x['branch_pattern']), reverse=True)
            
            for config in wildcard_configs:
                if fnmatch.fnmatch(branch_name, config['branch_pattern']):
                    logger.info(f"✅ 通配符匹配分支配置: {gitlab_base_url}/{project_slug}:{branch_name} -> {config['branch_pattern']}")
                    return config
            
            logger.debug(f"ℹ️ 未找到匹配的分支配置: {gitlab_base_url}/{project_slug}:{branch_name}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error matching branch webhook: {e}")
            return None

    @staticmethod
    def update_branch_webhook_by_id(webhook_id: int, gitlab_base_url: Optional[str] = None,
                                   project_slug: Optional[str] = None, branch_pattern: Optional[str] = None,
                                   dingtalk_url: Optional[str] = None, feishu_url: Optional[str] = None,
                                   wecom_url: Optional[str] = None, custom_prompt_system: Optional[str] = None,
                                   custom_prompt_user: Optional[str] = None, dingtalk_enabled: Optional[bool] = None,
                                   feishu_enabled: Optional[bool] = None, wecom_enabled: Optional[bool] = None,
                                   review_style: Optional[str] = None, daily_report_enabled: Optional[bool] = None,
                                   supported_extensions: Optional[str] = None):
        """通过ID更新分支级webhook配置"""
        try:
            now = int(time.time())
            engine = get_engine()
            
            sel = text('SELECT id FROM branch_webhooks WHERE id = :id LIMIT 1')
            upd = text('''UPDATE branch_webhooks
                         SET gitlab_base_url = :gitlab_base_url, project_slug = :project_slug,
                             branch_pattern = :branch_pattern, dingtalk_url = :dingtalk_url,
                             feishu_url = :feishu_url, wecom_url = :wecom_url,
                             dingtalk_enabled = :dingtalk_enabled, feishu_enabled = :feishu_enabled, wecom_enabled = :wecom_enabled,
                             custom_prompt_system = :custom_prompt_system,
                             custom_prompt_user = :custom_prompt_user, review_style = :review_style, daily_report_enabled = :daily_report_enabled, supported_extensions = :supported_extensions, updated_at = :updated_at
                         WHERE id = :id''')
            
            with engine.begin() as conn:
                res = conn.execute(sel, {'id': webhook_id})
                row = res.mappings().first()
                if not row:
                    logger.warning(f"⚠️ Branch webhook not found: id={webhook_id}")
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
                    'supported_extensions': supported_extensions,
                    'updated_at': now,
                    'id': webhook_id
                })
                logger.info(f"✅ Updated branch webhook by id: {webhook_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Error updating branch webhook by id: {e}")
            return False
