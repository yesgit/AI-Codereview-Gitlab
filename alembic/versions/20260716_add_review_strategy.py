"""add review strategy for per-project config

支持按项目选择评审策略：diff_only 或 agentic

Revision ID: 20260716_add_review_strategy
Revises: 20260715_add_comment_cfg
Create Date: 2026-07-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260716_add_review_strategy'
down_revision = '20260715_add_comment_cfg'
branch_labels = None
depends_on = None


def upgrade():
    """为 project_webhooks 表添加 review_strategy 字段"""

    conn = op.get_bind()
    inspector = sa.inspect(conn)

    project_columns = [col['name'] for col in inspector.get_columns('project_webhooks')]

    if 'review_strategy' not in project_columns:
        op.add_column('project_webhooks', sa.Column(
            'review_strategy', sa.String(20), nullable=False,
            server_default=sa.text("'diff_only'")
        ))
        print("✅ 已为 project_webhooks 表添加 review_strategy 字段")


def downgrade():
    """移除 review_strategy 字段"""

    op.drop_column('project_webhooks', 'review_strategy')
    print("✅ 已移除 review_strategy 字段")
