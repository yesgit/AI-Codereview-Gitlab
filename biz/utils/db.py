"""数据库连接工具：支持 sqlite 和 MySQL (PyMySQL)

配置项（从环境变量读取）：
- DB_DRIVER: sqlite (默认) 或 mysql
- DB_FILE: sqlite 文件路径，默认 data/data.db
- DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME: MySQL 连接信息
"""
import os
import time
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from biz.utils.log import logger


@lru_cache()
def get_engine() -> Engine:
    """Create and return a SQLAlchemy engine based on environment configuration.

    Supports sqlite (default) and mysql (pymysql).
    """
    driver = os.environ.get('DB_DRIVER', 'sqlite').lower()
    try:
        if driver == 'mysql':
            user = os.environ.get('DB_USER', 'root')
            password = os.environ.get('DB_PASSWORD', '')
            host = os.environ.get('DB_HOST', '127.0.0.1')
            port = int(os.environ.get('DB_PORT', 3306))
            dbname = os.environ.get('DB_NAME', 'ai_codereview')
            url = f'mysql+pymysql://{user}:{password}@{host}:{port}/{dbname}?charset=utf8mb4'
            engine = create_engine(url, future=True)
            return engine
        else:
            db_file = os.environ.get('DB_FILE', 'data/data.db')
            # ensure directory exists
            dir_path = os.path.dirname(db_file)
            if dir_path and not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path, exist_ok=True)
                except Exception as e:
                    logger.warning(f"Failed to create db directory {dir_path}: {e}")
            url = f'sqlite:///{db_file}'
            engine = create_engine(url, future=True, connect_args={"check_same_thread": False})
            return engine
    except SQLAlchemyError as e:
        logger.error(f"Failed to create DB engine: {e}")
        raise


def get_connection():
    """Return a context manager for a connection from the engine.

    Usage:
        with get_connection() as conn:
            conn.execute(...)
    """
    engine = get_engine()
    return engine.connect()

