import request from '@/utils/request';
import type { BranchWebhook, BranchWebhookForm } from '@/types';

export const branchWebhookApi = {
  getAll: () => 
    request.get<BranchWebhook[]>('/branch-webhooks'),
  
  create: (data: BranchWebhookForm) => 
    request.post<BranchWebhook>('/branch-webhooks', data),
  
  update: (id: number, data: BranchWebhookForm) => 
    request.put<BranchWebhook>(`/branch-webhooks/${id}`, data),
  
  delete: (id: number) => 
    request.delete(`/branch-webhooks/${id}`),
  
  getDefaultPrompts: () => 
    request.get<{custom_prompt_system: string; custom_prompt_user: string}>('/config/default-prompts'),
  
  getDefaultExtensions: () => 
    request.get<{supported_extensions: string}>('/config/default-extensions'),
};
