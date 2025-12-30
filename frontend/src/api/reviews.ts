import request from '@/utils/request';
import type { ReviewListResponse, StatsResponse, QueueStatsResponse } from '@/types';

export const reviewsApi = {
  getMrReviews: (params?: {
    authors?: string[];
    project_names?: string[];
    updated_at_gte?: number;
    updated_at_lte?: number;
  }) => 
    request.get<ReviewListResponse>('/reviews/mr', { params }),
  
  getPushReviews: (params?: {
    authors?: string[];
    project_names?: string[];
    updated_at_gte?: number;
    updated_at_lte?: number;
  }) => 
    request.get<ReviewListResponse>('/reviews/push', { params }),
  
  getStats: (params?: {
    authors?: string[];
    project_names?: string[];
    updated_at_gte?: number;
    updated_at_lte?: number;
  }) => 
    request.get<StatsResponse>('/reviews/stats', { params }),

  getQueueStatus: () => 
    request.get<QueueStatsResponse>('/reviews/queue-status'),

  sendDailyReport: () => 
    request.get<{ message: string }>('/review/daily_report', { baseURL: '' }),
};
