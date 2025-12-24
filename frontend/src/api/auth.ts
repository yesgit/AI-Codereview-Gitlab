import request from '@/utils/request';
import type { LoginRequest, LoginResponse, User } from '@/types';

export const authApi = {
  login: (data: LoginRequest) => 
    request.post<LoginResponse>('/auth/login', data),
  
  getCurrentUser: () => 
    request.get<User>('/auth/me'),
};
