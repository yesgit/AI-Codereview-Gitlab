"""add gitlab_base_url and project_slug to review logs

Revision ID: 20251224_project_slug
Revises: 20251223_branch_webhooks
Create Date: 2025-12-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251224_project_slug'
down_revision = '20251223_branch_webhooks'
branch_labels = None
depends_on = None


def upgrade():
    """为 mr_review_log 和 push_review_log 表添加 gitlab_base_url 和 project_slug 字段"""
    
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # 1. 为 mr_review_log 表添加字段
    mr_columns = [col['name'] for col in inspector.get_columns('mr_review_log')]
    
    if 'gitlab_base_url' not in mr_columns:
        op.add_column('mr_review_log', sa.Column('gitlab_base_url', sa.String(length=255), nullable=True))
    
    if 'project_slug' not in mr_columns:
        op.add_column('mr_review_log', sa.Column('project_slug', sa.String(length=255), nullable=True))
    
    # 2. 为 push_review_log 表添加字段
    push_columns = [col['name'] for col in inspector.get_columns('push_review_log')]
    
    if 'gitlab_base_url' not in push_columns:
        op.add_column('push_review_log', sa.Column('gitlab_base_url', sa.String(length=255), nullable=True))
    
    if 'project_slug' not in push_columns:
        op.add_column('push_review_log', sa.Column('project_slug', sa.String(length=255), nullable=True))


def downgrade():
    """从两个表中移除 gitlab_base_url 和 project_slug 字段"""
    
    op.drop_column('push_review_log', 'project_slug')
    op.drop_column('push_review_log', 'gitlab_base_url')
    op.drop_column('mr_review_log', 'project_slug')
    op.drop_column('mr_review_log', 'gitlab_base_url')
