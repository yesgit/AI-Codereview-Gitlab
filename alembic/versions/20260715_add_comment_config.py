"""add comment config for project webhooks

支持评论到非默认 GitLab 地址（仓库镜像场景）

Revision ID: 20260715_add_comment_cfg
Revises: 20251226_add_sup_ext
Create Date: 2026-07-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260715_add_comment_cfg'
down_revision = '20251226_add_sup_ext'
branch_labels = None
depends_on = None


def upgrade():
    """为 project_webhooks 表添加 comment 相关字段"""

    conn = op.get_bind()
    inspector = sa.inspect(conn)

    project_columns = [col['name'] for col in inspector.get_columns('project_webhooks')]

    if 'comment_enabled' not in project_columns:
        op.add_column('project_webhooks', sa.Column('comment_enabled', sa.Boolean(), nullable=True, server_default=sa.text('0')))
        print("✅ 已为 project_webhooks 表添加 comment_enabled 字段")

    if 'comment_url' not in project_columns:
        op.add_column('project_webhooks', sa.Column('comment_url', sa.Text(), nullable=True))
        print("✅ 已为 project_webhooks 表添加 comment_url 字段")

    if 'comment_token' not in project_columns:
        op.add_column('project_webhooks', sa.Column('comment_token', sa.Text(), nullable=True))
        print("✅ 已为 project_webhooks 表添加 comment_token 字段")


def downgrade():
    """移除 comment 相关字段"""

    op.drop_column('project_webhooks', 'comment_token')
    op.drop_column('project_webhooks', 'comment_url')
    op.drop_column('project_webhooks', 'comment_enabled')
    print("✅ 已移除 comment 相关字段")
