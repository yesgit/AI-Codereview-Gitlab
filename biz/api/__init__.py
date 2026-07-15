"""
API 应用初始化模块（已迁移到 FastAPI，保留 push_review_enabled 供兼容）
"""
import os

# 全局配置
push_review_enabled = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'