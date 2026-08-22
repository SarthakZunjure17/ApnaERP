import { api } from './api';
import { LoginPayload, TokenResponse, User } from '../types/auth';

const DEMO_USERS: Record<string, User> = {
  'admin@apnaerp.com': {
    id: 'e0123456-789a-bcde-f012-3456789abcde',
    email: 'admin@apnaerp.com',
    username: 'admin',
    full_name: 'ERP Admin',
    is_active: true,
    is_superuser: true,
    roles: ['SuperAdmin', 'FinanceDirector'],
    department: 'Executive Office',
    designation: 'System Overlord',
  },
  'sarah.j@apnaerp.com': {
    id: 'a1234567-89ab-cdef-0123-456789abcdef',
    email: 'sarah.j@apnaerp.com',
    username: 'sarah.jenkins',
    full_name: 'Sarah Jenkins',
    is_active: true,
    is_superuser: false,
    roles: ['EngineeringManager'],
    department: 'Engineering',
    designation: 'Senior Frontend Dev',
  },
  'amit.patel@apnaerp.com': {
    id: 'b2345678-9abc-def0-1234-56789abcdef0',
    email: 'amit.patel@apnaerp.com',
    username: 'amit.patel',
    full_name: 'Amit Patel',
    is_active: true,
    is_superuser: false,
    roles: ['StaffEngineer'],
    department: 'Engineering',
    designation: 'Senior Software Engineer',
  },
};

export const authService = {
  async login(payload: LoginPayload): Promise<{ tokens: TokenResponse; user: User }> {
    try {
      // 1. Try real backend API call
      const response = await api.post<TokenResponse>('/api/v1/auth/login', {
        username_or_email: payload.username_or_email,
        password: payload.password,
      });

      const tokens = response.data;
      
      // Store token temporarily for next call
      api.defaults.headers.common.Authorization = `Bearer ${tokens.access_token}`;

      // Fetch user profile from /auth/me or /api/v1/auth/me
      let user: User;
      try {
        const userRes = await api.get<User>('/api/v1/auth/me');
        user = userRes.data;
      } catch {
        // Fallback user details if me endpoint fails
        user = {
          id: 'user-' + Date.now(),
          email: payload.username_or_email,
          username: payload.username_or_email.split('@')[0],
          full_name: 'ApnaERP User',
          is_active: true,
          is_superuser: true,
          roles: ['Admin'],
          department: 'Executive Office',
          designation: 'System Overlord',
        };
      }

      return { tokens, user };
    } catch (error: any) {
      // If backend responded with 401/400 (explicit authentication error), rethrow it
      if (error.response?.status === 401 || error.response?.status === 400) {
        throw new Error(error.response.data?.detail || 'Invalid username or password');
      }

      // Check if it matches Demo Credentials for offline/standalone preview
      const normalized = payload.username_or_email.toLowerCase().trim();
      const matchedUser = DEMO_USERS[normalized] || DEMO_USERS['admin@apnaerp.com'];

      if (payload.password === 'admin123' || payload.password === 'password123' || payload.password === 'admin' || payload.password === 'password') {
        const mockTokens: TokenResponse = {
          access_token: 'mock_jwt_access_token_' + Date.now(),
          refresh_token: 'mock_jwt_refresh_token_' + Date.now(),
          token_type: 'bearer',
        };
        return { tokens: mockTokens, user: matchedUser };
      }

      // If backend network error and not valid demo password
      if (error.code === 'ERR_NETWORK' || error.message?.includes('Network Error') || !error.response) {
        throw new Error('Backend server is unreachable. Use demo password (admin123) for offline preview.');
      }

      throw new Error(error.response?.data?.detail || error.message || 'Authentication failed');
    }
  },

  async getCurrentUser(): Promise<User> {
    try {
      const res = await api.get<User>('/api/v1/auth/me');
      return res.data;
    } catch {
      // Return cached or default user
      const stored = localStorage.getItem('apnaerp_user_profile') || sessionStorage.getItem('apnaerp_user_profile');
      if (stored) {
        return JSON.parse(stored);
      }
      return DEMO_USERS['admin@apnaerp.com'];
    }
  },

  async logout(): Promise<void> {
    try {
      await api.post('/api/v1/auth/logout');
    } catch {
      // Ignore errors on logout
    } finally {
      localStorage.removeItem('apnaerp_access_token');
      localStorage.removeItem('apnaerp_refresh_token');
      localStorage.removeItem('apnaerp_user_profile');
      sessionStorage.removeItem('apnaerp_access_token');
      sessionStorage.removeItem('apnaerp_refresh_token');
      sessionStorage.removeItem('apnaerp_user_profile');
      delete api.defaults.headers.common.Authorization;
    }
  },
};
