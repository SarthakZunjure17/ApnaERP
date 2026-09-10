import React, { useState, useEffect } from 'react';
import {
  BookOpen,
  Plus,
  RefreshCw,
  Search,
  Layers,
  ChevronDown,
  ChevronRight,
  DollarSign,
  Calendar,
  Lock,
  Unlock,
  CheckCircle2,
  FolderTree,
} from 'lucide-react';
import { financeService } from '../../services/financeService';
import {
  ChartOfAccountItem,
  FiscalYearItem,
  FiscalPeriodItem,
  CompanyItem,
} from '../../types/finance';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { EmptyState } from '../../components/common/EmptyState';
import { ErrorState } from '../../components/common/ErrorState';
import { KpiCard } from '../../components/common/KpiCard';
import { useToast } from '../../context/ToastContext';

type TabType = 'accounts' | 'fiscal';

export const ChartOfAccountsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('accounts');
  const [accounts, setAccounts] = useState<ChartOfAccountItem[]>([]);
  const [fiscalYears, setFiscalYears] = useState<FiscalYearItem[]>([]);
  const [fiscalPeriods, setFiscalPeriods] = useState<FiscalPeriodItem[]>([]);
  const [company, setCompany] = useState<CompanyItem | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [isAddAccountModalOpen, setIsAddAccountModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form State
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    account_type: 'Asset' as 'Asset' | 'Liability' | 'Equity' | 'Revenue' | 'Expense',
    account_group: 'Current Assets',
    parent_id: '',
    is_reconciliation: false,
  });

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState('All');
  const { success, error: toastError } = useToast();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [accList, yrList, perList, compData] = await Promise.all([
        financeService.getChartOfAccounts(),
        financeService.getFiscalYears(),
        financeService.getFiscalPeriods(),
        financeService.getCompany(),
      ]);
      setAccounts(accList);
      setFiscalYears(yrList);
      setFiscalPeriods(perList);
      setCompany(compData);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load Chart of Accounts and Fiscal calendars');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.code || !formData.name) {
      toastError('Account code and name are required');
      return;
    }
    setIsSubmitting(true);
    try {
      await financeService.createAccount({
        code: formData.code,
        name: formData.name,
        account_type: formData.account_type,
        account_group: formData.account_group || undefined,
        parent_id: formData.parent_id || undefined,
        is_reconciliation: formData.is_reconciliation,
      });
      success('Account Created', `Account ${formData.code} - ${formData.name} added to CoA.`);
      setIsAddAccountModalOpen(false);
      setFormData({
        code: '',
        name: '',
        account_type: 'Asset',
        account_group: 'Current Assets',
        parent_id: '',
        is_reconciliation: false,
      });
      loadData();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to create ledger account');
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredAccounts = accounts.filter((a) => {
    const matchesSearch =
      a.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.account_group?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = selectedType === 'All' || a.account_type === selectedType;
    return matchesSearch && matchesType;
  });

  const assetAccounts = accounts.filter((a) => a.account_type === 'Asset');
  const liabilityAccounts = accounts.filter((a) => a.account_type === 'Liability');
  const revenueAccounts = accounts.filter((a) => a.account_type === 'Revenue');
  const expenseAccounts = accounts.filter((a) => a.account_type === 'Expense');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">General Ledger & Chart of Accounts</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Standard CoA taxonomy, debit/credit hierarchies, and active fiscal financial periods
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" icon={<RefreshCw className="w-4 h-4" />} onClick={loadData}>
            Refresh
          </Button>
          {activeTab === 'accounts' && (
            <Button
              variant="primary"
              icon={<Plus className="w-4 h-4" />}
              onClick={() => setIsAddAccountModalOpen(true)}
            >
              Add GL Account
            </Button>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard
          title="Total GL Accounts"
          value={accounts.length}
          icon={<BookOpen className="w-5 h-5 text-blue-600 dark:text-blue-400" />}
          description="Configured balance sheet & P&L"
        />
        <KpiCard
          title="Assets & Liabilities"
          value={`${assetAccounts.length} / ${liabilityAccounts.length}`}
          icon={<Layers className="w-5 h-5 text-purple-600 dark:text-purple-400" />}
          description="Balance Sheet Structure"
        />
        <KpiCard
          title="Revenue & Expense"
          value={`${revenueAccounts.length} / ${expenseAccounts.length}`}
          icon={<DollarSign className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />}
          description="Income Statement Classes"
        />
        <KpiCard
          title="Fiscal Periods"
          value={fiscalPeriods.length}
          icon={<Calendar className="w-5 h-5 text-amber-600 dark:text-amber-400" />}
          description="Operating calendar months"
        />
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 space-x-2">
        <button
          onClick={() => setActiveTab('accounts')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'accounts'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <BookOpen className="w-4 h-4" /> Chart of Accounts ({accounts.length})
        </button>
        <button
          onClick={() => setActiveTab('fiscal')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'fiscal'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <Calendar className="w-4 h-4" /> Fiscal Calendar & Periods ({fiscalPeriods.length})
        </button>
      </div>

      {/* Main Content Area */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8">
            <LoadingState message="Loading Chart of Accounts..." />
          </div>
        ) : error ? (
          <div className="p-8">
            <ErrorState title="Failed to load CoA" message={error} onRetry={loadData} />
          </div>
        ) : (
          <>
            {/* Tab: Accounts */}
            {activeTab === 'accounts' && (
              <div className="p-4 space-y-4">
                <div className="flex flex-col md:flex-row gap-3 items-center justify-between">
                  <div className="relative w-full md:w-80">
                    <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                      type="text"
                      placeholder="Search by code, account name..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-9 pr-4 py-2 bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div className="flex items-center gap-2">
                    <select
                      value={selectedType}
                      onChange={(e) => setSelectedType(e.target.value)}
                      className="bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="All">All Types</option>
                      <option value="Asset">Asset</option>
                      <option value="Liability">Liability</option>
                      <option value="Equity">Equity</option>
                      <option value="Revenue">Revenue</option>
                      <option value="Expense">Expense</option>
                    </select>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                    <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                      <tr>
                        <th className="px-6 py-4">Account Code</th>
                        <th className="px-6 py-4">Account Name</th>
                        <th className="px-6 py-4">Class / Type</th>
                        <th className="px-6 py-4">Account Group</th>
                        <th className="px-6 py-4">Reconciliation</th>
                        <th className="px-6 py-4 text-right">Balance ($)</th>
                        <th className="px-6 py-4">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                      {filteredAccounts.length === 0 ? (
                        <tr>
                          <td colSpan={7} className="px-6 py-8 text-center text-gray-400">
                            No chart of accounts matched your filter criteria.
                          </td>
                        </tr>
                      ) : (
                        filteredAccounts.map((a) => (
                          <tr key={a.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                            <td className="px-6 py-4 font-mono font-bold text-gray-900 dark:text-white">
                              {a.code}
                            </td>
                            <td className="px-6 py-4 font-semibold text-gray-900 dark:text-white">{a.name}</td>
                            <td className="px-6 py-4">
                              <span
                                className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                                  a.account_type === 'Asset'
                                    ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                                    : a.account_type === 'Liability'
                                    ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
                                    : a.account_type === 'Equity'
                                    ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                                    : a.account_type === 'Revenue'
                                    ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300'
                                    : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                                }`}
                              >
                                {a.account_type}
                              </span>
                            </td>
                            <td className="px-6 py-4 text-gray-500">{a.account_group || 'General'}</td>
                            <td className="px-6 py-4">
                              {a.is_reconciliation ? (
                                <span className="inline-flex items-center gap-1 text-xs text-emerald-600 font-medium">
                                  <CheckCircle2 className="w-3.5 h-3.5" /> Reconciled
                                </span>
                              ) : (
                                <span className="text-xs text-gray-400">-</span>
                              )}
                            </td>
                            <td className="px-6 py-4 text-right font-mono font-bold text-gray-900 dark:text-white">
                              ${Number(a.current_balance || 0).toFixed(2)}
                            </td>
                            <td className="px-6 py-4">
                              <StatusBadge
                                status={a.is_active ? 'Active' : 'Inactive'}
                                variant={a.is_active ? 'success' : 'default'}
                              />
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Tab: Fiscal Calendar */}
            {activeTab === 'fiscal' && (
              <div className="p-6 space-y-6">
                <div>
                  <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-3">Fiscal Years</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {fiscalYears.map((fy) => (
                      <div
                        key={fy.id}
                        className="p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/30"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-base text-gray-900 dark:text-white">{fy.year_name}</span>
                          <StatusBadge
                            status={fy.is_closed ? 'Closed' : 'Open'}
                            variant={fy.is_closed ? 'default' : 'success'}
                          />
                        </div>
                        <p className="text-xs text-gray-500 mt-2">
                          Duration: {fy.start_date} to {fy.end_date}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-3">Accounting Periods</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                      <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                        <tr>
                          <th className="px-6 py-3">Period Name</th>
                          <th className="px-6 py-3">Number</th>
                          <th className="px-6 py-3">Start Date</th>
                          <th className="px-6 py-3">End Date</th>
                          <th className="px-6 py-3">Lock Status</th>
                          <th className="px-6 py-3">Period Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                        {fiscalPeriods.map((fp) => (
                          <tr key={fp.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                            <td className="px-6 py-3 font-semibold text-gray-900 dark:text-white">{fp.period_name}</td>
                            <td className="px-6 py-3 font-mono">{fp.period_number}</td>
                            <td className="px-6 py-3 text-xs text-gray-500">{fp.start_date}</td>
                            <td className="px-6 py-3 text-xs text-gray-500">{fp.end_date}</td>
                            <td className="px-6 py-3">
                              {fp.is_locked ? (
                                <span className="inline-flex items-center gap-1 text-xs text-amber-600">
                                  <Lock className="w-3.5 h-3.5" /> Locked
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 text-xs text-emerald-600">
                                  <Unlock className="w-3.5 h-3.5" /> Unlocked
                                </span>
                              )}
                            </td>
                            <td className="px-6 py-3">
                              <StatusBadge
                                status={fp.is_closed ? 'Closed' : 'Open'}
                                variant={fp.is_closed ? 'default' : 'success'}
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Modal: Add Account */}
      <Modal
        isOpen={isAddAccountModalOpen}
        onClose={() => setIsAddAccountModalOpen(false)}
        title="Add General Ledger Account"
        size="md"
      >
        <form onSubmit={handleCreateAccount} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Account Code *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. 1010"
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Account Class *
              </label>
              <select
                value={formData.account_type}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    account_type: e.target.value as 'Asset' | 'Liability' | 'Equity' | 'Revenue' | 'Expense',
                  })
                }
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                <option value="Asset">Asset</option>
                <option value="Liability">Liability</option>
                <option value="Equity">Equity</option>
                <option value="Revenue">Revenue</option>
                <option value="Expense">Expense</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
              Account Name *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Operating Bank Account"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
              Account Group
            </label>
            <input
              type="text"
              placeholder="e.g. Current Assets / Cash & Equivalents"
              value={formData.account_group}
              onChange={(e) => setFormData({ ...formData, account_group: e.target.value })}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-center gap-2 pt-2">
            <input
              type="checkbox"
              id="is_reconciliation"
              checked={formData.is_reconciliation}
              onChange={(e) => setFormData({ ...formData, is_reconciliation: e.target.checked })}
              className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
            />
            <label htmlFor="is_reconciliation" className="text-sm text-gray-700 dark:text-gray-300">
              Enable for Bank / Ledger Reconciliation
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsAddAccountModalOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={isSubmitting}>
              Create GL Account
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
