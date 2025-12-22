"""add custom_prompt fields to project_webhooks

Revision ID: 20251222_prompts
Create Date: 2025-12-22 20:35:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251222_prompts'
down_revision = '20251222_add_unique_constraints_project_webhooks'
branch_labels = None
depends_on = None


def upgrade():
    # 添加自定义 prompt 字段到 project_webhooks 表
    op.add_column('project_webhooks', sa.Column('custom_prompt_system', sa.Text(), nullable=True))
    op.add_column('project_webhooks', sa.Column('custom_prompt_user', sa.Text(), nullable=True))


def downgrade():
    # 删除自定义 prompt 字段
    op.drop_column('project_webhooks', 'custom_prompt_user')
    op.drop_column('project_webhooks', 'custom_prompt_system')
