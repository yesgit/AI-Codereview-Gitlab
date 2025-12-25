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
  gitlab_token?: string;
  created_at?: number;
  updated_at?: number;
}

export interface WebhookForm {
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
  gitlab_token?: string;
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
  gitlab_token?: string;
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
  gitlab_token?: string;
}

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
  };
}
