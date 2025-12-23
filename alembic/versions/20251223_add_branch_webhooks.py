"""add branch webhooks table

Revision ID: 20251223_branch_webhooks
Revises: 20251222_initial
Create Date: 2025-12-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251223_branch_webhooks'
down_revision = '20251222_initial'
branch_labels = None
depends_on = None


def upgrade():
    """创建分支级webhook配置表，并为project_webhooks表添加新字段"""
    
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # 1. 创建 branch_webhooks 表
    if 'branch_webhooks' not in inspector.get_table_names():
        op.create_table(
            'branch_webhooks',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('gitlab_base_url', sa.String(length=255), nullable=False),
            sa.Column('project_slug', sa.String(length=255), nullable=False),
            sa.Column('branch_pattern', sa.String(length=255), nullable=False),
            sa.Column('dingtalk_url', sa.Text(), nullable=True),
            sa.Column('feishu_url', sa.Text(), nullable=True),
            sa.Column('wecom_url', sa.Text(), nullable=True),
            sa.Column('custom_prompt_system', sa.Text(), nullable=True),
            sa.Column('custom_prompt_user', sa.Text(), nullable=True),
            sa.Column('created_at', sa.Integer(), nullable=True),
            sa.Column('updated_at', sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('gitlab_base_url', 'project_slug', 'branch_pattern', 
                              name='uq_branch_webhooks_gitlab_project_branch')
        )
    
    # 2. 为 project_webhooks 表添加新字段（如果不存在）
    columns = [col['name'] for col in inspector.get_columns('project_webhooks')]
    
    if 'gitlab_base_url' not in columns:
        op.add_column('project_webhooks', sa.Column('gitlab_base_url', sa.String(length=255), nullable=True))
    
    if 'project_slug' not in columns:
        op.add_column('project_webhooks', sa.Column('project_slug', sa.String(length=255), nullable=True))


def downgrade():
    """删除分支级webhook配置表，并移除project_webhooks表中的新字段"""
    
    # 删除 branch_webhooks 表
    op.drop_table('branch_webhooks')
    
    # 移除 project_webhooks 表中的新字段
    op.drop_column('project_webhooks', 'project_slug')
    op.drop_column('project_webhooks', 'gitlab_base_url')
