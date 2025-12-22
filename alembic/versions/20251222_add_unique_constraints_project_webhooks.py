"""add unique constraints to project_webhooks

Revision ID: 20251222_add_unique_constraints
Revises: 
Create Date: 2025-12-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20251222_add_unique_constraints'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name

    # Try to create unique constraints. Note: SQLite doesn't support ADD CONSTRAINT easily;
    # Alembic may emulate via table copy but in some setups it fails — see instructions below.
    if dialect == 'sqlite':
        # For sqlite, prefer running the provided cleanup script and then recreating the table manually,
        # or use the offline migration tooling. Here we emit a clear exception with guidance.
        raise RuntimeError(
            "SQLite detected: adding unique constraints on existing SQLite tables is not safe automatically. "
            "Please run the provided `scripts/webhook_cleanup.py` to resolve duplicates, then either "
            "(a) drop and recreate `project_webhooks` with unique constraints, or (b) use a SQLite-aware alembic migration tool."
        )

    # For other dialects (MySQL/Postgres), create unique constraints directly
    inspector = inspect(conn)
    cols = [c['name'] for c in inspector.get_columns('project_webhooks')]
    if 'project_name' in cols:
        try:
            op.create_unique_constraint('uix_project_webhooks_project_name', 'project_webhooks', ['project_name'])
        except Exception:
            pass
    if 'url_slug' in cols:
        try:
            op.create_unique_constraint('uix_project_webhooks_url_slug', 'project_webhooks', ['url_slug'])
        except Exception:
            pass


def downgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == 'sqlite':
        raise RuntimeError("SQLite downgrade not supported automatically; manual intervention required.")

    try:
        op.drop_constraint('uix_project_webhooks_project_name', 'project_webhooks', type_='unique')
    except Exception:
        pass
    try:
        op.drop_constraint('uix_project_webhooks_url_slug', 'project_webhooks', type_='unique')
    except Exception:
        pass
