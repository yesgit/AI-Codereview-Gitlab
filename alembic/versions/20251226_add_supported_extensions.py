"""add supported extensions for projects and branches

Revision ID: 20251226_add_sup_ext
Revises: 20251226_add_daily_report_enabled
Create Date: 2025-12-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251226_add_sup_ext'
down_revision = '20251226_add_daily_report_enabled'
branch_labels = None
depends_on = None


def upgrade():
    """为 project_webhooks 和 branch_webhooks 表添加 supported_extensions 字段"""
    
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # 1. 为 project_webhooks 表添加 supported_extensions 字段
    project_columns = [col['name'] for col in inspector.get_columns('project_webhooks')]
    
    if 'supported_extensions' not in project_columns:
        op.add_column('project_webhooks', sa.Column('supported_extensions', sa.Text(), nullable=True))
        print("✅ 已为 project_webhooks 表添加 supported_extensions 字段")
    
    # 2. 为 branch_webhooks 表添加 supported_extensions 字段
    branch_columns = [col['name'] for col in inspector.get_columns('branch_webhooks')]
    
    if 'supported_extensions' not in branch_columns:
        op.add_column('branch_webhooks', sa.Column('supported_extensions', sa.Text(), nullable=True))
        print("✅ 已为 branch_webhooks 表添加 supported_extensions 字段")


def downgrade():
    """移除 supported_extensions 字段"""
    
    op.drop_column('branch_webhooks', 'supported_extensions')
    op.drop_column('project_webhooks', 'supported_extensions')
    print("✅ 已移除 supported_extensions 字段")
