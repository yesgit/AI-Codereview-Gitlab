"""
查询统计 API
"""
from typing import List, Optional, Any, Dict
import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from biz.service.review_service import ReviewService
from biz.service.queue_service import QueueService
from api.routers.auth import get_current_user

router = APIRouter()


class ReviewLogItem(BaseModel):
    id: int
    project_name: str
    author: str
    updated_at: int
    commit_messages: str
    score: int
    review_result: str
    additions: int
    deletions: int


class ReviewStatsResponse(BaseModel):
    total_count: int
    average_score: float


class QueueStatsResponse(BaseModel):
    queue_driver: str
    supported: bool
    message: Optional[str] = None
    stats: Optional[Dict[str, int]] = None
    by_project: Optional[Dict[str, Any]] = None
    total: Optional[int] = None


@router.get("/mr")
async def get_mr_reviews(
    authors: Optional[List[str]] = Query(None),
    project_names: Optional[List[str]] = Query(None),
    updated_at_gte: Optional[int] = Query(None),
    updated_at_lte: Optional[int] = Query(None),
    current_user: str = Depends(get_current_user)
):
    """获取 MR 审查记录"""
    df = ReviewService().get_mr_review_logs(
        authors=authors,
        project_names=project_names,
        updated_at_gte=updated_at_gte,
        updated_at_lte=updated_at_lte
    )
    
    # 将 datetime 转换为可读格式（从 UTC 转换为北京时间 +8小时）
    if not df.empty and 'updated_at' in df.columns:
        df['updated_at'] = df['updated_at'].apply(
            lambda ts: (datetime.datetime.utcfromtimestamp(ts) + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(ts, (int, float)) else ts
        )
    
    return {
        "data": df.to_dict(orient='records'),
        "total": len(df),
        "average_score": float(df['score'].mean()) if not df.empty else 0.0
    }


@router.get("/push")
async def get_push_reviews(
    authors: Optional[List[str]] = Query(None),
    project_names: Optional[List[str]] = Query(None),
    updated_at_gte: Optional[int] = Query(None),
    updated_at_lte: Optional[int] = Query(None),
    current_user: str = Depends(get_current_user)
):
    """获取 Push 审查记录"""
    df = ReviewService().get_push_review_logs(
        authors=authors,
        project_names=project_names,
        updated_at_gte=updated_at_gte,
        updated_at_lte=updated_at_lte
    )
    
    # 将 datetime 转换为可读格式（从 UTC 转换为北京时间 +8小时）
    if not df.empty and 'updated_at' in df.columns:
        df['updated_at'] = df['updated_at'].apply(
            lambda ts: (datetime.datetime.utcfromtimestamp(ts) + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(ts, (int, float)) else ts
        )
    
    return {
        "data": df.to_dict(orient='records'),
        "total": len(df),
        "average_score": float(df['score'].mean()) if not df.empty else 0.0
    }


@router.get("/stats")
async def get_stats(
    authors: Optional[List[str]] = Query(None),
    project_names: Optional[List[str]] = Query(None),
    updated_at_gte: Optional[int] = Query(None),
    updated_at_lte: Optional[int] = Query(None),
    current_user: str = Depends(get_current_user)
):
    """获取统计数据"""
    # MR 统计
    mr_df = ReviewService().get_mr_review_logs(
        authors=authors,
        project_names=project_names,
        updated_at_gte=updated_at_gte,
        updated_at_lte=updated_at_lte
    )
    
    # Push 统计
    push_df = ReviewService().get_push_review_logs(
        authors=authors,
        project_names=project_names,
        updated_at_gte=updated_at_gte,
        updated_at_lte=updated_at_lte
    )
    
    # 项目统计
    mr_project_counts = mr_df['project_name'].value_counts().to_dict() if not mr_df.empty else {}
    mr_project_scores = mr_df.groupby('project_name')['score'].mean().to_dict() if not mr_df.empty else {}
    
    # 人员统计
    mr_author_counts = mr_df['author'].value_counts().to_dict() if not mr_df.empty else {}
    mr_author_scores = mr_df.groupby('author')['score'].mean().to_dict() if not mr_df.empty else {}
    
    # 代码行数统计
    mr_additions = mr_df.groupby('author')['additions'].sum().to_dict() if not mr_df.empty else {}
    mr_deletions = mr_df.groupby('author')['deletions'].sum().to_dict() if not mr_df.empty else {}
    
    return {
        "mr": {
            "total": len(mr_df),
            "average_score": float(mr_df['score'].mean()) if not mr_df.empty else 0.0,
            "project_counts": mr_project_counts,
            "project_scores": mr_project_scores,
            "author_counts": mr_author_counts,
            "author_scores": mr_author_scores,
            "author_additions": mr_additions,
            "author_deletions": mr_deletions
        },
        "push": {
            "total": len(push_df),
            "average_score": float(push_df['score'].mean()) if not push_df.empty else 0.0,
            "author_counts": push_df['author'].value_counts().to_dict() if not push_df.empty else {},
            "author_scores": push_df.groupby('author')['score'].mean().to_dict() if not push_df.empty else {}
        }
    }


@router.get("/queue-status", response_model=QueueStatsResponse)
async def get_queue_status(
    current_user: str = Depends(get_current_user)
):
    """获取队列状态统计（仅支持 Redis Queue 模式）"""
    queue_service = QueueService()
    return queue_service.get_queue_status()
