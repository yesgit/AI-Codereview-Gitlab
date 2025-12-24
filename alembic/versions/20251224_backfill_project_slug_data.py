"""backfill gitlab_base_url and project_slug for existing records

Revision ID: 20251224_backfill
Revises: 20251224_project_slug
Create Date: 2025-12-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251224_backfill'
down_revision = '20251224_project_slug'
branch_labels = None
depends_on = None


def upgrade():
    """为历史数据补全 gitlab_base_url 和 project_slug 字段
    
    注意：由于历史数据中没有这两个值，这里只是做占位处理。
    实际使用时，这些历史记录不会影响新功能的分组发送。
    """
    # 对于 mr_review_log 表
    # 将空的 gitlab_base_url 设置为 'UNKNOWN'，project_slug 设置为 'UNKNOWN'
    # 这样查询时可以识别出这些是历史数据
    conn = op.get_bind()
    
    # 更新 mr_review_log 表
    conn.execute(sa.text("""
        UPDATE mr_review_log 
        SET gitlab_base_url = 'UNKNOWN', project_slug = 'UNKNOWN'
        WHERE gitlab_base_url IS NULL OR gitlab_base_url = ''
           OR project_slug IS NULL OR project_slug = ''
    """))
    
    # 更新 push_review_log 表
    conn.execute(sa.text("""
        UPDATE push_review_log 
        SET gitlab_base_url = 'UNKNOWN', project_slug = 'UNKNOWN'
        WHERE gitlab_base_url IS NULL OR gitlab_base_url = ''
           OR project_slug IS NULL OR project_slug = ''
    """))


def downgrade():
    """将历史数据的新字段重置为 NULL"""
    conn = op.get_bind()
    
    # 重置 mr_review_log 表
    conn.execute(sa.text("""
        UPDATE mr_review_log 
        SET gitlab_base_url = NULL, project_slug = NULL
        WHERE gitlab_base_url = 'UNKNOWN' AND project_slug = 'UNKNOWN'
    """))
    
    # 重置 push_review_log 表
    conn.execute(sa.text("""
        UPDATE push_review_log 
        SET gitlab_base_url = NULL, project_slug = NULL
        WHERE gitlab_base_url = 'UNKNOWN' AND project_slug = 'UNKNOWN'
    """))
