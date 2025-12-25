"""add review style column to branch_webhooks and project_webhooks

Revision ID: 20251225_add_review_style
Revises: 20251225_notification_enabled
Create Date: 2025-12-25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251225_add_review_style'
down_revision = '20251225_notification_enabled'
branch_labels = None
depends_on = None


def upgrade():
    """为 branch_webhooks 和 project_webhooks 表添加 review_style 字段"""
    
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # 为 branch_webhooks 表添加 review_style 字段
    branch_columns = [col['name'] for col in inspector.get_columns('branch_webhooks')]
    if 'review_style' not in branch_columns:
        op.add_column('branch_webhooks', sa.Column('review_style', sa.String(length=50), nullable=True))
    
    # 为 project_webhooks 表添加 review_style 字段
    project_columns = [col['name'] for col in inspector.get_columns('project_webhooks')]
    if 'review_style' not in project_columns:
        op.add_column('project_webhooks', sa.Column('review_style', sa.String(length=50), nullable=True))


def downgrade():
    """移除 review_style 字段"""
    op.drop_column('project_webhooks', 'review_style')
    op.drop_column('branch_webhooks', 'review_style')
