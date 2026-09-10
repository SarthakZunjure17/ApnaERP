export interface UserAccountItem {
  id: string;
  email: string;
  username: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  roles?: string[];
  department?: string;
  designation?: string;
  created_at?: string;
}

export interface RoleItem {
  id: string;
  name: string;
  code: string;
  description?: string;
  is_system_role: boolean;
  is_active: boolean;
  permissions_count?: number;
}

export interface PermissionItem {
  id: string;
  name: string;
  code: string;
  module_name: string;
  description?: string;
}

export interface AuditLogItem {
  id: string;
  user_id?: string;
  user_name?: string;
  user_email?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  timestamp: string;
  ip_address?: string;
  status?: string;
}
