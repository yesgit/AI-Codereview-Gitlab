"""add gitlab_token field

Revision ID: 20251223_gitlab_token
Revises: 20251223_branch_webhooks
Create Date: 2025-12-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251223_gitlab_token'
down_revision = '20251223_branch_webhooks'
branch_labels = None
depends_on = None


def upgrade():
    """为 project_webhooks 和 branch_webhooks 表添加 gitlab_token 字段"""
    
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # 为 project_webhooks 表添加 gitlab_token 字段
    columns = [col['name'] for col in inspector.get_columns('project_webhooks')]
    if 'gitlab_token' not in columns:
        op.add_column('project_webhooks', sa.Column('gitlab_token', sa.Text(), nullable=True))
    
    # 为 branch_webhooks 表添加 gitlab_token 字段
    if 'branch_webhooks' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('branch_webhooks')]
        if 'gitlab_token' not in columns:
            op.add_column('branch_webhooks', sa.Column('gitlab_token', sa.Text(), nullable=True))


def downgrade():
    """删除 gitlab_token 字段"""
    
    # 从 branch_webhooks 表删除 gitlab_token 字段
    op.drop_column('branch_webhooks', 'gitlab_token')
    
    # 从 project_webhooks 表删除 gitlab_token 字段
    op.drop_column('project_webhooks', 'gitlab_token')
