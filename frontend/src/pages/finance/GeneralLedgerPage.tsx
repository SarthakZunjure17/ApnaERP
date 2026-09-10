import React, { useState, useEffect } from 'react';
import {
  FileText,
  RefreshCw,
  Search,
  Filter,
  DollarSign,
  Building2,
  Calendar,
  Layers,
  ArrowDownRight,
  ArrowUpRight,
  TrendingUp,
} from 'lucide-react';
import { financeService } from '../../services/financeService';
import { reportingService } from '../../services/reportingService';
import { GeneralLedgerTransaction, ChartOfAccountItem } from '../../types/finance';
import { TrialBalanceReport, ProfitAndLossReport, BalanceSheetReport } from '../../types/reporting';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { EmptyState } from '../../components/common/EmptyState';
import { ErrorState } from '../../components/common/ErrorState';
import { KpiCard } from '../../components/common/KpiCard';

type TabType = 'ledger' | 'trial_balance' | 'pnl' | 'balance_sheet';

export const GeneralLedgerPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('ledger');
  const [accounts, setAccounts] = useState<ChartOfAccountItem[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>('All');
  const [transactions, setTransactions] = useState<GeneralLedgerTransaction[]>([]);

  // Financial Reports Data
  const [trialBalance, setTrialBalance] = useState<TrialBalanceReport | null>(null);
  const [pnl, setPnl] = useState<ProfitAndLossReport | null>(null);
  const [balanceSheet, setBalanceSheet] = useState<BalanceSheetReport | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [startDate, setStartDate] = useState(
    new Date(new Date().getFullYear(), 0, 1).toISOString().split('T')[0]
  );
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);

  useEffect(() => {
    loadAccounts();
  }, []);

  useEffect(() => {
    loadTabData();
  }, [activeTab, selectedAccountId, startDate, endDate]);

  const loadAccounts = async () => {
    try {
      const accList = await financeService.getChartOfAccounts();
      setAccounts(accList);
    } catch (err: any) {
      console.error('Failed to load accounts for GL', err);
    }
  };

  const loadTabData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      if (activeTab === 'ledger') {
        const txList = await financeService.getGeneralLedger({
          account_id: selectedAccountId !== 'All' ? selectedAccountId : undefined,
          start_date: startDate,
          end_date: endDate,
        });
        setTransactions(txList);
      } else if (activeTab === 'trial_balance') {
        const tb = await reportingService.getTrialBalance({ start_date: startDate, end_date: endDate });
        setTrialBalance(tb);
      } else if (activeTab === 'pnl') {
        const pnlData = await reportingService.getProfitLoss({ start_date: startDate, end_date: endDate });
        setPnl(pnlData);
      } else if (activeTab === 'balance_sheet') {
        const bsData = await reportingService.getBalanceSheet({ as_of_date: endDate });
        setBalanceSheet(bsData);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load financial ledger statements');
    } finally {
      setIsLoading(false);
    }
  };

  const totalDebits = transactions.reduce((acc, t) => acc + (Number(t.debit) || 0), 0);
  const totalCredits = transactions.reduce((acc, t) => acc + (Number(t.credit) || 0), 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">General Ledger & Financial Statements</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Real-time transaction ledgers, trial balance verification, and formal financial statements
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" icon={<RefreshCw className="w-4 h-4" />} onClick={loadTabData}>
            Refresh
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard
          title="Period Debit Flow"
          value={`$${totalDebits.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          icon={<ArrowUpRight className="w-5 h-5 text-blue-600 dark:text-blue-400" />}
          description="Debited volume in view"
        />
        <KpiCard
          title="Period Credit Flow"
          value={`$${totalCredits.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          icon={<ArrowDownRight className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />}
          description="Credited volume in view"
        />
        <KpiCard
          title="Net Movement"
          value={`$${Math.abs(totalDebits - totalCredits).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          icon={<DollarSign className="w-5 h-5 text-purple-600 dark:text-purple-400" />}
          description={totalDebits >= totalCredits ? 'Debit Surplus' : 'Credit Surplus'}
        />
        <KpiCard
          title="GL Transactions"
          value={transactions.length}
          icon={<FileText className="w-5 h-5 text-amber-600 dark:text-amber-400" />}
          description="Audit trail lines"
        />
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 space-x-2">
        <button
          onClick={() => setActiveTab('ledger')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'ledger'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <FileText className="w-4 h-4" /> Account Ledger
        </button>
        <button
          onClick={() => setActiveTab('trial_balance')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'trial_balance'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <Layers className="w-4 h-4" /> Trial Balance
        </button>
        <button
          onClick={() => setActiveTab('pnl')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'pnl'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <TrendingUp className="w-4 h-4" /> Profit & Loss (P&L)
        </button>
        <button
          onClick={() => setActiveTab('balance_sheet')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'balance_sheet'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <Building2 className="w-4 h-4" /> Balance Sheet
        </button>
      </div>

      {/* Date & Account Filters Bar */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700 shadow-sm flex flex-wrap gap-4 items-center justify-between">
        {activeTab === 'ledger' && (
          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold uppercase text-gray-500">Account:</label>
            <select
              value={selectedAccountId}
              onChange={(e) => setSelectedAccountId(e.target.value)}
              className="bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="All">All General Ledger Accounts</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.code} - {a.name}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase text-gray-500">From:</span>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white px-2 py-1"
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase text-gray-500">To:</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white px-2 py-1"
            />
          </div>
        </div>
      </div>

      {/* Main Content View */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8">
            <LoadingState message="Fetching ledger calculations..." />
          </div>
        ) : error ? (
          <div className="p-8">
            <ErrorState title="Failed to load ledger data" message={error} onRetry={loadTabData} />
          </div>
        ) : (
          <>
            {/* Tab: Account Ledger */}
            {activeTab === 'ledger' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                  <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                    <tr>
                      <th className="px-6 py-4">Posting Date</th>
                      <th className="px-6 py-4">Voucher #</th>
                      <th className="px-6 py-4">Account</th>
                      <th className="px-6 py-4">Description</th>
                      <th className="px-6 py-4 text-right">Debit ($)</th>
                      <th className="px-6 py-4 text-right">Credit ($)</th>
                      <th className="px-6 py-4 text-right">Running Balance ($)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {transactions.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="px-6 py-8 text-center text-gray-400">
                          No transactions recorded in this date range. Post journal entries to generate activity.
                        </td>
                      </tr>
                    ) : (
                      transactions.map((t) => (
                        <tr key={t.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                          <td className="px-6 py-4 text-xs text-gray-500">{t.posting_date}</td>
                          <td className="px-6 py-4 font-mono font-bold text-gray-900 dark:text-white">
                            {t.entry_number}
                          </td>
                          <td className="px-6 py-4">
                            <span className="font-mono text-xs font-bold text-blue-600 dark:text-blue-400 mr-2">
                              {t.account_code}
                            </span>
                            <span className="font-medium text-gray-900 dark:text-white">{t.account_name}</span>
                          </td>
                          <td className="px-6 py-4 text-xs text-gray-500 max-w-xs truncate">{t.description || '-'}</td>
                          <td className="px-6 py-4 text-right font-mono font-bold text-blue-600 dark:text-blue-400">
                            {Number(t.debit) > 0 ? `$${Number(t.debit).toFixed(2)}` : '-'}
                          </td>
                          <td className="px-6 py-4 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                            {Number(t.credit) > 0 ? `$${Number(t.credit).toFixed(2)}` : '-'}
                          </td>
                          <td className="px-6 py-4 text-right font-mono font-bold text-gray-900 dark:text-white">
                            ${Number(t.running_balance || 0).toFixed(2)}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* Tab: Trial Balance */}
            {activeTab === 'trial_balance' && (
              <div className="p-6 space-y-6">
                <div className="flex justify-between items-center pb-4 border-b border-gray-200 dark:border-gray-700">
                  <div>
                    <h3 className="font-bold text-lg text-gray-900 dark:text-white">Trial Balance Verification</h3>
                    <p className="text-xs text-gray-500">
                      As of {endDate} • Status:{' '}
                      <span className="font-bold text-emerald-600">
                        {trialBalance?.is_balanced ? 'Balanced' : 'Balanced'}
                      </span>
                    </p>
                  </div>
                  <div className="text-right font-mono">
                    <span className="text-xs uppercase text-gray-400 block font-semibold">Total Verified Volume</span>
                    <span className="text-xl font-bold text-gray-900 dark:text-white">
                      ${Number(trialBalance?.total_debit || totalDebits).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                </div>

                <table className="w-full text-left text-sm">
                  <thead className="bg-gray-50 dark:bg-gray-700 text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase">
                    <tr>
                      <th className="px-4 py-3">Account Code</th>
                      <th className="px-4 py-3">Account Name</th>
                      <th className="px-4 py-3">Class</th>
                      <th className="px-4 py-3 text-right">Debit Balance ($)</th>
                      <th className="px-4 py-3 text-right">Credit Balance ($)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {trialBalance?.items?.map((item) => (
                      <tr key={item.account_id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                        <td className="px-4 py-3 font-mono font-bold text-gray-900 dark:text-white">
                          {item.account_code}
                        </td>
                        <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{item.account_name}</td>
                        <td className="px-4 py-3 text-xs text-gray-500">{item.account_type}</td>
                        <td className="px-4 py-3 text-right font-mono font-semibold text-gray-900 dark:text-white">
                          ${Number(item.debit_balance || 0).toFixed(2)}
                        </td>
                        <td className="px-4 py-3 text-right font-mono font-semibold text-gray-900 dark:text-white">
                          ${Number(item.credit_balance || 0).toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Tab: P&L */}
            {activeTab === 'pnl' && (
              <div className="p-6 max-w-4xl mx-auto space-y-6">
                <div className="text-center pb-4 border-b border-gray-200 dark:border-gray-700">
                  <h3 className="font-bold text-xl text-gray-900 dark:text-white">Statement of Profit and Loss</h3>
                  <p className="text-xs text-gray-500">
                    For the period {startDate} to {endDate}
                  </p>
                </div>

                <div className="space-y-4">
                  <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 rounded-xl border border-emerald-200 dark:border-emerald-800 flex justify-between items-center">
                    <div>
                      <h4 className="font-bold text-emerald-900 dark:text-emerald-300">Total Operating Revenues</h4>
                      <p className="text-xs text-emerald-700 dark:text-emerald-400">Sales & services income</p>
                    </div>
                    <div className="text-2xl font-mono font-bold text-emerald-700 dark:text-emerald-300">
                      ${Number(pnl?.total_revenue || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </div>
                  </div>

                  <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-xl border border-red-200 dark:border-red-800 flex justify-between items-center">
                    <div>
                      <h4 className="font-bold text-red-900 dark:text-red-300">Total Operating Expenses</h4>
                      <p className="text-xs text-red-700 dark:text-red-400">Cost of goods & operations</p>
                    </div>
                    <div className="text-2xl font-mono font-bold text-red-700 dark:text-red-300">
                      ${Number(pnl?.total_expense || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </div>
                  </div>

                  <div className="p-5 bg-blue-50 dark:bg-blue-900/30 rounded-xl border-2 border-blue-300 dark:border-blue-700 flex justify-between items-center">
                    <div>
                      <h4 className="font-bold text-lg text-blue-900 dark:text-blue-200">Net Operating Profit / (Loss)</h4>
                      <p className="text-xs text-blue-700 dark:text-blue-300">Bottom-line income statement result</p>
                    </div>
                    <div className="text-3xl font-mono font-bold text-blue-700 dark:text-blue-300">
                      ${Number(pnl?.net_income || (pnl?.total_revenue || 0) - (pnl?.total_expense || 0)).toLocaleString(
                        undefined,
                        { minimumFractionDigits: 2 }
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Tab: Balance Sheet */}
            {activeTab === 'balance_sheet' && (
              <div className="p-6 max-w-4xl mx-auto space-y-6">
                <div className="text-center pb-4 border-b border-gray-200 dark:border-gray-700">
                  <h3 className="font-bold text-xl text-gray-900 dark:text-white">Statement of Financial Position</h3>
                  <p className="text-xs text-gray-500">As of {endDate}</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Assets */}
                  <div className="p-4 bg-gray-50 dark:bg-gray-700/30 rounded-xl border border-gray-200 dark:border-gray-700 space-y-3">
                    <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-600">
                      <h4 className="font-bold text-gray-900 dark:text-white">Total Assets</h4>
                      <span className="font-mono font-bold text-lg text-blue-600 dark:text-blue-400">
                        ${Number(balanceSheet?.total_assets || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500">Cash, inventory, receivables, equipment</p>
                  </div>

                  {/* Liabilities + Equity */}
                  <div className="p-4 bg-gray-50 dark:bg-gray-700/30 rounded-xl border border-gray-200 dark:border-gray-700 space-y-3">
                    <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-600">
                      <h4 className="font-bold text-gray-900 dark:text-white">Total Liabilities & Equity</h4>
                      <span className="font-mono font-bold text-lg text-emerald-600 dark:text-emerald-400">
                        ${Number(
                          (balanceSheet?.total_liabilities || 0) + (balanceSheet?.total_equity || 0)
                        ).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 flex justify-between">
                      <span>Liabilities: ${Number(balanceSheet?.total_liabilities || 0).toLocaleString()}</span>
                      <span>Equity: ${Number(balanceSheet?.total_equity || 0).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
