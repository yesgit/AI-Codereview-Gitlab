import request from '@/utils/request';
import type { Webhook, WebhookForm } from '@/types';

export const webhookApi = {
  getAll: () => 
    request.get<Webhook[]>('/webhooks'),
  
  create: (data: WebhookForm) => 
    request.post<Webhook>('/webhooks', data),
  
  update: (id: number, data: WebhookForm) => 
    request.put<Webhook>(`/webhooks/${id}`, data),
  
  delete: (id: number) => 
    request.delete(`/webhooks/${id}`),
  
  getDefaultPrompts: () => 
    request.get<{custom_prompt_system: string; custom_prompt_user: string}>('/config/default-prompts'),
};
