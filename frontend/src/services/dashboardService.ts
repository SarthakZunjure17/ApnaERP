import { api } from './api';
import { ExecutiveDashboardResponse } from '../types/dashboard';

export const dashboardService = {
  async getExecutiveDashboard(asOfDate?: string): Promise<ExecutiveDashboardResponse> {
    const params: Record<string, string> = {};
    if (asOfDate) params.as_of_date = asOfDate;
    const response = await api.get<ExecutiveDashboardResponse>('/api/v1/reports/dashboard', { params });
    return response.data;
  },

  async getRecentAuditLogs(limit: number = 5) {
    try {
      const response = await api.get('/api/v1/audit-logs', { params: { limit } });
      if (Array.isArray(response.data)) return response.data;
      if (response.data?.items) return response.data.items;
      return [];
    } catch {
      return [];
    }
  },
};
