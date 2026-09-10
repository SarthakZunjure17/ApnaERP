import React, { useState, useEffect } from 'react';
import {
  FileSpreadsheet,
  Plus,
  RefreshCw,
  Search,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Eye,
  Trash2,
  AlertTriangle,
  DollarSign,
  Calendar,
  Filter,
} from 'lucide-react';
import { financeService } from '../../services/financeService';
import { JournalEntryItem, ChartOfAccountItem } from '../../types/finance';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { EmptyState } from '../../components/common/EmptyState';
import { ErrorState } from '../../components/common/ErrorState';
import { KpiCard } from '../../components/common/KpiCard';
import { useToast } from '../../context/ToastContext';

export const JournalsPage: React.FC = () => {
  const [journals, setJournals] = useState<JournalEntryItem[]>([]);
  const [accounts, setAccounts] = useState<ChartOfAccountItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedStatus, setSelectedStatus] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');

  // Modals
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedJournal, setSelectedJournal] = useState<JournalEntryItem | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form State
  const [formData, setFormData] = useState({
    journal_type: 'General',
    posting_date: new Date().toISOString().split('T')[0],
    description: '',
    reference_number: '',
    lines: [
      { account_id: '', description: '', debit_amount: 100, credit_amount: 0 },
      { account_id: '', description: '', debit_amount: 0, credit_amount: 100 },
    ],
  });

  const { success, error: toastError } = useToast();

  useEffect(() => {
    loadMetadata();
    loadJournals();
  }, [selectedStatus]);

  const loadMetadata = async () => {
    try {
      const accList = await financeService.getChartOfAccounts();
      setAccounts(accList);
      if (accList.length >= 2) {
        setFormData((prev) => ({
          ...prev,
          lines: [
            { account_id: accList[0].id, description: '', debit_amount: 100, credit_amount: 0 },
            { account_id: accList[1].id, description: '', debit_amount: 0, credit_amount: 100 },
          ],
        }));
      }
    } catch (err: any) {
      console.error('Failed to load accounts for journals', err);
    }
  };

  const loadJournals = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await financeService.getJournals({
        status: selectedStatus !== 'All' ? selectedStatus : undefined,
      });
      setJournals(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load journal entries');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddLine = () => {
    if (accounts.length === 0) return;
    setFormData({
      ...formData,
      lines: [
        ...formData.lines,
        { account_id: accounts[0].id, description: '', debit_amount: 0, credit_amount: 0 },
      ],
    });
  };

  const handleRemoveLine = (index: number) => {
    if (formData.lines.length <= 2) return;
    setFormData({
      ...formData,
      lines: formData.lines.filter((_, i) => i !== index),
    });
  };

  const handleLineChange = (index: number, field: string, value: any) => {
    const updated = [...formData.lines];
    updated[index] = { ...updated[index], [field]: value };
    setFormData({ ...formData, lines: updated });
  };

  const totalDebit = formData.lines.reduce((acc, l) => acc + (parseFloat(String(l.debit_amount)) || 0), 0);
  const totalCredit = formData.lines.reduce((acc, l) => acc + (parseFloat(String(l.credit_amount)) || 0), 0);
  const isBalanced = Math.abs(totalDebit - totalCredit) < 0.001 && totalDebit > 0;

  const handleCreateJournal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isBalanced) {
      toastError(`Journal is not balanced! Debits ($${totalDebit.toFixed(2)}) must equal Credits ($${totalCredit.toFixed(2)})`);
      return;
    }
    if (!formData.description) {
      toastError('Journal description is required');
      return;
    }

    setIsSubmitting(true);
    try {
      await financeService.createJournal({
        ...formData,
        lines: formData.lines.map((l) => ({
          account_id: l.account_id,
          description: l.description || undefined,
          debit_amount: Number(l.debit_amount),
          credit_amount: Number(l.credit_amount),
        })),
      });
      success('Journal Voucher Created', 'Draft journal entry registered.');
      setIsCreateModalOpen(false);
      loadJournals();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to create journal');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePostJournal = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await financeService.postJournal(id);
      success('Journal Posted', 'Entry successfully posted to General Ledger.');
      loadJournals();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to post journal');
    }
  };

  const handleReverseJournal = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await financeService.reverseJournal(id, 'User initiated reversal');
      success('Journal Reversed', 'Reversal entry posted to ledger.');
      loadJournals();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to reverse journal');
    }
  };

  const handleCancelJournal = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Cancel this draft journal?')) return;
    try {
      await financeService.cancelJournal(id);
      success('Journal Cancelled', 'Draft entry marked cancelled.');
      loadJournals();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to cancel journal');
    }
  };

  const filtered = journals.filter(
    (j) =>
      j.entry_number?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      j.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const totalPostedVolume = journals
    .filter((j) => j.status === 'Posted')
    .reduce((acc, j) => acc + (Number(j.total_debit) || 0), 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Journal Entries & Vouchers</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Double-entry ledger adjustments, manual vouchers, posting validation, and reversals
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" icon={<RefreshCw className="w-4 h-4" />} onClick={loadJournals}>
            Refresh
          </Button>
          <Button
            variant="primary"
            icon={<Plus className="w-4 h-4" />}
            onClick={() => setIsCreateModalOpen(true)}
          >
            New Journal Voucher
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard
          title="Total Journals"
          value={journals.length}
          icon={<FileSpreadsheet className="w-5 h-5 text-blue-600 dark:text-blue-400" />}
          description="Ledger entries created"
        />
        <KpiCard
          title="Posted Volume"
          value={`$${totalPostedVolume.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          icon={<DollarSign className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />}
          description="Debits posted to ledger"
        />
        <KpiCard
          title="Draft Entries"
          value={journals.filter((j) => j.status === 'Draft').length}
          icon={<Calendar className="w-5 h-5 text-amber-600 dark:text-amber-400" />}
          description="Awaiting posting"
        />
        <KpiCard
          title="Posted Entries"
          value={journals.filter((j) => j.status === 'Posted').length}
          icon={<CheckCircle2 className="w-5 h-5 text-purple-600 dark:text-purple-400" />}
          description="Financial records sealed"
        />
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700 shadow-sm flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search entry # or description..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="All">All Statuses</option>
            <option value="Draft">Draft</option>
            <option value="Posted">Posted</option>
            <option value="Reversed">Reversed</option>
            <option value="Cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      {/* Journals Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8">
            <LoadingState message="Loading journal vouchers..." />
          </div>
        ) : error ? (
          <div className="p-8">
            <ErrorState title="Failed to load journals" message={error} onRetry={loadJournals} />
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No journal vouchers found"
              description="Create a balanced double-entry voucher to record ledger transactions."
              action={
                <Button
                  variant="primary"
                  icon={<Plus className="w-4 h-4" />}
                  onClick={() => setIsCreateModalOpen(true)}
                >
                  New Journal Voucher
                </Button>
              }
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
              <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <th className="px-6 py-4">Entry Number</th>
                  <th className="px-6 py-4">Posting Date</th>
                  <th className="px-6 py-4">Type</th>
                  <th className="px-6 py-4">Description</th>
                  <th className="px-6 py-4 text-right">Debit ($)</th>
                  <th className="px-6 py-4 text-right">Credit ($)</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {filtered.map((j) => (
                  <tr
                    key={j.id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors cursor-pointer"
                    onClick={() => setSelectedJournal(j)}
                  >
                    <td className="px-6 py-4 font-mono font-bold text-gray-900 dark:text-white">
                      {j.entry_number}
                    </td>
                    <td className="px-6 py-4 text-xs text-gray-500">{j.posting_date}</td>
                    <td className="px-6 py-4">
                      <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
                        {j.journal_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-medium text-gray-900 dark:text-white max-w-xs truncate">
                      {j.description}
                    </td>
                    <td className="px-6 py-4 text-right font-mono font-bold text-gray-900 dark:text-white">
                      ${Number(j.total_debit || 0).toFixed(2)}
                    </td>
                    <td className="px-6 py-4 text-right font-mono font-bold text-gray-900 dark:text-white">
                      ${Number(j.total_credit || 0).toFixed(2)}
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge
                        status={j.status}
                        variant={
                          j.status === 'Posted'
                            ? 'success'
                            : j.status === 'Draft'
                            ? 'warning'
                            : j.status === 'Reversed'
                            ? 'info'
                            : 'default'
                        }
                      />
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {j.status === 'Draft' && (
                          <>
                            <Button
                              size="sm"
                              variant="primary"
                              icon={<CheckCircle2 className="w-3.5 h-3.5" />}
                              onClick={(e) => handlePostJournal(j.id, e)}
                            >
                              Post
                            </Button>
                            <button
                              title="Cancel"
                              className="p-1 text-gray-400 hover:text-red-500"
                              onClick={(e) => handleCancelJournal(j.id, e)}
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </>
                        )}
                        {j.status === 'Posted' && (
                          <Button
                            size="sm"
                            variant="secondary"
                            icon={<RotateCcw className="w-3.5 h-3.5" />}
                            onClick={(e) => handleReverseJournal(j.id, e)}
                          >
                            Reverse
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal: View Journal Details */}
      {selectedJournal && (
        <Modal
          isOpen={!!selectedJournal}
          onClose={() => setSelectedJournal(null)}
          title={`Journal Voucher: ${selectedJournal.entry_number}`}
          size="lg"
        >
          <div className="space-y-6">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 bg-gray-50 dark:bg-gray-700/50 p-4 rounded-xl border border-gray-200 dark:border-gray-600">
              <div>
                <span className="text-xs text-gray-400 uppercase font-semibold">Posting Date</span>
                <p className="font-semibold text-gray-900 dark:text-white mt-0.5">{selectedJournal.posting_date}</p>
              </div>
              <div>
                <span className="text-xs text-gray-400 uppercase font-semibold">Journal Type</span>
                <p className="font-medium text-gray-900 dark:text-white mt-0.5">{selectedJournal.journal_type}</p>
              </div>
              <div>
                <span className="text-xs text-gray-400 uppercase font-semibold">Status</span>
                <div className="mt-0.5">
                  <StatusBadge
                    status={selectedJournal.status}
                    variant={selectedJournal.status === 'Posted' ? 'success' : 'default'}
                  />
                </div>
              </div>
              <div>
                <span className="text-xs text-gray-400 uppercase font-semibold">Total Amount</span>
                <p className="font-mono font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">
                  ${Number(selectedJournal.total_debit || 0).toFixed(2)}
                </p>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-semibold uppercase text-gray-500 mb-1">Description</h4>
              <p className="text-sm text-gray-800 dark:text-gray-200 bg-gray-50 dark:bg-gray-700/30 p-3 rounded-lg">
                {selectedJournal.description}
              </p>
            </div>

            <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50 dark:bg-gray-700 text-xs font-semibold text-gray-700 dark:text-gray-300">
                  <tr>
                    <th className="px-4 py-3">Account</th>
                    <th className="px-4 py-3">Line Description</th>
                    <th className="px-4 py-3 text-right">Debit ($)</th>
                    <th className="px-4 py-3 text-right">Credit ($)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {selectedJournal.lines?.map((line, idx) => (
                    <tr key={idx}>
                      <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">
                        {line.account_name || line.account_code || `Account (${line.account_id.substring(0, 8)})`}
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{line.description || '-'}</td>
                      <td className="px-4 py-3 text-right font-mono font-semibold text-gray-900 dark:text-white">
                        {Number(line.debit_amount || 0) > 0 ? `$${Number(line.debit_amount).toFixed(2)}` : '-'}
                      </td>
                      <td className="px-4 py-3 text-right font-mono font-semibold text-gray-900 dark:text-white">
                        {Number(line.credit_amount || 0) > 0 ? `$${Number(line.credit_amount).toFixed(2)}` : '-'}
                      </td>
                    </tr>
                  ))}
                  <tr className="bg-gray-50 dark:bg-gray-700/50 font-bold border-t-2 border-gray-300 dark:border-gray-600">
                    <td colSpan={2} className="px-4 py-3 text-gray-900 dark:text-white">
                      Balanced Totals
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-emerald-600">
                      ${Number(selectedJournal.total_debit || 0).toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-emerald-600">
                      ${Number(selectedJournal.total_credit || 0).toFixed(2)}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <Button variant="secondary" onClick={() => setSelectedJournal(null)}>
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal: Create Journal Entry */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create Double-Entry Journal Voucher"
        size="lg"
      >
        <form onSubmit={handleCreateJournal} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Journal Type *
              </label>
              <select
                value={formData.journal_type}
                onChange={(e) => setFormData({ ...formData, journal_type: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                <option value="General">General Journal</option>
                <option value="Bank">Bank / Cash</option>
                <option value="Adjustment">Adjustment</option>
                <option value="Opening">Opening Balance</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Posting Date *
              </label>
              <input
                type="date"
                required
                value={formData.posting_date}
                onChange={(e) => setFormData({ ...formData, posting_date: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Reference #
              </label>
              <input
                type="text"
                placeholder="INV-99001 / Bank Ref"
                value={formData.reference_number}
                onChange={(e) => setFormData({ ...formData, reference_number: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
              Description / Memo *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Monthly rent accrual / Operating expense"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Lines */}
          <div className="pt-2">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-semibold uppercase text-gray-700 dark:text-gray-300">
                Ledger Debit & Credit Lines
              </h4>
              <Button type="button" size="sm" variant="secondary" onClick={handleAddLine}>
                + Add Line
              </Button>
            </div>

            <div className="space-y-3">
              {formData.lines.map((line, idx) => (
                <div
                  key={idx}
                  className="grid grid-cols-12 gap-2 items-center bg-gray-50 dark:bg-gray-700/40 p-3 rounded-lg border border-gray-200 dark:border-gray-700"
                >
                  <div className="col-span-5">
                    <label className="block text-[10px] uppercase text-gray-500 mb-0.5">Account</label>
                    <select
                      value={line.account_id}
                      onChange={(e) => handleLineChange(idx, 'account_id', e.target.value)}
                      className="w-full px-2 py-1.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-xs text-gray-900 dark:text-white"
                    >
                      {accounts.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.code} - {a.name} ({a.account_type})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="col-span-3">
                    <label className="block text-[10px] uppercase text-gray-500 mb-0.5">Debit ($)</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={line.debit_amount}
                      onChange={(e) =>
                        handleLineChange(idx, 'debit_amount', parseFloat(e.target.value) || 0)
                      }
                      className="w-full px-2 py-1.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-xs text-gray-900 dark:text-white"
                    />
                  </div>

                  <div className="col-span-3">
                    <label className="block text-[10px] uppercase text-gray-500 mb-0.5">Credit ($)</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={line.credit_amount}
                      onChange={(e) =>
                        handleLineChange(idx, 'credit_amount', parseFloat(e.target.value) || 0)
                      }
                      className="w-full px-2 py-1.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-xs text-gray-900 dark:text-white"
                    />
                  </div>

                  <div className="col-span-1 text-right pt-4">
                    <button
                      type="button"
                      disabled={formData.lines.length <= 2}
                      onClick={() => handleRemoveLine(idx)}
                      className="text-gray-400 hover:text-red-500 disabled:opacity-30"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Validation Balance Bar */}
          <div
            className={`p-3 rounded-xl flex items-center justify-between border ${
              isBalanced
                ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300'
                : 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300'
            }`}
          >
            <div className="flex items-center gap-2">
              {isBalanced ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-amber-600" />
              )}
              <span className="text-xs font-semibold">
                {isBalanced ? 'Journal is Balanced' : `Imbalance: $${Math.abs(totalDebit - totalCredit).toFixed(2)}`}
              </span>
            </div>

            <div className="text-xs font-mono font-bold flex gap-4">
              <span>Total Debits: ${totalDebit.toFixed(2)}</span>
              <span>Total Credits: ${totalCredit.toFixed(2)}</span>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsCreateModalOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={!isBalanced} loading={isSubmitting}>
              Save Journal Entry
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
