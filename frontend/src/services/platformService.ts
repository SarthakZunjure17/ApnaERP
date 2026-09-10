import { api } from './api';
import { UserAccountItem, RoleItem, PermissionItem, AuditLogItem } from '../types/platform';

export const platformService = {
  // Users & RBAC
  async getUsers(): Promise<UserAccountItem[]> {
    const response = await api.get('/api/v1/rbac/users');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async getRoles(): Promise<RoleItem[]> {
    const response = await api.get('/api/v1/rbac/roles');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async getPermissions(): Promise<PermissionItem[]> {
    const response = await api.get('/api/v1/rbac/permissions');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async assignUserRoles(userId: string, roleIds: string[]): Promise<any> {
    const response = await api.post(`/api/v1/rbac/users/${userId}/roles`, { role_ids: roleIds });
    return response.data;
  },

  // Audit Logs
  async getAuditLogs(params?: { limit?: number; action?: string; resource_type?: string }): Promise<AuditLogItem[]> {
    const response = await api.get('/api/v1/audit-logs', { params });
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },
};
