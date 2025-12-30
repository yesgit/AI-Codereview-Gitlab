export interface User {
  username: string;
}

export interface LoginRequest {
  username: string;
  password: string;
  remember?: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  username: string;
  expires_at: string;
}

export interface Webhook {
  id: number;
  project_name?: string;
  url_slug?: string;
  gitlab_base_url?: string;
  project_slug?: string;
  dingtalk_url?: string;
  feishu_url?: string;
  wecom_url?: string;
  dingtalk_enabled?: boolean;
  feishu_enabled?: boolean;
  wecom_enabled?: boolean;
  custom_prompt_system?: string;
  custom_prompt_user?: string;
  review_style?: string;
  gitlab_token?: string;
  daily_report_enabled?: boolean;
  supported_extensions?: string;
  created_at?: number;
  updated_at?: number;
}

export interface WebhookForm {
  id?: number;
  project_name: string;
  url_slug?: string;
  gitlab_base_url?: string;
  project_slug?: string;
  dingtalk_url?: string;
  feishu_url?: string;
  wecom_url?: string;
  custom_prompt_system?: string;
  custom_prompt_user?: string;
  gitlab_token?: string;
  dingtalk_enabled?: boolean;
  feishu_enabled?: boolean;
  wecom_enabled?: boolean;
  review_style?: string;
  daily_report_enabled?: boolean;
  supported_extensions?: string;
}

export interface BranchWebhook {
  id: number;
  gitlab_base_url: string;
  project_slug: string;
  branch_pattern: string;
  dingtalk_url?: string;
  feishu_url?: string;
  wecom_url?: string;
  dingtalk_enabled?: boolean;
  feishu_enabled?: boolean;
  wecom_enabled?: boolean;
  custom_prompt_system?: string;
  custom_prompt_user?: string;
  review_style?: string;
  gitlab_token?: string;
  daily_report_enabled?: boolean;
  supported_extensions?: string;
  created_at?: number;
  updated_at?: number;
}

export interface BranchWebhookForm {
  gitlab_base_url: string;
  project_slug: string;
  branch_pattern: string;
  dingtalk_url?: string;
  feishu_url?: string;
  wecom_url?: string;
  dingtalk_enabled?: boolean;
  feishu_enabled?: boolean;
  wecom_enabled?: boolean;
  custom_prompt_system?: string;
  custom_prompt_user?: string;
  review_style?: string;
  gitlab_token?: string;
  daily_report_enabled?: boolean;
  supported_extensions?: string;
}

export const ReviewStyleOptions = [
  { label: '专业风格', value: 'professional' },
  { label: '讽刺风格', value: 'sarcastic' },
  { label: '温和风格', value: 'gentle' },
  { label: '幽默风格', value: 'humorous' },
];

export interface ReviewLog {
  id?: number;
  project_name?: string;
  author?: string;
  source_branch?: string;
  target_branch?: string;
  branch?: string;
  updated_at?: string | number;
  commit_messages?: string;
  score?: number;
  url?: string;
  review_result?: string;
  additions?: number;
  deletions?: number;
  last_commit_id?: string;
  gitlab_base_url?: string;
  project_slug?: string;
}

export interface ReviewListResponse {
  data: ReviewLog[];
  total: number;
  average_score: number;
}

export interface StatsResponse {
  mr: {
    total: number;
    average_score: number;
    project_counts: Record<string, number>;
    project_scores: Record<string, number>;
    author_counts: Record<string, number>;
    author_scores: Record<string, number>;
    author_additions: Record<string, number>;
    author_deletions: Record<string, number>;
  };
  push: {
    total: number;
    average_score: number;
    author_counts: Record<string, number>;
    author_scores: Record<string, number>;
  };
}

export interface QueueTask {
  job_id: string;
  created_at: string;
  enqueued_at: string;
  status: string;
  function_name: string;
  event_type?: string;
  project_name?: string;
  author?: string;
  source_branch?: string;
  target_branch?: string;
  branch?: string;
  url?: string;
  changed_files?: number;
  commit_count?: number;
}

export interface ProjectQueueInfo {
  pending: number;
  processing: number;
  tasks: QueueTask[];
}

export interface QueueStatsResponse {
  queue_driver: string;
  supported: boolean;
  message?: string;
  stats?: {
    pending: number;
    processing: number;
    failed: number;
    completed: number;
  };
  by_project?: Record<string, ProjectQueueInfo>;
  total?: number;
}
