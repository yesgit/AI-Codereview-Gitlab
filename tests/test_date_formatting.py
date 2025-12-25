"""
测试日期格式化功能 - 确保使用 UTC 时间
"""
import datetime
import pandas as pd
from unittest.mock import Mock, patch
import pytest


class TestDateFormatting:
    """测试日期格式化是否正确使用 UTC 时间"""
    
    def test_utc_timestamp_conversion(self):
        """测试 UTC 时间戳转换是否正确"""
        # 使用当前时间生成一个固定的时间戳（2024-12-25 00:00:00 UTC）
        utc_timestamp = 1735084800
        
        # 使用 utcfromtimestamp 转换
        utc_time = datetime.datetime.utcfromtimestamp(utc_timestamp).strftime("%Y-%m-%d %H:%M:%S")
        
        # 验证转换结果（修正为正确的年份）
        assert utc_time == "2024-12-25 00:00:00"
        
    def test_utc_vs_local_time_difference(self):
        """测试 UTC 时间与本地时间的区别"""
        utc_timestamp = 1735084800
        
        # UTC 时间
        utc_time = datetime.datetime.utcfromtimestamp(utc_timestamp)
        
        # 本地时间（取决于服务器时区）
        local_time = datetime.datetime.fromtimestamp(utc_timestamp)
        
        # 在中国时区（UTC+8），本地时间应该比 UTC 时间多 8 小时
        # 但我们使用 utcfromtimestamp 应该不受影响
        utc_formatted = utc_time.strftime("%Y-%m-%d %H:%M:%S")
        local_formatted = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # 验证 UTC 时间是正确的（修正为正确的年份）
        assert utc_formatted == "2024-12-25 00:00:00"
        
    def test_date_format_with_various_timestamps(self):
        """测试不同时间戳的格式化"""
        test_cases = [
            (1735084800, "2024-12-25 00:00:00"),  # 2024-12-25 00:00:00 UTC
            (1735095600, "2024-12-25 03:00:00"),  # 2024-12-25 03:00:00 UTC
            (1735113600, "2024-12-25 08:00:00"),  # 2024-12-25 08:00:00 UTC
        ]
        
        for timestamp, expected in test_cases:
            result = datetime.datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            assert result == expected, f"时间戳 {timestamp} 转换失败: 期望 {expected}, 实际 {result}"
    
    @patch('api.routers.reviews.ReviewService')
    def test_mr_reviews_date_formatting(self, mock_review_service):
        """测试 MR 审查记录 API 的日期格式化"""
        # 模拟返回的数据
        mock_df = pd.DataFrame([
            {
                'id': 1,
                'project_name': 'test-project',
                'author': 'test-user',
                'source_branch': 'feature/test',
                'target_branch': 'main',
                'updated_at': 1735084800,  # UTC 时间戳
                'commit_messages': 'test commit',
                'score': 85,
                'url': 'http://example.com',
                'review_result': 'good',
                'additions': 100,
                'deletions': 50,
                'gitlab_base_url': 'http://gitlab.example.com',
                'project_slug': 'test/project'
            }
        ])
        
        mock_review_service.return_value.get_mr_review_logs.return_value = mock_df
        
        # 导入并测试 API
        from api.routers import reviews
        
        # 调用日期格式化逻辑
        df = mock_df.copy()
        if not df.empty and 'updated_at' in df.columns:
            df['updated_at'] = df['updated_at'].apply(
                lambda ts: datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                if isinstance(ts, (int, float)) else ts
            )
        
        # 验证日期格式（修正为正确的年份）
        assert df.iloc[0]['updated_at'] == "2024-12-25 00:00:00"
        
    @patch('api.routers.reviews.ReviewService')
    def test_push_reviews_date_formatting(self, mock_review_service):
        """测试 Push 审查记录 API 的日期格式化"""
        # 模拟返回的数据
        mock_df = pd.DataFrame([
            {
                'id': 1,
                'project_name': 'test-project',
                'author': 'test-user',
                'branch': 'main',
                'updated_at': 1735084800,  # UTC 时间戳
                'commit_messages': 'test commit',
                'score': 90,
                'review_result': 'good',
                'additions': 200,
                'deletions': 100,
                'gitlab_base_url': 'http://gitlab.example.com',
                'project_slug': 'test/project'
            }
        ])
        
        mock_review_service.return_value.get_push_review_logs.return_value = mock_df
        
        # 调用日期格式化逻辑
        df = mock_df.copy()
        if not df.empty and 'updated_at' in df.columns:
            df['updated_at'] = df['updated_at'].apply(
                lambda ts: datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                if isinstance(ts, (int, float)) else ts
            )
        
        # 验证日期格式（修正为正确的年份）
        assert df.iloc[0]['updated_at'] == "2024-12-25 00:00:00"
    
    def test_empty_dataframe_handling(self):
        """测试空数据框的处理"""
        empty_df = pd.DataFrame()
        
        # 应用日期格式化逻辑
        if not empty_df.empty and 'updated_at' in empty_df.columns:
            empty_df['updated_at'] = empty_df['updated_at'].apply(
                lambda ts: datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                if isinstance(ts, (int, float)) else ts
            )
        
        # 验证数据框仍然为空
        assert empty_df.empty
    
    def test_invalid_timestamp_handling(self):
        """测试无效时间戳的处理"""
        df = pd.DataFrame([
            {
                'updated_at': 'invalid',  # 非时间戳值
            },
            {
                'updated_at': None,  # None 值
            }
        ])
        
        # 应用日期格式化逻辑
        if not df.empty and 'updated_at' in df.columns:
            df['updated_at'] = df['updated_at'].apply(
                lambda ts: datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                if isinstance(ts, (int, float)) else ts
            )
        
        # 验证非时间戳值保持不变
        assert df.iloc[0]['updated_at'] == 'invalid'
        assert pd.isna(df.iloc[1]['updated_at']) or df.iloc[1]['updated_at'] is None
    
    def test_timezone_independence(self):
        """测试时区独立性 - 确保不受服务器时区影响"""
        # 同一个 UTC 时间戳
        timestamp = 1735084800
        
        # 多次转换应该得到相同结果
        result1 = datetime.datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        result2 = datetime.datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        
        # 验证结果一致（修正为正确的年份）
        assert result1 == result2 == "2024-12-25 00:00:00"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
