import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Request interceptor to attach JWT token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('apnaerp_access_token') || sessionStorage.getItem('apnaerp_access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor for automatic token refresh on 401
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => {
    // If response data is an HTML document (SPA fallback on invalid/missing route), reject
    if (
      typeof response.data === 'string' &&
      (response.data.includes('<!doctype html>') ||
        response.data.includes('<!DOCTYPE html>') ||
        response.data.includes('<html'))
    ) {
      return Promise.reject(new Error('Invalid response format: Received HTML instead of JSON'));
    }
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      if (originalRequest.url?.includes('/auth/login') || originalRequest.url?.includes('/auth/refresh')) {
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken =
        localStorage.getItem('apnaerp_refresh_token') ||
        sessionStorage.getItem('apnaerp_refresh_token');

      if (!refreshToken) {
        isRefreshing = false;
        return Promise.reject(error);
      }

      try {
        const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token: newRefreshToken } = response.data;
        if (localStorage.getItem('apnaerp_refresh_token')) {
          localStorage.setItem('apnaerp_access_token', access_token);
          if (newRefreshToken) localStorage.setItem('apnaerp_refresh_token', newRefreshToken);
        } else {
          sessionStorage.setItem('apnaerp_access_token', access_token);
          if (newRefreshToken) sessionStorage.setItem('apnaerp_refresh_token', newRefreshToken);
        }

        api.defaults.headers.common.Authorization = `Bearer ${access_token}`;
        processQueue(null, access_token);
        return api(originalRequest);
      } catch (refreshErr) {
        processQueue(refreshErr as Error, null);
        localStorage.removeItem('apnaerp_access_token');
        localStorage.removeItem('apnaerp_refresh_token');
        sessionStorage.removeItem('apnaerp_access_token');
        sessionStorage.removeItem('apnaerp_refresh_token');
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);
