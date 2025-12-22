"""Webhook 配置管理服务：负责项目级 IM webhook 的增删改查。
封装 DB 访问，供 API、通知器调用。
"""
import time
from typing import Optional

from sqlalchemy import text

from biz.utils.db import get_engine
from biz.utils.log import logger


class WebhookService:
    @staticmethod
    def init_db():
        try:
            engine = get_engine()
            from sqlalchemy import MetaData, Table, Column, Integer, Text, UniqueConstraint

            metadata = MetaData()
            Table(
                'project_webhooks', metadata,
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('project_name', Text, unique=True),
                Column('url_slug', Text, unique=True),
                Column('dingtalk_url', Text),
                Column('feishu_url', Text),
                Column('wecom_url', Text),
                Column('created_at', Integer),
                Column('updated_at', Integer),
            )
            metadata.create_all(engine)
        except Exception as e:
            logger.error(f"WebhookService.init_db failed: {e}")

    @staticmethod
    def create_or_update_webhook_mapping(project_name: Optional[str] = None, url_slug: Optional[str] = None,
                                         dingtalk_url: Optional[str] = None, feishu_url: Optional[str] = None,
                                         wecom_url: Optional[str] = None):
        try:
            now = int(time.time())
            engine = get_engine()
            # Check duplicates: ensure project_name and url_slug are unique
            sel_by_project = text('SELECT id, project_name, url_slug FROM project_webhooks WHERE project_name = :project_name LIMIT 1')
            sel_by_slug = text('SELECT id, project_name, url_slug FROM project_webhooks WHERE url_slug = :url_slug LIMIT 1')
            ins = text('''INSERT INTO project_webhooks (project_name, url_slug, dingtalk_url, feishu_url, wecom_url, created_at, updated_at)
                         VALUES (:project_name, :url_slug, :dingtalk_url, :feishu_url, :wecom_url, :created_at, :updated_at)''')
            upd = text('''UPDATE project_webhooks SET project_name = :project_name, url_slug = :url_slug, dingtalk_url = :dingtalk_url, feishu_url = :feishu_url, wecom_url = :wecom_url, updated_at = :updated_at WHERE id = :id''')
            with engine.begin() as conn:
                existing_project = None
                existing_slug = None
                if project_name:
                    r = conn.execute(sel_by_project, {'project_name': project_name})
                    existing_project = r.mappings().first()
                if url_slug:
                    r = conn.execute(sel_by_slug, {'url_slug': url_slug})
                    existing_slug = r.mappings().first()

                # Determine action: update existing (if same record) or insert.
                if existing_project and existing_slug:
                    # both exist
                    if existing_project['id'] != existing_slug['id']:
                        logger.error("Duplicate mapping exists for project_name or url_slug")
                        return None
                    mapping_id = existing_project['id']
                    conn.execute(upd, {'project_name': project_name, 'url_slug': url_slug, 'dingtalk_url': dingtalk_url, 'feishu_url': feishu_url, 'wecom_url': wecom_url, 'updated_at': now, 'id': mapping_id})
                elif existing_project:
                    # update same record by project
                    mapping_id = existing_project['id']
                    conn.execute(upd, {'project_name': project_name, 'url_slug': url_slug, 'dingtalk_url': dingtalk_url, 'feishu_url': feishu_url, 'wecom_url': wecom_url, 'updated_at': now, 'id': mapping_id})
                elif existing_slug:
                    # update same record by slug
                    mapping_id = existing_slug['id']
                    conn.execute(upd, {'project_name': project_name, 'url_slug': url_slug, 'dingtalk_url': dingtalk_url, 'feishu_url': feishu_url, 'wecom_url': wecom_url, 'updated_at': now, 'id': mapping_id})
                else:
                    # safe to insert
                    conn.execute(ins, {'project_name': project_name, 'url_slug': url_slug, 'dingtalk_url': dingtalk_url, 'feishu_url': feishu_url, 'wecom_url': wecom_url, 'created_at': now, 'updated_at': now})
        except Exception as e:
            logger.error(f"Error creating/updating webhook mapping: {e}")
            return None

        # 返回刚创建或更新的映射对象
        try:
            return WebhookService.get_webhook_mapping(project_name=project_name, url_slug=url_slug)
        except Exception:
            return None

    @staticmethod
    def delete_webhook_mapping(mapping_id: int):
        try:
            engine = get_engine()
            sql = text('DELETE FROM project_webhooks WHERE id = :id')
            with engine.begin() as conn:
                conn.execute(sql, {'id': mapping_id})
        except Exception as e:
            logger.error(f"Error deleting webhook mapping: {e}")

    @staticmethod
    def get_webhook_mapping(project_name: Optional[str] = None, url_slug: Optional[str] = None):
        try:
            engine = get_engine()
            sql = text('''SELECT id, project_name, url_slug, dingtalk_url, feishu_url, wecom_url FROM project_webhooks
                          WHERE project_name = :project_name OR url_slug = :url_slug LIMIT 1''')
            with engine.connect() as conn:
                res = conn.execute(sql, {'project_name': project_name, 'url_slug': url_slug})
                row = res.mappings().first()
                if not row:
                    return None
                return dict(row)
        except Exception as e:
            logger.error(f"Error fetching webhook mapping: {e}")
            return None

    @staticmethod
    def get_all_webhook_mappings():
        try:
            engine = get_engine()
            sql = text('SELECT id, project_name, url_slug, dingtalk_url, feishu_url, wecom_url, created_at, updated_at FROM project_webhooks')
            with engine.connect() as conn:
                res = conn.execute(sql)
                rows = [dict(r) for r in res.mappings().all()]
                return rows
        except Exception as e:
            logger.error(f"Error listing webhook mappings: {e}")
            return []

    @staticmethod
    def update_webhook_mapping_by_id(mapping_id: int, project_name: Optional[str] = None, url_slug: Optional[str] = None,
                                     dingtalk_url: Optional[str] = None, feishu_url: Optional[str] = None, wecom_url: Optional[str] = None):
        try:
            now = int(time.time())
            engine = get_engine()
            sel = text('SELECT id FROM project_webhooks WHERE id = :id LIMIT 1')
            upd = text('''UPDATE project_webhooks SET project_name = :project_name, url_slug = :url_slug, dingtalk_url = :dingtalk_url, feishu_url = :feishu_url, wecom_url = :wecom_url, updated_at = :updated_at WHERE id = :id''')
            with engine.begin() as conn:
                res = conn.execute(sel, {'id': mapping_id})
                row = res.mappings().first()
                if not row:
                    return False
                conn.execute(upd, {'project_name': project_name, 'url_slug': url_slug, 'dingtalk_url': dingtalk_url, 'feishu_url': feishu_url, 'wecom_url': wecom_url, 'updated_at': now, 'id': mapping_id})
                return True
        except Exception as e:
            logger.error(f"Error updating webhook mapping: {e}")
            return False
