"""extend version_num column to varchar(100)

Revision ID: 20251226_extend_version_num
Revises: 20251225_add_review_style
Create Date: 2025-12-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251226_extend_version_num'
down_revision = '20251225_add_review_style'
branch_labels = None
depends_on = None


def upgrade():
    """扩展 alembic_version 表的 version_num 列到 VARCHAR(100)"""
    
    # 检查 alembic_version 表是否存在
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'alembic_version' in inspector.get_table_names():
        # 获取当前列信息
        columns = inspector.get_columns('alembic_version')
        version_num_col = next((col for col in columns if col['name'] == 'version_num'), None)
        
        if version_num_col:
            current_type = str(version_num_col['type'])
            # 检查当前长度，如果不足 100 则扩展
            if 'varchar(100)' not in current_type.lower():
                op.alter_column('alembic_version', 'version_num',
                              type_=sa.String(length=100),
                              existing_type=sa.String(length=32))
                print("✅ Extended version_num column to VARCHAR(100)")
            else:
                print("ℹ️ version_num column is already VARCHAR(100)")
    else:
        print("ℹ️ alembic_version table does not exist, creating it with VARCHAR(100)")
        op.create_table(
            'alembic_version',
            sa.Column('version_num', sa.String(length=100), nullable=False),
            sa.PrimaryKeyConstraint('version_num')
        )


def downgrade():
    """回滚 version_num 列到 VARCHAR(32)"""
    op.alter_column('alembic_version', 'version_num',
                   type_=sa.String(length=32),
                   existing_type=sa.String(length=100))
