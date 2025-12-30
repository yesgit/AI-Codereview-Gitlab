"""
测试 Push 统计 API
"""
import pytest
import os
import sys
import time

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from biz.service.review_service import ReviewService
from biz.entity.review_entity import PushReviewEntity
from api.routers.reviews import get_stats


def setup_module():
    """测试前设置 - 使用内存数据库"""
    os.environ['DB_DRIVER'] = 'sqlite'
    os.environ['DB_FILE'] = ':memory:'
    try:
        from biz.utils.db import get_engine
        get_engine.cache_clear()
    except Exception:
        pass
    ReviewService.init_db()


class TestPushStats:
    """测试 Push 统计 API"""
    
    @pytest.mark.asyncio
    async def test_push_stats_has_project_data(self):
        """测试 Push 统计包含项目维度数据"""
        # 先插入一些测试数据
        now = int(time.time())
        
        test_data = [
            PushReviewEntity(
                project_name="test-project-1",
                author="user1",
                branch="main",
                updated_at=now,
                commits=[{"message": "Test commit 1"}],
                score=80,
                review_result="Review result 1",
                url_slug="default",
                webhook_data={},
                additions=100,
                deletions=50,
                gitlab_base_url="https://gitlab.example.com",
                project_slug="test-project-1"
            ),
            PushReviewEntity(
                project_name="test-project-1",
                author="user2",
                branch="feature",
                updated_at=now,
                commits=[{"message": "Test commit 2"}],
                score=90,
                review_result="Review result 2",
                url_slug="default",
                webhook_data={},
                additions=200,
                deletions=100,
                gitlab_base_url="https://gitlab.example.com",
                project_slug="test-project-1"
            ),
            PushReviewEntity(
                project_name="test-project-2",
                author="user1",
                branch="main",
                updated_at=now,
                commits=[{"message": "Test commit 3"}],
                score=70,
                review_result="Review result 3",
                url_slug="default",
                webhook_data={},
                additions=150,
                deletions=75,
                gitlab_base_url="https://gitlab.example.com",
                project_slug="test-project-2"
            ),
        ]
        
        for entity in test_data:
            ReviewService().insert_push_review_log(entity)
        
        # 获取统计数据 - 直接调用函数，传入 mock 用户
        data = await get_stats(
            authors=None,
            project_names=None,
            updated_at_gte=None,
            updated_at_lte=None,
            current_user="test_user"
        )
        
        # 验证 Push 统计包含项目维度
        assert 'push' in data
        assert 'project_counts' in data['push']
        assert 'project_scores' in data['push']
        
        # 验证项目统计数据
        project_counts = data['push']['project_counts']
        project_scores = data['push']['project_scores']
        
        assert 'test-project-1' in project_counts
        assert 'test-project-2' in project_counts
        
        # test-project-1 有 2 条记录
        assert project_counts['test-project-1'] == 2
        
        # test-project-2 有 1 条记录
        assert project_counts['test-project-2'] == 1
        
        # 验证项目评分
        assert 'test-project-1' in project_scores
        assert 'test-project-2' in project_scores
        
        # test-project-1 平均分: (80 + 90) / 2 = 85
        assert abs(project_scores['test-project-1'] - 85.0) < 0.01
        
        # test-project-2 平均分: 70
        assert abs(project_scores['test-project-2'] - 70.0) < 0.01
        
        print("✅ 测试通过：Push 统计包含项目维度数据")
        print(f"项目统计: {project_counts}")
        print(f"项目评分: {project_scores}")
    
    @pytest.mark.asyncio
    async def test_push_stats_empty_data(self):
        """测试空数据时的 Push 统计"""
        # 获取统计（空数据）
        data = await get_stats(
            authors=None,
            project_names=None,
            updated_at_gte=None,
            updated_at_lte=None,
            current_user="test_user"
        )
        
        # 验证即使没有数据，结构也是完整的
        assert 'push' in data
        assert 'project_counts' in data['push']
        assert 'project_scores' in data['push']
        assert isinstance(data['push']['project_counts'], dict)
        assert isinstance(data['push']['project_scores'], dict)
        
        print("✅ 测试通过：空数据时 Push 统计结构正确")
    
    @pytest.mark.asyncio
    async def test_push_stats_structure_consistency_with_mr(self):
        """测试 Push 统计结构与 MR 统计一致"""
        data = await get_stats(
            authors=None,
            project_names=None,
            updated_at_gte=None,
            updated_at_lte=None,
            current_user="test_user"
        )
        
        # 验证 MR 和 Push 都包含相同的字段
        assert 'mr' in data
        assert 'push' in data
        
        mr_fields = set(data['mr'].keys())
        push_fields = set(data['push'].keys())
        
        # 两个统计都应该包含项目统计字段
        assert 'project_counts' in mr_fields
        assert 'project_scores' in mr_fields
        assert 'project_counts' in push_fields
        assert 'project_scores' in push_fields
        
        # 两个统计都应该包含作者统计字段
        assert 'author_counts' in mr_fields
        assert 'author_scores' in mr_fields
        assert 'author_counts' in push_fields
        assert 'author_scores' in push_fields
        
        # 两个统计都应该包含总数和平均分
        assert 'total' in mr_fields
        assert 'average_score' in mr_fields
        assert 'total' in push_fields
        assert 'average_score' in push_fields
        
        print("✅ 测试通过：Push 统计结构与 MR 统计一致")
        print(f"MR 字段: {sorted(mr_fields)}")
        print(f"Push 字段: {sorted(push_fields)}")


if __name__ == '__main__':
    # 运行测试
    import pytest
    pytest.main([__file__, "-v"])
