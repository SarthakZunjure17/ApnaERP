import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus,
  Building2,
  Calendar,
  Filter,
  ChevronRight,
  RotateCcw,
  CheckCircle2,
} from 'lucide-react';
import { procurementService } from '../../services/procurementService';
import { PurchaseOrderListItem } from '../../types/procurement';
import { Pagination } from '../../components/common/Pagination';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { useToast } from '../../context/ToastContext';

export const PurchaseOrdersPage: React.FC = () => {
  const [orders, setOrders] = useState<PurchaseOrderListItem[]>([]);
  const [selectedSupplier, setSelectedSupplier] = useState('All Suppliers');
  const [dateRange, setDateRange] = useState('Jan 1, 2024 - Jan 31, 2024');
  const [selectedStatus, setSelectedStatus] = useState<string>('Pending');
  const [selectedRows, setSelectedRows] = useState<string[]>([]);
  const [totalPending, setTotalPending] = useState('$450,230.00');
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);

  // Create PO Modal
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newPoForm, setNewPoForm] = useState({
    supplier_name: 'Acme Corp',
    amount: 15000,
    expected_date: 'Nov 20, 2024',
  });

  const navigate = useNavigate();
  const { success, info } = useToast();

  useEffect(() => {
    loadOrders();
  }, [selectedSupplier, selectedStatus]);

  const loadOrders = async () => {
    setIsLoading(true);
    const data = await procurementService.getPurchaseOrders({
      supplier: selectedSupplier,
      status: selectedStatus === 'All' ? undefined : selectedStatus === 'Pending' ? 'Pending Approval' : selectedStatus,
    });
    setOrders(data.items);
    setTotalPending(data.totalPendingAmount);
    setIsLoading(false);
  };

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedRows(orders.map((o) => o.id));
    } else {
      setSelectedRows([]);
    }
  };

  const handleSelectRow = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedRows((prev) =>
      prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id]
    );
  };

  const handleClearFilters = () => {
    setSelectedSupplier('All Suppliers');
    setSelectedStatus('All');
  };

  const handleCreatePo = (e: React.FormEvent) => {
    e.preventDefault();
    const created: PurchaseOrderListItem = {
      id: `po-${Date.now()}`,
      po_number: `PO-2024-${Math.floor(1050 + Math.random() * 50)}`,
      date: 'Today',
      supplier_name: newPoForm.supplier_name,
      supplier_initials: newPoForm.supplier_name.slice(0, 2).toUpperCase(),
      amount: newPoForm.amount,
      formatted_amount: `$${newPoForm.amount.toLocaleString()}.00`,
      expected_date: newPoForm.expected_date,
      status: 'Pending Approval',
      approver_name: 'ERP Admin',
    };

    setOrders([created, ...orders]);
    setIsCreateModalOpen(false);
    success('Purchase Order Created', `${created.po_number} submitted for approval.`);
    navigate(`/procurement/orders/${created.id}`);
  };

  const renderStatusBadge = (status: PurchaseOrderListItem['status']) => {
    switch (status) {
      case 'Pending Approval':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-100/80 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200/80 dark:border-amber-900/40">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-600 shrink-0" />
            Pending Approval
          </span>
        );
      case 'Approved':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border border-blue-200/80 dark:border-blue-900/40">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-600 shrink-0" />
            Approved
          </span>
        );
      case 'Draft':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300 border border-slate-200/70 dark:border-slate-700">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400 shrink-0" />
            Draft
          </span>
        );
      case 'Rejected':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-200/80 dark:border-rose-900/40">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-600 shrink-0" />
            Rejected
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-600">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-4 sm:space-y-5 animate-fade-in pb-8">
      {/* Top Header (Matching Screenshot 5) */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Purchase Orders
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Manage and track all supplier purchase orders across the organization.
          </p>
        </div>

        {/* Right side summary pill and create button */}
        <div className="flex items-center gap-3 self-start sm:self-auto">
          <div className="px-3.5 py-1.5 rounded-xl bg-[#f0f4ff] dark:bg-slate-900 border border-blue-100 dark:border-slate-800 flex flex-col justify-center">
            <span className="text-[9px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider leading-none">
              Total Pending Approval
            </span>
            <span className="text-base sm:text-lg font-bold text-amber-700 dark:text-amber-400 mt-0.5 leading-none">
              {totalPending}
            </span>
          </div>

          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            Create PO
          </button>
        </div>
      </div>

      {/* Filter Card (Matching Screenshot 5) */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 shadow-xs">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
          <div className="flex flex-col sm:flex-row items-stretch sm:items-end gap-3 flex-1">
            {/* Supplier select */}
            <div className="flex-1">
              <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">
                Supplier
              </label>
              <div className="relative">
                <Building2 className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <select
                  value={selectedSupplier}
                  onChange={(e) => setSelectedSupplier(e.target.value)}
                  className="w-full pl-9 pr-6 py-2 bg-slate-50/80 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-brand-500 font-medium"
                >
                  <option value="All Suppliers">All Suppliers</option>
                  <option value="Acme Corp">Acme Corp</option>
                  <option value="Global Industries">Global Industries</option>
                  <option value="TechSolutions Inc">TechSolutions Inc</option>
                </select>
              </div>
            </div>

            {/* Date range */}
            <div className="flex-1">
              <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">
                Date Range
              </label>
              <div className="relative">
                <Calendar className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={dateRange}
                  onChange={(e) => setDateRange(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-slate-50/80 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-brand-500 font-medium"
                />
              </div>
            </div>

            {/* Status Pills */}
            <div>
              <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">
                Status
              </label>
              <div className="inline-flex items-center gap-1.5">
                {(['Draft', 'Pending', 'Approved'] as const).map((status) => {
                  const isSelected = selectedStatus === status;
                  return (
                    <button
                      key={status}
                      type="button"
                      onClick={() => setSelectedStatus(isSelected ? 'All' : status)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                        isSelected
                          ? status === 'Pending'
                            ? 'bg-amber-700 text-white shadow-xs'
                            : 'bg-brand-600 text-white shadow-xs'
                          : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                      }`}
                    >
                      {status}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 self-end">
            <button
              onClick={handleClearFilters}
              className="text-xs font-semibold text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 px-2 py-1.5 cursor-pointer"
            >
              Clear
            </button>

            <button
              onClick={loadOrders}
              className="inline-flex items-center gap-1.5 px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 text-slate-700 dark:text-slate-200 rounded-lg text-xs font-semibold shadow-xs transition-colors cursor-pointer"
            >
              <Filter className="w-3.5 h-3.5" />
              Apply Filters
            </button>
          </div>
        </div>
      </div>

      {/* Table (Matching Screenshot 5) */}
      {isLoading ? (
        <LoadingState message="Loading purchase orders..." />
      ) : (
        <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800 text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                  <th className="py-2 px-3 w-8">
                    <input
                      type="checkbox"
                      checked={selectedRows.length === orders.length && orders.length > 0}
                      onChange={handleSelectAll}
                      className="rounded border-slate-300 dark:border-slate-700 text-brand-600 focus:ring-brand-500"
                    />
                  </th>
                  <th className="py-2 px-3">PO Number</th>
                  <th className="py-2 px-3">Date</th>
                  <th className="py-2 px-3">Supplier</th>
                  <th className="py-2 px-3">Amount</th>
                  <th className="py-2 px-3">Expected</th>
                  <th className="py-2 px-3">Status</th>
                  <th className="py-2 px-3">Approver</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100/80 dark:divide-slate-800/60 text-xs">
                {orders.map((po) => {
                  const isChecked = selectedRows.includes(po.id);

                  return (
                    <tr
                      key={po.id}
                      onClick={() => navigate(`/procurement/orders/${po.id}`)}
                      className={`hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors group cursor-pointer ${
                        isChecked ? 'bg-blue-50/40 dark:bg-blue-950/20' : ''
                      }`}
                    >
                      {/* Checkbox */}
                      <td className="py-3.5 px-3">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onClick={(e) => handleSelectRow(po.id, e)}
                          onChange={() => {}}
                          className="rounded border-slate-300 dark:border-slate-700 text-brand-600 focus:ring-brand-500"
                        />
                      </td>

                      {/* PO Number link in blue */}
                      <td className="py-3.5 px-3 font-semibold text-brand-600 hover:text-brand-700 group-hover:underline">
                        {po.po_number}
                      </td>

                      {/* Date */}
                      <td className="py-3.5 px-3 text-slate-600 dark:text-slate-400 whitespace-nowrap">
                        {po.date}
                      </td>

                      {/* Supplier with Avatar Initials */}
                      <td className="py-3.5 px-3">
                        <div className="flex items-center gap-2">
                          <div className="w-6.5 h-6.5 rounded bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 flex items-center justify-center font-bold text-[10px] shrink-0">
                            {po.supplier_initials}
                          </div>
                          <span className="font-medium text-slate-900 dark:text-white">
                            {po.supplier_name}
                          </span>
                        </div>
                      </td>

                      {/* Amount */}
                      <td className="py-3.5 px-3 font-medium text-slate-900 dark:text-white whitespace-nowrap">
                        {po.formatted_amount}
                      </td>

                      {/* Expected */}
                      <td className="py-3.5 px-3 text-slate-500 whitespace-nowrap">
                        {po.expected_date}
                      </td>

                      {/* Status */}
                      <td className="py-3.5 px-3 whitespace-nowrap">
                        {renderStatusBadge(po.status)}
                      </td>

                      {/* Approver */}
                      <td className="py-3.5 px-3 whitespace-nowrap">
                        {po.approver_name !== 'Unassigned' ? (
                          <div className="flex items-center gap-2">
                            <img
                              src={
                                po.approver_avatar ||
                                'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=50&auto=format&fit=crop&q=80'
                              }
                              alt={po.approver_name}
                              className="w-5 h-5 rounded-full object-cover shrink-0"
                            />
                            <span className="text-slate-700 dark:text-slate-300 font-medium">
                              {po.approver_name}
                            </span>
                          </div>
                        ) : (
                          <span className="text-slate-400 italic">Unassigned</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <Pagination
            currentPage={currentPage}
            totalPages={31}
            totalEntries={124}
            pageSize={4}
            onPageChange={(p) => setCurrentPage(p)}
          />
        </div>
      )}

      {/* Create PO Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create Purchase Order"
      >
        <form onSubmit={handleCreatePo} className="space-y-3.5 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
              Select Supplier
            </label>
            <select
              value={newPoForm.supplier_name}
              onChange={(e) => setNewPoForm({ ...newPoForm, supplier_name: e.target.value })}
              className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
            >
              <option value="Acme Corp">Acme Corp</option>
              <option value="Global Industries">Global Industries</option>
              <option value="TechSolutions Inc">TechSolutions Inc</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                Estimated Amount ($)
              </label>
              <input
                type="number"
                min="100"
                value={newPoForm.amount}
                onChange={(e) => setNewPoForm({ ...newPoForm, amount: Number(e.target.value) })}
                className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                Expected Delivery Date
              </label>
              <input
                type="text"
                value={newPoForm.expected_date}
                onChange={(e) => setNewPoForm({ ...newPoForm, expected_date: e.target.value })}
                className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <Button variant="outline" size="sm" type="button" onClick={() => setIsCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit">
              Submit PO
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
