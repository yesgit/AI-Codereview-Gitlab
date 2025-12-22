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
            engine = get_engine()
            # 使用 SQLAlchemy metadata 创建表，跨数据库兼容
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
                Column('last_commit_id', Text, default='')
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
                Column('deletions', Integer, default=0)
            )

            # project_webhooks 表由 WebhookService 管理，但确保存在且添加唯一约束
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
            logger.error(f"Database initialization failed: {e}")

    @staticmethod
    def insert_mr_review_log(entity: MergeRequestReviewEntity):
        """插入合并请求审核日志"""
        try:
            engine = get_engine()
            sql = text('''
                INSERT INTO mr_review_log (project_name, author, source_branch, target_branch, updated_at, commit_messages, score, url, review_result, additions, deletions, last_commit_id)
                VALUES (:project_name, :author, :source_branch, :target_branch, :updated_at, :commit_messages, :score, :url, :review_result, :additions, :deletions, :last_commit_id)
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
                    'last_commit_id': entity.last_commit_id
                })
        except Exception as e:
            logger.error(f"Error inserting review log: {e}")

    @staticmethod
    def get_mr_review_logs(authors: list = None, project_names: list = None, updated_at_gte: int = None,
                           updated_at_lte: int = None) -> pd.DataFrame:
        """获取符合条件的合并请求审核日志"""
        try:
            engine = get_engine()
            query = "SELECT project_name, author, source_branch, target_branch, updated_at, commit_messages, score, url, review_result, additions, deletions FROM mr_review_log WHERE 1=1"
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
        """检查指定项目的Merge Request是否已经存在相同的last_commit_id"""
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
        """插入推送审核日志"""
        try:
            engine = get_engine()
            sql = text('''INSERT INTO push_review_log (project_name, author, branch, updated_at, commit_messages, score, review_result, additions, deletions)
                         VALUES (:project_name, :author, :branch, :updated_at, :commit_messages, :score, :review_result, :additions, :deletions)''')
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
                    'deletions': entity.deletions
                })
        except Exception as e:
            logger.error(f"Error inserting review log: {e}")

    @staticmethod
    def get_push_review_logs(authors: list = None, project_names: list = None, updated_at_gte: int = None,
                             updated_at_lte: int = None) -> pd.DataFrame:
        """获取符合条件的推送审核日志"""
        try:
            engine = get_engine()
            query = "SELECT project_name, author, branch, updated_at, commit_messages, score, review_result, additions, deletions FROM push_review_log WHERE 1=1"
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

    # -- webhook mapping management --
    @staticmethod
    def create_or_update_webhook_mapping(project_name: str = None, url_slug: str = None, dingtalk_url: str = None,
                                         feishu_url: str = None, wecom_url: str = None):
        """Create or update a project webhook mapping."""
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

                if existing_project and existing_slug:
                    if existing_project['id'] != existing_slug['id']:
                        logger.error("Duplicate mapping exists for project_name or url_slug")
                        return None
                    mapping_id = existing_project['id']
                    conn.execute(upd, {'project_name': project_name, 'url_slug': url_slug, 'dingtalk_url': dingtalk_url, 'feishu_url': feishu_url, 'wecom_url': wecom_url, 'updated_at': now, 'id': mapping_id})
                elif existing_project:
                    mapping_id = existing_project['id']
                    conn.execute(upd, {'project_name': project_name, 'url_slug': url_slug, 'dingtalk_url': dingtalk_url, 'feishu_url': feishu_url, 'wecom_url': wecom_url, 'updated_at': now, 'id': mapping_id})
                elif existing_slug:
                    mapping_id = existing_slug['id']
                    conn.execute(upd, {'project_name': project_name, 'url_slug': url_slug, 'dingtalk_url': dingtalk_url, 'feishu_url': feishu_url, 'wecom_url': wecom_url, 'updated_at': now, 'id': mapping_id})
                else:
                    conn.execute(ins, {'project_name': project_name, 'url_slug': url_slug, 'dingtalk_url': dingtalk_url, 'feishu_url': feishu_url, 'wecom_url': wecom_url, 'created_at': now, 'updated_at': now})
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
<<<<<<< HEAD
import sqlite3

import pandas as pd

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity
=======
import time
import pandas as pd
from sqlalchemy import text

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity
from biz.utils.db import get_engine
from biz.utils.log import logger
>>>>>>> c85976a (feat(通知): 支持每个项目独立通知 Hook；整理并扁平化测试目录)


class ReviewService:
    DB_FILE = "data/data.db"

    @staticmethod
    def init_db():
        """初始化数据库及表结构"""
        try:
<<<<<<< HEAD
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                        CREATE TABLE IF NOT EXISTS mr_review_log (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            project_name TEXT,
                            author TEXT,
                            source_branch TEXT,
                            target_branch TEXT,
                            updated_at INTEGER,
                            commit_messages TEXT,
                            score INTEGER,
                            url TEXT,
                            review_result TEXT,
                            additions INTEGER DEFAULT 0,
                            deletions INTEGER DEFAULT 0,
                            last_commit_id TEXT DEFAULT ''
                        )
                    ''')
                cursor.execute('''
                        CREATE TABLE IF NOT EXISTS push_review_log (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            project_name TEXT,
                            author TEXT,
                            branch TEXT,
                            updated_at INTEGER,
                            commit_messages TEXT,
                            score INTEGER,
                            review_result TEXT,
                            additions INTEGER DEFAULT 0,
                            deletions INTEGER DEFAULT 0
                        )
                    ''')
                # 确保旧版本的mr_review_log、push_review_log表添加additions、deletions列
                tables = ["mr_review_log", "push_review_log"]
                columns = ["additions", "deletions"]
                for table in tables:
                    cursor.execute(f"PRAGMA table_info({table})")
                    current_columns = [col[1] for col in cursor.fetchall()]
                    for column in columns:
                        if column not in current_columns:
                            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} INTEGER DEFAULT 0")

                # 为旧版本的mr_review_log表添加last_commit_id字段
                mr_columns = [
                    {
                        "name": "last_commit_id",
                        "type": "TEXT",
                        "default": "''"
                    }
                ]
                cursor.execute(f"PRAGMA table_info('mr_review_log')")
                current_columns = [col[1] for col in cursor.fetchall()]
                for column in mr_columns:
                    if column.get("name") not in current_columns:
                        cursor.execute(f"ALTER TABLE mr_review_log ADD COLUMN {column.get('name')} {column.get('type')} "
                                       f"DEFAULT {column.get('default')}")

                conn.commit()
                # 添加时间字段索引（默认查询就需要时间范围）
                conn.execute('CREATE INDEX IF NOT EXISTS idx_push_review_log_updated_at ON '
                             'push_review_log (updated_at);')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_mr_review_log_updated_at ON mr_review_log (updated_at);')
        except sqlite3.DatabaseError as e:
            print(f"Database initialization failed: {e}")
=======
            engine = get_engine()
            # 使用 SQLAlchemy metadata 创建表，跨数据库兼容
            from sqlalchemy import MetaData, Table, Column, Integer, Text, UniqueConstraint

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
                Column('last_commit_id', Text, default='')
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
                Column('deletions', Integer, default=0)
            )

            # project_webhooks 表由 WebhookService 管理，但确保存在且添加唯一约束
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
            logger.error(f"Database initialization failed: {e}")
>>>>>>> c85976a (feat(通知): 支持每个项目独立通知 Hook；整理并扁平化测试目录)

    @staticmethod
    def insert_mr_review_log(entity: MergeRequestReviewEntity):
        """插入合并请求审核日志"""
        try:
<<<<<<< HEAD
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                                INSERT INTO mr_review_log (project_name,author, source_branch, target_branch, 
                                updated_at, commit_messages, score, url,review_result, additions, deletions, 
                                last_commit_id)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''',
                               (entity.project_name, entity.author, entity.source_branch,
                                entity.target_branch, entity.updated_at, entity.commit_messages, entity.score,
                                entity.url, entity.review_result, entity.additions, entity.deletions,
                                entity.last_commit_id))
                conn.commit()
        except sqlite3.DatabaseError as e:
            print(f"Error inserting review log: {e}")
=======
            engine = get_engine()
            sql = text('''
                INSERT INTO mr_review_log (project_name, author, source_branch, target_branch, updated_at, commit_messages, score, url, review_result, additions, deletions, last_commit_id)
                VALUES (:project_name, :author, :source_branch, :target_branch, :updated_at, :commit_messages, :score, :url, :review_result, :additions, :deletions, :last_commit_id)
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
                    'last_commit_id': entity.last_commit_id
                })
        except Exception as e:
            logger.error(f"Error inserting review log: {e}")
>>>>>>> c85976a (feat(通知): 支持每个项目独立通知 Hook；整理并扁平化测试目录)

    @staticmethod
    def get_mr_review_logs(authors: list = None, project_names: list = None, updated_at_gte: int = None,
                           updated_at_lte: int = None) -> pd.DataFrame:
        """获取符合条件的合并请求审核日志"""
        try:
<<<<<<< HEAD
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                query = """
                            SELECT project_name, author, source_branch, target_branch, updated_at, commit_messages, score, url, review_result, additions, deletions
                            FROM mr_review_log
                            WHERE 1=1
                            """
                params = []

                if authors:
                    placeholders = ','.join(['?'] * len(authors))
                    query += f" AND author IN ({placeholders})"
                    params.extend(authors)

                if project_names:
                    placeholders = ','.join(['?'] * len(project_names))
                    query += f" AND project_name IN ({placeholders})"
                    params.extend(project_names)

                if updated_at_gte is not None:
                    query += " AND updated_at >= ?"
                    params.append(updated_at_gte)

                if updated_at_lte is not None:
                    query += " AND updated_at <= ?"
                    params.append(updated_at_lte)
                query += " ORDER BY updated_at DESC"
                df = pd.read_sql_query(sql=query, con=conn, params=params)
            return df
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving review logs: {e}")
=======
            engine = get_engine()
            query = "SELECT project_name, author, source_branch, target_branch, updated_at, commit_messages, score, url, review_result, additions, deletions FROM mr_review_log WHERE 1=1"
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
>>>>>>> c85976a (feat(通知): 支持每个项目独立通知 Hook；整理并扁平化测试目录)
            return pd.DataFrame()

    @staticmethod
    def check_mr_last_commit_id_exists(project_name: str, source_branch: str, target_branch: str, last_commit_id: str) -> bool:
        """检查指定项目的Merge Request是否已经存在相同的last_commit_id"""
        try:
<<<<<<< HEAD
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM mr_review_log 
                    WHERE project_name = ? AND source_branch = ? AND target_branch = ? AND last_commit_id = ?
                ''', (project_name, source_branch, target_branch, last_commit_id))
                count = cursor.fetchone()[0]
                return count > 0
        except sqlite3.DatabaseError as e:
            print(f"Error checking last_commit_id: {e}")
=======
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
>>>>>>> c85976a (feat(通知): 支持每个项目独立通知 Hook；整理并扁平化测试目录)
            return False

    @staticmethod
    def insert_push_review_log(entity: PushReviewEntity):
        """插入推送审核日志"""
        try:
<<<<<<< HEAD
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                                INSERT INTO push_review_log (project_name,author, branch, updated_at, commit_messages, score,review_result, additions, deletions)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''',
                               (entity.project_name, entity.author, entity.branch,
                                entity.updated_at, entity.commit_messages, entity.score,
                                entity.review_result, entity.additions, entity.deletions))
                conn.commit()
        except sqlite3.DatabaseError as e:
            print(f"Error inserting review log: {e}")
=======
            engine = get_engine()
            sql = text('''INSERT INTO push_review_log (project_name, author, branch, updated_at, commit_messages, score, review_result, additions, deletions)
                         VALUES (:project_name, :author, :branch, :updated_at, :commit_messages, :score, :review_result, :additions, :deletions)''')
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
                    'deletions': entity.deletions
                })
        except Exception as e:
            logger.error(f"Error inserting review log: {e}")
>>>>>>> c85976a (feat(通知): 支持每个项目独立通知 Hook；整理并扁平化测试目录)

    @staticmethod
    def get_push_review_logs(authors: list = None, project_names: list = None, updated_at_gte: int = None,
                             updated_at_lte: int = None) -> pd.DataFrame:
        """获取符合条件的推送审核日志"""
        try:
<<<<<<< HEAD
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                # 基础查询
                query = """
                    SELECT project_name, author, branch, updated_at, commit_messages, score, review_result, additions, deletions
                    FROM push_review_log
                    WHERE 1=1
                """
                params = []

                # 动态添加 authors 条件
                if authors:
                    placeholders = ','.join(['?'] * len(authors))
                    query += f" AND author IN ({placeholders})"
                    params.extend(authors)

                if project_names:
                    placeholders = ','.join(['?'] * len(project_names))
                    query += f" AND project_name IN ({placeholders})"
                    params.extend(project_names)

                # 动态添加 updated_at_gte 条件
                if updated_at_gte is not None:
                    query += " AND updated_at >= ?"
                    params.append(updated_at_gte)

                # 动态添加 updated_at_lte 条件
                if updated_at_lte is not None:
                    query += " AND updated_at <= ?"
                    params.append(updated_at_lte)

                # 按 updated_at 降序排序
                query += " ORDER BY updated_at DESC"

                # 执行查询
                df = pd.read_sql_query(sql=query, con=conn, params=params)
                return df
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving push review logs: {e}")
            return pd.DataFrame()

=======
            engine = get_engine()
            query = "SELECT project_name, author, branch, updated_at, commit_messages, score, review_result, additions, deletions FROM push_review_log WHERE 1=1"
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

    # -- webhook mapping management --
    @staticmethod
    def create_or_update_webhook_mapping(project_name: str = None, url_slug: str = None, dingtalk_url: str = None,
                                         feishu_url: str = None, wecom_url: str = None):
        """Create or update a project webhook mapping."""
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

                if existing_project and existing_slug:
                    if existing_project['id'] != existing_slug['id']:
                        logger.error("Duplicate mapping exists for project_name or url_slug")
                        return None
                    mapping_id = existing_project['id']
                    conn.execute(upd, {'project_name': project_name, 'url_slug': url_slug, 'dingtalk_url': dingtalk_url, 'feishu_url': feishu_url, 'wecom_url': wecom_url, 'updated_at': now, 'id': mapping_id})
                elif existing_project:
                    mapping_id = existing_project['id']
                    conn.execute(upd, {'project_name': project_name, 'url_slug': url_slug, 'dingtalk_url': dingtalk_url, 'feishu_url': feishu_url, 'wecom_url': wecom_url, 'updated_at': now, 'id': mapping_id})
                elif existing_slug:
                    mapping_id = existing_slug['id']
                    conn.execute(upd, {'project_name': project_name, 'url_slug': url_slug, 'dingtalk_url': dingtalk_url, 'feishu_url': feishu_url, 'wecom_url': wecom_url, 'updated_at': now, 'id': mapping_id})
                else:
                    conn.execute(ins, {'project_name': project_name, 'url_slug': url_slug, 'dingtalk_url': dingtalk_url, 'feishu_url': feishu_url, 'wecom_url': wecom_url, 'created_at': now, 'updated_at': now})
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

>>>>>>> c85976a (feat(通知): 支持每个项目独立通知 Hook；整理并扁平化测试目录)

# Initialize database
ReviewService.init_db()
