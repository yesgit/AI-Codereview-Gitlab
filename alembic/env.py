import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Ensure project root is on sys.path so project imports work when alembic runs
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import project's engine factory. This allows alembic to use the same DB settings as the app.
try:
    from biz.utils.db import get_engine
except Exception:
    get_engine = None

# this is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
logger = None
import logging
logger = logging.getLogger('alembic.env')

# If you have SQLAlchemy models with metadata, import them here and set target_metadata.
# e.g. from biz.models import Base
# target_metadata = Base.metadata
target_metadata = None


def _get_sqlalchemy_url_from_engine():
    if get_engine is None:
        return None
    try:
        engine = get_engine()
        # engine.url is a URL object; convert to string
        return str(engine.url)
    except Exception:
        return None


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine, though the
    URL is pulled from the project's engine if available.
    """
    url = config.get_main_option('sqlalchemy.url') or _get_sqlalchemy_url_from_engine()
    if not url:
        raise RuntimeError('No sqlalchemy.url configured for offline migrations')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    # Prefer the project's engine when available to reuse same connection settings
    engine = None
    if get_engine is not None:
        try:
            engine = get_engine()
        except Exception:
            engine = None

    if engine is not None:
        connectable = engine
    else:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section),
            prefix='sqlalchemy.',
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
