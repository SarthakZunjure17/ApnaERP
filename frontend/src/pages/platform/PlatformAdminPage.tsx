import React, { useState, useEffect } from 'react';
import {
  Shield,
  Users,
  Key,
  History,
  RefreshCw,
  Search,
  CheckCircle2,
  XCircle,
  Lock,
  UserCheck,
  Server,
  Layers,
} from 'lucide-react';
import { platformService } from '../../services/platformService';
import {
  UserAccountItem,
  RoleItem,
  PermissionItem,
  AuditLogItem,
} from '../../types/platform';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { EmptyState } from '../../components/common/EmptyState';
import { ErrorState } from '../../components/common/ErrorState';
import { KpiCard } from '../../components/common/KpiCard';
import { useToast } from '../../context/ToastContext';

type TabType = 'users' | 'roles' | 'audit';

export const PlatformAdminPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('users');
  const [users, setUsers] = useState<UserAccountItem[]>([]);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [permissions, setPermissions] = useState<PermissionItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const { success, error: toastError } = useToast();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [userList, roleList, permList, logList] = await Promise.all([
        platformService.getUsers(),
        platformService.getRoles(),
        platformService.getPermissions(),
        platformService.getAuditLogs({ limit: 50 }),
      ]);
      setUsers(userList);
      setRoles(roleList);
      setPermissions(permList);
      setAuditLogs(logList);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load platform security and governance data');
    } finally {
      setIsLoading(false);
    }
  };

  const filteredUsers = users.filter(
    (u) =>
      u.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.username?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredLogs = auditLogs.filter(
    (l) =>
      l.action?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      l.resource_type?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      l.user_email?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Platform Administration & Security</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            User access management, role-based access control (RBAC), and enterprise security audit logging
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" icon={<RefreshCw className="w-4 h-4" />} onClick={loadData}>
            Refresh
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard
          title="Registered Users"
          value={users.length}
          icon={<Users className="w-5 h-5 text-blue-600 dark:text-blue-400" />}
          description="Active user credentials"
        />
        <KpiCard
          title="RBAC Roles"
          value={roles.length}
          icon={<Shield className="w-5 h-5 text-purple-600 dark:text-purple-400" />}
          description="Security role definitions"
        />
        <KpiCard
          title="System Permissions"
          value={permissions.length}
          icon={<Key className="w-5 h-5 text-amber-600 dark:text-amber-400" />}
          description="Granular capability tokens"
        />
        <KpiCard
          title="Audit Trail Logs"
          value={auditLogs.length}
          icon={<History className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />}
          description="Recent tracked operations"
        />
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 space-x-2">
        <button
          onClick={() => setActiveTab('users')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'users'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <Users className="w-4 h-4" /> User Accounts ({users.length})
        </button>
        <button
          onClick={() => setActiveTab('roles')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'roles'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <Shield className="w-4 h-4" /> Roles & Permissions ({roles.length})
        </button>
        <button
          onClick={() => setActiveTab('audit')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'audit'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <History className="w-4 h-4" /> Audit Logs ({auditLogs.length})
        </button>
      </div>

      {/* Main Content Area */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8">
            <LoadingState message="Loading platform configuration..." />
          </div>
        ) : error ? (
          <div className="p-8">
            <ErrorState title="Failed to load platform data" message={error} onRetry={loadData} />
          </div>
        ) : (
          <>
            {/* Tab: Users */}
            {activeTab === 'users' && (
              <div className="p-4 space-y-4">
                <div className="relative w-full md:w-80">
                  <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search user by name, email..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-4 py-2 bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                    <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                      <tr>
                        <th className="px-6 py-4">User</th>
                        <th className="px-6 py-4">Username</th>
                        <th className="px-6 py-4">Roles</th>
                        <th className="px-6 py-4">Superuser</th>
                        <th className="px-6 py-4">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                      {filteredUsers.map((u) => (
                        <tr key={u.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                          <td className="px-6 py-4">
                            <div className="font-semibold text-gray-900 dark:text-white">{u.full_name || u.username}</div>
                            <div className="text-xs text-gray-400">{u.email}</div>
                          </td>
                          <td className="px-6 py-4 font-mono text-xs text-gray-700 dark:text-gray-300">
                            {u.username}
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex flex-wrap gap-1">
                              {u.roles?.map((r, idx) => (
                                <span
                                  key={idx}
                                  className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300"
                                >
                                  {r}
                                </span>
                              )) || <span className="text-xs text-gray-400">User</span>}
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            {u.is_superuser ? (
                              <span className="inline-flex items-center gap-1 text-xs font-semibold text-amber-600">
                                <Key className="w-3.5 h-3.5" /> Superuser
                              </span>
                            ) : (
                              <span className="text-xs text-gray-400">Standard</span>
                            )}
                          </td>
                          <td className="px-6 py-4">
                            <StatusBadge
                              status={u.is_active ? 'Active' : 'Inactive'}
                              variant={u.is_active ? 'success' : 'default'}
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Tab: Roles */}
            {activeTab === 'roles' && (
              <div className="p-6 space-y-6">
                <div>
                  <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-3">Security Roles</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {roles.map((r) => (
                      <div
                        key={r.id}
                        className="p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/30 space-y-2"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-gray-900 dark:text-white">{r.name}</span>
                          <StatusBadge status={r.is_active ? 'Active' : 'Inactive'} variant={r.is_active ? 'success' : 'default'} />
                        </div>
                        <p className="text-xs text-gray-500">{r.description || 'System security role'}</p>
                        <div className="text-xs font-mono text-gray-400 pt-2 flex justify-between">
                          <span>Code: {r.code}</span>
                          <span>{r.is_system_role ? 'Built-in' : 'Custom'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-3">Granular Permissions</h3>
                  <div className="overflow-x-auto max-h-96">
                    <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                      <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                        <tr>
                          <th className="px-6 py-3">Permission Name</th>
                          <th className="px-6 py-3">Code</th>
                          <th className="px-6 py-3">Module</th>
                          <th className="px-6 py-3">Description</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                        {permissions.map((p) => (
                          <tr key={p.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                            <td className="px-6 py-3 font-semibold text-gray-900 dark:text-white">{p.name}</td>
                            <td className="px-6 py-3 font-mono text-xs text-blue-600 dark:text-blue-400">{p.code}</td>
                            <td className="px-6 py-3">
                              <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                                {p.module_name}
                              </span>
                            </td>
                            <td className="px-6 py-3 text-xs text-gray-500">{p.description || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* Tab: Audit Logs */}
            {activeTab === 'audit' && (
              <div className="p-4 space-y-4">
                <div className="relative w-full md:w-80">
                  <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search logs by action, user, resource..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-4 py-2 bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                    <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                      <tr>
                        <th className="px-6 py-4">Timestamp</th>
                        <th className="px-6 py-4">User</th>
                        <th className="px-6 py-4">Action</th>
                        <th className="px-6 py-4">Resource</th>
                        <th className="px-6 py-4">IP Address</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                      {filteredLogs.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="px-6 py-8 text-center text-gray-400">
                            No audit logs found.
                          </td>
                        </tr>
                      ) : (
                        filteredLogs.map((l) => (
                          <tr key={l.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                            <td className="px-6 py-4 text-xs text-gray-500">{new Date(l.timestamp).toLocaleString()}</td>
                            <td className="px-6 py-4">
                              <div className="font-semibold text-gray-900 dark:text-white">{l.user_name || 'System User'}</div>
                              {l.user_email && <div className="text-xs text-gray-400">{l.user_email}</div>}
                            </td>
                            <td className="px-6 py-4 font-mono font-bold text-blue-600 dark:text-blue-400 text-xs">
                              {l.action}
                            </td>
                            <td className="px-6 py-4">
                              <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                                {l.resource_type}
                              </span>
                            </td>
                            <td className="px-6 py-4 font-mono text-xs text-gray-400">{l.ip_address || '127.0.0.1'}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
