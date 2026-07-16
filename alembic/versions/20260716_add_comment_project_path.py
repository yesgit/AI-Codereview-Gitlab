"""add comment_project_path for mirror with different project path

镜像场景：目标库和源库的项目路径可能不同，需独立配置

Revision ID: 20260716_add_comment_project_path
Revises: 20260716_add_review_strategy
Create Date: 2026-07-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260716_add_comment_project_path'
down_revision = '20260716_add_review_strategy'
branch_labels = None
depends_on = None


def upgrade():
    """为 project_webhooks 表添加 comment_project_path 字段"""

    conn = op.get_bind()
    inspector = sa.inspect(conn)

    project_columns = [col['name'] for col in inspector.get_columns('project_webhooks')]

    if 'comment_project_path' not in project_columns:
        op.add_column('project_webhooks', sa.Column(
            'comment_project_path', sa.String(255), nullable=True
        ))
        print("✅ 已为 project_webhooks 表添加 comment_project_path 字段")


def downgrade():
    """移除 comment_project_path 字段"""

    op.drop_column('project_webhooks', 'comment_project_path')
    print("✅ 已移除 comment_project_path 字段")
