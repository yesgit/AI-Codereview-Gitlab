"""add comment_project_id for mirror with different project numeric ID

Revision ID: 20260716_add_comment_project_id
Revises: 20260716_add_comment_project_path
Create Date: 2026-07-16

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260716_add_comment_project_id'
down_revision = '20260716_add_comment_project_path'
branch_labels = None
depends_on = None


def upgrade():
    """为 project_webhooks 表添加 comment_project_id 字段"""
    # 检查列是否已存在
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('project_webhooks')]

    if 'comment_project_id' not in columns:
        op.add_column(
            'project_webhooks',
            sa.Column('comment_project_id', sa.Integer, nullable=True)
        )
        print("✅ 已为 project_webhooks 表添加 comment_project_id 字段")


def downgrade():
    """移除 comment_project_id 字段"""
    op.drop_column('project_webhooks', 'comment_project_id')
    print("✅ 已移除 comment_project_id 字段")
