import time
import pandas as pd
from sqlalchemy import text

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity
from biz.utils.db import get_engine
from biz.utils.log import logger


class ReviewService:
    DB_FILE = "data/data.db"

    @staticmethod
    def init_db():
        """初始化数据库及表结构"""
        try:
            # 确保由 WebhookService 初始化 project_webhooks 表（包含完整字段）
            try:
                from biz.service.webhook_service import WebhookService
                WebhookService.init_db()
            except Exception as e:
                logger.debug(f"WebhookService.init_db() 调用失败（可能已初始化）: {e}")
            
            # 确保由 BranchWebhookService 初始化 branch_webhooks 表
            try:
                from biz.service.branch_webhook_service import BranchWebhookService
                BranchWebhookService.init_db()
            except Exception as e:
                logger.debug(f"BranchWebhookService.init_db() 调用失败（可能已初始化）: {e}")
            
            engine = get_engine()
            from sqlalchemy import MetaData, Table, Column, Integer, Text

            metadata = MetaData()
            Table(
                'mr_review_log', metadata,
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('project_name', Text),
                Column('author', Text),
                Column('source_branch', Text),
                Column('target_branch', Text),
                Column('updated_at', Integer),
                Column('commit_messages', Text),
                Column('score', Integer),
                Column('url', Text),
                Column('review_result', Text),
                Column('additions', Integer, default=0),
                Column('deletions', Integer, default=0),
                Column('last_commit_id', Text, default=''),
                Column('gitlab_base_url', Text),
                Column('project_slug', Text)
            )
            Table(
                'push_review_log', metadata,
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('project_name', Text),
                Column('author', Text),
                Column('branch', Text),
                Column('updated_at', Integer),
                Column('commit_messages', Text),
                Column('score', Integer),
                Column('review_result', Text),
                Column('additions', Integer, default=0),
                Column('deletions', Integer, default=0),
                Column('gitlab_base_url', Text),
                Column('project_slug', Text)
            )
            metadata.create_all(engine)
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")

    @staticmethod
    def insert_mr_review_log(entity: MergeRequestReviewEntity):
        try:
            engine = get_engine()
            sql = text('''
                INSERT INTO mr_review_log (project_name, author, source_branch, target_branch, updated_at, commit_messages, score, url, review_result, additions, deletions, last_commit_id, gitlab_base_url, project_slug)
                VALUES (:project_name, :author, :source_branch, :target_branch, :updated_at, :commit_messages, :score, :url, :review_result, :additions, :deletions, :last_commit_id, :gitlab_base_url, :project_slug)
            ''')
            with engine.begin() as conn:
                conn.execute(sql, {
                    'project_name': entity.project_name,
                    'author': entity.author,
                    'source_branch': entity.source_branch,
                    'target_branch': entity.target_branch,
                    'updated_at': entity.updated_at,
                    'commit_messages': entity.commit_messages,
                    'score': entity.score,
                    'url': entity.url,
                    'review_result': entity.review_result,
                    'additions': entity.additions,
                    'deletions': entity.deletions,
                    'last_commit_id': entity.last_commit_id,
                    'gitlab_base_url': entity.gitlab_base_url,
                    'project_slug': entity.project_slug
                })
        except Exception as e:
            logger.error(f"Error inserting review log: {e}")

    @staticmethod
    def get_mr_review_logs(authors: list = None, project_names: list = None, updated_at_gte: int = None,
                           updated_at_lte: int = None) -> pd.DataFrame:
        try:
            engine = get_engine()
            query = "SELECT project_name, author, source_branch, target_branch, updated_at, commit_messages, score, url, review_result, additions, deletions, gitlab_base_url, project_slug FROM mr_review_log WHERE 1=1"
            params = {}
            if authors:
                placeholders = ','.join([f':a{i}' for i in range(len(authors))])
                query += f" AND author IN ({placeholders})"
                for i, v in enumerate(authors):
                    params[f'a{i}'] = v
            if project_names:
                placeholders = ','.join([f':p{i}' for i in range(len(project_names))])
                query += f" AND project_name IN ({placeholders})"
                for i, v in enumerate(project_names):
                    params[f'p{i}'] = v
            if updated_at_gte is not None:
                query += " AND updated_at >= :updated_at_gte"
                params['updated_at_gte'] = updated_at_gte
            if updated_at_lte is not None:
                query += " AND updated_at <= :updated_at_lte"
                params['updated_at_lte'] = updated_at_lte
            query += " ORDER BY updated_at DESC"
            df = pd.read_sql_query(sql=text(query), con=engine, params=params)
            return df
        except Exception as e:
            logger.error(f"Error retrieving review logs: {e}")
            return pd.DataFrame()

    @staticmethod
    def check_mr_last_commit_id_exists(project_name: str, source_branch: str, target_branch: str, last_commit_id: str) -> bool:
        try:
            engine = get_engine()
            sql = text('''SELECT COUNT(*) as cnt FROM mr_review_log WHERE project_name = :project_name AND source_branch = :source_branch AND target_branch = :target_branch AND last_commit_id = :last_commit_id''')
            with engine.connect() as conn:
                res = conn.execute(sql, {
                    'project_name': project_name,
                    'source_branch': source_branch,
                    'target_branch': target_branch,
                    'last_commit_id': last_commit_id
                })
                row = res.mappings().first()
                count = row['cnt'] if row else 0
                return count > 0
        except Exception as e:
            logger.error(f"Error checking last_commit_id: {e}")
            return False

    @staticmethod
    def insert_push_review_log(entity: PushReviewEntity):
        try:
            engine = get_engine()
            sql = text('''INSERT INTO push_review_log (project_name, author, branch, updated_at, commit_messages, score, review_result, additions, deletions, gitlab_base_url, project_slug)
                         VALUES (:project_name, :author, :branch, :updated_at, :commit_messages, :score, :review_result, :additions, :deletions, :gitlab_base_url, :project_slug)''')
            with engine.begin() as conn:
                conn.execute(sql, {
                    'project_name': entity.project_name,
                    'author': entity.author,
                    'branch': entity.branch,
                    'updated_at': entity.updated_at,
                    'commit_messages': entity.commit_messages,
                    'score': entity.score,
                    'review_result': entity.review_result,
                    'additions': entity.additions,
                    'deletions': entity.deletions,
                    'gitlab_base_url': entity.gitlab_base_url,
                    'project_slug': entity.project_slug
                })
        except Exception as e:
            logger.error(f"Error inserting review log: {e}")

    @staticmethod
    def get_push_review_logs(authors: list = None, project_names: list = None, updated_at_gte: int = None,
                             updated_at_lte: int = None) -> pd.DataFrame:
        try:
            engine = get_engine()
            query = "SELECT project_name, author, branch, updated_at, commit_messages, score, review_result, additions, deletions, gitlab_base_url, project_slug FROM push_review_log WHERE 1=1"
            params = {}
            if authors:
                placeholders = ','.join([f':a{i}' for i in range(len(authors))])
                query += f" AND author IN ({placeholders})"
                for i, v in enumerate(authors):
                    params[f'a{i}'] = v
            if project_names:
                placeholders = ','.join([f':p{i}' for i in range(len(project_names))])
                query += f" AND project_name IN ({placeholders})"
                for i, v in enumerate(project_names):
                    params[f'p{i}'] = v
            if updated_at_gte is not None:
                query += " AND updated_at >= :updated_at_gte"
                params['updated_at_gte'] = updated_at_gte
            if updated_at_lte is not None:
                query += " AND updated_at <= :updated_at_lte"
                params['updated_at_lte'] = updated_at_lte
            query += " ORDER BY updated_at DESC"
            df = pd.read_sql_query(sql=text(query), con=engine, params=params)
            return df
        except Exception as e:
            logger.error(f"Error retrieving push review logs: {e}")
            return pd.DataFrame()

    @staticmethod
    def create_or_update_webhook_mapping(project_name: str = None, url_slug: str = None, dingtalk_url: str = None,
                                         feishu_url: str = None, wecom_url: str = None, gitlab_base_url: str = None,
                                         project_slug: str = None):
        try:
            now = int(time.time())
            engine = get_engine()
            sel_by_project = text('SELECT id, project_name, url_slug FROM project_webhooks WHERE project_name = :project_name LIMIT 1')
            sel_by_slug = text('SELECT id, project_name, url_slug FROM project_webhooks WHERE url_slug = :url_slug LIMIT 1')
            ins = text('''INSERT INTO project_webhooks (project_name, url_slug, dingtalk_url, feishu_url, wecom_url, gitlab_base_url, project_slug, created_at, updated_at)
                         VALUES (:project_name, :url_slug, :dingtalk_url, :feishu_url, :wecom_url, :gitlab_base_url, :project_slug, :created_at, :updated_at)''')
            upd = text('''UPDATE project_webhooks SET project_name = :project_name, url_slug = :url_slug, dingtalk_url = :dingtalk_url, feishu_url = :feishu_url, wecom_url = :wecom_url, gitlab_base_url = :gitlab_base_url, project_slug = :project_slug, updated_at = :updated_at WHERE id = :id''')
            with engine.begin() as conn:
                existing_project = None
                existing_slug = None
                if project_name:
                    r = conn.execute(sel_by_project, {'project_name': project_name})
                    existing_project = r.mappings().first()
                if url_slug:
                    r = conn.execute(sel_by_slug, {'url_slug': url_slug})
                    existing_slug = r.mappings().first()
                if existing_project and existing_slug:
                    if existing_project['id'] != existing_slug['id']:
                        logger.error("Duplicate mapping exists for project_name or url_slug")
                        return None
                    mapping_id = existing_project['id']
                    conn.execute(upd, {'project_name': project_name, 'url_slug': url_slug, 'dingtalk_url': dingtalk_url, 'feishu_url': feishu_url, 'wecom_url': wecom_url, 'gitlab_base_url': gitlab_base_url, 'project_slug': project_slug, 'updated_at': now, 'id': mapping_id})
                elif existing_project:
                    mapping_id = existing_project['id']
                    conn.execute(upd, {'project_name': project_name, 'url_slug': url_slug, 'dingtalk_url': dingtalk_url, 'feishu_url': feishu_url, 'wecom_url': wecom_url, 'gitlab_base_url': gitlab_base_url, 'project_slug': project_slug, 'updated_at': now, 'id': mapping_id})
                elif existing_slug:
                    mapping_id = existing_slug['id']
                    conn.execute(upd, {'project_name': project_name, 'url_slug': url_slug, 'dingtalk_url': dingtalk_url, 'feishu_url': feishu_url, 'wecom_url': wecom_url, 'gitlab_base_url': gitlab_base_url, 'project_slug': project_slug, 'updated_at': now, 'id': mapping_id})
                else:
                    conn.execute(ins, {'project_name': project_name, 'url_slug': url_slug, 'dingtalk_url': dingtalk_url, 'feishu_url': feishu_url, 'wecom_url': wecom_url, 'gitlab_base_url': gitlab_base_url, 'project_slug': project_slug, 'created_at': now, 'updated_at': now})
        except Exception as e:
            logger.error(f"Error creating/updating webhook mapping: {e}")

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
    def get_webhook_mapping(project_name: str = None, url_slug: str = None):
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
    def update_webhook_mapping_by_id(mapping_id: int, project_name: str = None, url_slug: str = None,
                                     dingtalk_url: str = None, feishu_url: str = None, wecom_url: str = None):
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


# Initialize database
ReviewService.init_db()
