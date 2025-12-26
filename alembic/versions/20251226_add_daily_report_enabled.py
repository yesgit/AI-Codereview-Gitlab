"""add daily_report_enabled to project_webhooks and branch_webhooks

Revision ID: 20251226_add_daily_report_enabled
Revises: 20251225_add_review_style
Create Date: 2025-12-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251226_add_daily_report_enabled'
down_revision = '20251226_extend_version_num'
branch_labels = None
depends_on = None


def logger(msg: str):
    """简单的日志函数"""
    print(msg)


def upgrade():
    """添加 daily_report_enabled 字段到两个表"""
    
    # 检查表和字段是否已存在
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # 1. 为 project_webhooks 表添加 daily_report_enabled 字段
    if 'project_webhooks' in inspector.get_table_names():
        project_columns = [col['name'] for col in inspector.get_columns('project_webhooks')]
        if 'daily_report_enabled' not in project_columns:
            op.add_column('project_webhooks', 
                         sa.Column('daily_report_enabled', sa.Boolean(), nullable=True, server_default='1'))
            logger("✅ Added daily_report_enabled column to project_webhooks")
        else:
            logger("ℹ️ daily_report_enabled column already exists in project_webhooks")
    
    # 2. 为 branch_webhooks 表添加 daily_report_enabled 字段
    if 'branch_webhooks' in inspector.get_table_names():
        branch_columns = [col['name'] for col in inspector.get_columns('branch_webhooks')]
        if 'daily_report_enabled' not in branch_columns:
            op.add_column('branch_webhooks', 
                         sa.Column('daily_report_enabled', sa.Boolean(), nullable=True, server_default='1'))
            logger("✅ Added daily_report_enabled column to branch_webhooks")
        else:
            logger("ℹ️ daily_report_enabled column already exists in branch_webhooks")


def downgrade():
    """删除 daily_report_enabled 字段"""
    
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # 1. 从 project_webhooks 表删除 daily_report_enabled 字段
    if 'project_webhooks' in inspector.get_table_names():
        project_columns = [col['name'] for col in inspector.get_columns('project_webhooks')]
        if 'daily_report_enabled' in project_columns:
            op.drop_column('project_webhooks', 'daily_report_enabled')
            logger("✅ Dropped daily_report_enabled column from project_webhooks")
    
    # 2. 从 branch_webhooks 表删除 daily_report_enabled 字段
    if 'branch_webhooks' in inspector.get_table_names():
        branch_columns = [col['name'] for col in inspector.get_columns('branch_webhooks')]
        if 'daily_report_enabled' in branch_columns:
            op.drop_column('branch_webhooks', 'daily_report_enabled')
            logger("✅ Dropped daily_report_enabled column from branch_webhooks")
