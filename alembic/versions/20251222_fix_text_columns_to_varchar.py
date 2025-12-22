"""fix TEXT columns to VARCHAR for MySQL UNIQUE constraints

Revision ID: 20251222_fix_text_columns
Revises: 20251222_add_custom_prompts
Create Date: 2025-12-22
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251222_fix_text_columns'
down_revision = '20251222_add_custom_prompts'
branch_labels = None
depends_on = None


def upgrade():
    """将 project_name 和 url_slug 从 TEXT 改为 VARCHAR(255)
    
    MySQL 不支持对 TEXT 列创建 UNIQUE 索引，必须使用 VARCHAR
    """
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == 'mysql':
        # MySQL: 修改列类型
        op.alter_column('project_webhooks', 'project_name',
                       existing_type=sa.Text(),
                       type_=sa.String(255),
                       existing_nullable=True)
        op.alter_column('project_webhooks', 'url_slug',
                       existing_type=sa.Text(),
                       type_=sa.String(255),
                       existing_nullable=True)
    elif dialect == 'sqlite':
        # SQLite 不需要修改，TEXT 可以有 UNIQUE 约束
        pass
    else:
        # PostgreSQL 等其他数据库
        op.alter_column('project_webhooks', 'project_name',
                       existing_type=sa.Text(),
                       type_=sa.String(255),
                       existing_nullable=True)
        op.alter_column('project_webhooks', 'url_slug',
                       existing_type=sa.Text(),
                       type_=sa.String(255),
                       existing_nullable=True)


def downgrade():
    """回退到 TEXT 类型"""
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == 'mysql':
        op.alter_column('project_webhooks', 'project_name',
                       existing_type=sa.String(255),
                       type_=sa.Text(),
                       existing_nullable=True)
        op.alter_column('project_webhooks', 'url_slug',
                       existing_type=sa.String(255),
                       type_=sa.Text(),
                       existing_nullable=True)
    elif dialect == 'sqlite':
        pass
    else:
        op.alter_column('project_webhooks', 'project_name',
                       existing_type=sa.String(255),
                       type_=sa.Text(),
                       existing_nullable=True)
        op.alter_column('project_webhooks', 'url_slug',
                       existing_type=sa.String(255),
                       type_=sa.Text(),
                       existing_nullable=True)
