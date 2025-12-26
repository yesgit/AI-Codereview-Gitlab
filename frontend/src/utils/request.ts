import axios, { AxiosRequestConfig } from 'axios';
import { message } from 'antd';
import qs from 'qs';

// 使用相对路径，前端和后端在同域名下时无需指定完整 URL
const instance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000,
  paramsSerializer: (params) => {
    return qs.stringify(params, { arrayFormat: 'repeat', skipNulls: true });
  },
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
instance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器 - 返回 response.data
instance.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    const { response } = error;
    
    if (response) {
      const { status, data } = response;
      
      switch (status) {
        case 401:
          message.error('未认证，请重新登录');
          localStorage.removeItem('token');
          window.location.href = '/login';
          break;
        case 403:
          message.error('无权限访问');
          break;
        case 404:
          message.error('请求的资源不存在');
          break;
        case 409:
          message.error(Array.isArray(data.detail) ? data.detail.join('; ') : data.detail || '请求冲突');
          break;
        case 500:
          message.error('服务器错误，请稍后重试');
          break;
        default:
          message.error(data.detail || '请求失败');
      }
    } else {
      message.error('网络错误，请检查网络连接');
    }
    
    return Promise.reject(error);
  }
);

// 包装的请求方法，返回类型为 T 而不是 AxiosResponse
const request = {
  get: <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    return instance.get(url, config);
  },
  post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    return instance.post(url, data, config);
  },
  put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    return instance.put(url, data, config);
  },
  delete: <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    return instance.delete(url, config);
  },
};

export default request;
