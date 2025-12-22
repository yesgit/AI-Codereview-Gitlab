"""initial schema with project_webhooks table

Revision ID: 20251222_initial
Revises: 
Create Date: 2025-12-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251222_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """创建 project_webhooks 表，包含完整结构"""
    
    # 检查表是否已存在
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'project_webhooks' not in inspector.get_table_names():
        op.create_table(
            'project_webhooks',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('project_name', sa.String(length=255), nullable=True),
            sa.Column('url_slug', sa.String(length=255), nullable=True),
            sa.Column('dingtalk_url', sa.Text(), nullable=True),
            sa.Column('feishu_url', sa.Text(), nullable=True),
            sa.Column('wecom_url', sa.Text(), nullable=True),
            sa.Column('custom_prompt_system', sa.Text(), nullable=True),
            sa.Column('custom_prompt_user', sa.Text(), nullable=True),
            sa.Column('created_at', sa.Integer(), nullable=True),
            sa.Column('updated_at', sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('project_name', name='uq_project_webhooks_project_name'),
            sa.UniqueConstraint('url_slug', name='uq_project_webhooks_url_slug')
        )


def downgrade():
    """删除 project_webhooks 表"""
    op.drop_table('project_webhooks')
