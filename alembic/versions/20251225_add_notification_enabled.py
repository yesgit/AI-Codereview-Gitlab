"""add notification enabled fields

Revision ID: 20251225_notification_enabled
Revises: 20251224_backfill
Create Date: 2025-12-25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251225_notification_enabled'
down_revision = '20251224_backfill'
branch_labels = None
depends_on = None


def upgrade():
    """为 project_webhooks 和 branch_webhooks 表添加通知启用字段"""
    
    # 为 project_webhooks 表添加通知启用字段
    op.add_column('project_webhooks', sa.Column('dingtalk_enabled', sa.Boolean(), nullable=True))
    op.add_column('project_webhooks', sa.Column('feishu_enabled', sa.Boolean(), nullable=True))
    op.add_column('project_webhooks', sa.Column('wecom_enabled', sa.Boolean(), nullable=True))
    
    # 为 branch_webhooks 表添加通知启用字段
    op.add_column('branch_webhooks', sa.Column('dingtalk_enabled', sa.Boolean(), nullable=True))
    op.add_column('branch_webhooks', sa.Column('feishu_enabled', sa.Boolean(), nullable=True))
    op.add_column('branch_webhooks', sa.Column('wecom_enabled', sa.Boolean(), nullable=True))


def downgrade():
    """移除 project_webhooks 和 branch_webhooks 表的通知启用字段"""
    
    # 移除 project_webhooks 表的字段
    op.drop_column('project_webhooks', 'wecom_enabled')
    op.drop_column('project_webhooks', 'feishu_enabled')
    op.drop_column('project_webhooks', 'dingtalk_enabled')
    
    # 移除 branch_webhooks 表的字段
    op.drop_column('branch_webhooks', 'wecom_enabled')
    op.drop_column('branch_webhooks', 'feishu_enabled')
    op.drop_column('branch_webhooks', 'dingtalk_enabled')
