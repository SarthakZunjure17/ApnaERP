import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  Plus,
  Search,
  Filter,
  DollarSign,
  TrendingUp,
  Truck,
  CheckCircle2,
  Clock,
  AlertCircle,
  Building2,
  Globe,
  MapPin,
  ChevronRight,
  Download,
} from 'lucide-react';
import { salesService } from '../../services/salesService';
import { SalesOrderListItem, SalesMetrics } from '../../types/sales';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Pagination } from '../../components/common/Pagination';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { EmptyState } from '../../components/common/EmptyState';
import { useToast } from '../../context/ToastContext';

export const SalesOrdersPage: React.FC = () => {
  const [orders, setOrders] = useState<SalesOrderListItem[]>([]);
  const [metrics, setMetrics] = useState<SalesMetrics | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCustomer, setSelectedCustomer] = useState('All Customers');
  const [selectedRegion, setSelectedRegion] = useState('All Regions');
  const [selectedFulfillment, setSelectedFulfillment] = useState('All Fulfillment');
  const [selectedPaymentStatus, setSelectedPaymentStatus] = useState('All Payment');
  const [selectedRows, setSelectedRows] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const pageSize = 6;

  // New Sales Order Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newOrderForm, setNewOrderForm] = useState({
    customer_name: 'Starlight Retail Inc.',
    region: 'North America',
    amount: 18500,
    expected_delivery: 'Nov 20, 2024',
    sales_rep_name: 'Sarah Jenkins',
  });

  const navigate = useNavigate();
  const { success, info } = useToast();

  useEffect(() => {
    setCurrentPage(1);
    loadSalesOrders();
  }, [searchQuery, selectedCustomer, selectedRegion, selectedFulfillment, selectedPaymentStatus]);

  const loadSalesOrders = async () => {
    setIsLoading(true);
    try {
      const data = await salesService.getSalesOrders({
        search: searchQuery,
        customer: selectedCustomer,
        region: selectedRegion,
        fulfillment: selectedFulfillment,
        paymentStatus: selectedPaymentStatus,
      });
      setOrders(data.items || []);
      setMetrics(data.metrics || null);
    } catch (err) {
      console.error('Failed to load sales orders', err);
      setOrders([]);
      setMetrics(null);
    } finally {
      setIsLoading(false);
    }
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
    setSearchQuery('');
    setSelectedCustomer('All Customers');
    setSelectedRegion('All Regions');
    setSelectedFulfillment('All Fulfillment');
    setSelectedPaymentStatus('All Payment');
  };

  const handleCreateOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newOrderForm.customer_name || !newOrderForm.amount) return;

    const created = await salesService.createSalesOrder(newOrderForm);
    setOrders((prev) => [created, ...prev]);
    setIsCreateModalOpen(false);
    success('Sales Order Created', `${created.order_number} created for ${created.customer_name}.`);
    navigate(`/sales/orders/${created.id}`);
  };

  const handleExport = () => {
    if (orders.length === 0) {
      info('No Orders', 'There are no sales orders to export.');
      return;
    }
    const headers = ['Order Number', 'Date', 'Customer', 'Region', 'Amount', 'Payment Status', 'Fulfillment Status', 'Sales Rep'];
    const rows = orders.map((o) => [
      `"${o.order_number}"`,
      `"${o.date}"`,
      `"${o.customer_name}"`,
      `"${o.region}"`,
      o.amount,
      `"${o.payment_status}"`,
      `"${o.fulfillment_status}"`,
      `"${o.sales_rep_name}"`,
    ]);
    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `sales_orders_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    success('Export Completed', `Exported ${orders.length} sales orders.`);
  };

  const totalPages = Math.max(1, Math.ceil(orders.length / pageSize));
  const paginatedOrders = orders.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const renderPaymentBadge = (status: string) => {
    switch (status) {
      case 'Paid':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300">
            <CheckCircle2 className="w-3 h-3" />
            Paid
          </span>
        );
      case 'Pending':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300">
            <Clock className="w-3 h-3" />
            Pending
          </span>
        );
      case 'Partially Paid':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300">
            <Clock className="w-3 h-3" />
            Partial
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {status}
          </span>
        );
    }
  };

  const renderFulfillmentBadge = (status: string) => {
    switch (status) {
      case 'Delivered':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100/70 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
            Delivered
          </span>
        );
      case 'Shipped':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100/70 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300">
            <Truck className="w-3 h-3" />
            Shipped
          </span>
        );
      case 'Processing':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100/70 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300">
            Processing
          </span>
        );
      case 'Unfulfilled':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100/70 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
            Unfulfilled
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-4 sm:space-y-5 animate-fade-in pb-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Sales Orders
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Manage customer quotations, confirmations, fulfillment pipelines, and billing.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <button
            onClick={handleExport}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            Export CSV
          </button>

          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            New Order
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      {metrics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 sm:gap-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                Total Orders
              </span>
              <div className="w-7 h-7 rounded-lg bg-blue-50 dark:bg-blue-950 text-brand-600 flex items-center justify-center">
                <FileText className="w-3.5 h-3.5" />
              </div>
            </div>
            <h3 className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
              {metrics.total_orders_count}
            </h3>
            <span className="text-[11px] text-emerald-600 font-medium mt-1 inline-block">
              +14% vs last month
            </span>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                Pipeline Value
              </span>
              <div className="w-7 h-7 rounded-lg bg-emerald-50 dark:bg-emerald-950 text-emerald-600 flex items-center justify-center">
                <DollarSign className="w-3.5 h-3.5" />
              </div>
            </div>
            <h3 className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
              {metrics.total_revenue_formatted}
            </h3>
            <span className="text-[11px] text-emerald-600 font-medium mt-1 inline-block">
              Confirmed & Invoiced
            </span>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                Pending Dispatch
              </span>
              <div className="w-7 h-7 rounded-lg bg-amber-50 dark:bg-amber-950 text-amber-600 flex items-center justify-center">
                <Truck className="w-3.5 h-3.5" />
              </div>
            </div>
            <h3 className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
              {metrics.pending_fulfillment_count}
            </h3>
            <span className="text-[11px] text-amber-600 font-medium mt-1 inline-block">
              Requires warehouse pick
            </span>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                Avg Order Value
              </span>
              <div className="w-7 h-7 rounded-lg bg-purple-50 dark:bg-purple-950 text-purple-600 flex items-center justify-center">
                <TrendingUp className="w-3.5 h-3.5" />
              </div>
            </div>
            <h3 className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
              {metrics.average_order_value_formatted}
            </h3>
            <span className="text-[11px] text-slate-400 font-medium mt-1 inline-block">
              Across enterprise deals
            </span>
          </div>
        </div>
      )}

      {/* Filter Bar */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-3.5 shadow-xs flex flex-col md:flex-row items-stretch md:items-center gap-2.5 text-xs">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by Order #, Customer or Sales Rep..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-slate-100/70 dark:bg-slate-800/80 border border-slate-200/60 dark:border-slate-700/60 rounded-lg text-slate-800 dark:text-slate-200 placeholder:text-slate-400 focus:outline-none focus:border-brand-500"
          />
        </div>

        {/* Region Filter */}
        <div className="relative">
          <select
            value={selectedRegion}
            onChange={(e) => setSelectedRegion(e.target.value)}
            className="w-full md:w-auto pl-3 pr-8 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-200 focus:outline-none focus:border-brand-500 font-medium"
          >
            <option value="All Regions">All Regions</option>
            <option value="North America">North America</option>
            <option value="Europe">Europe</option>
            <option value="Asia Pacific">Asia Pacific</option>
            <option value="Latin America">Latin America</option>
          </select>
        </div>

        {/* Fulfillment Filter */}
        <div className="relative">
          <select
            value={selectedFulfillment}
            onChange={(e) => setSelectedFulfillment(e.target.value)}
            className="w-full md:w-auto pl-3 pr-8 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-200 focus:outline-none focus:border-brand-500 font-medium"
          >
            <option value="All Fulfillment">All Fulfillment</option>
            <option value="Unfulfilled">Unfulfilled</option>
            <option value="Processing">Processing</option>
            <option value="Shipped">Shipped</option>
            <option value="Delivered">Delivered</option>
          </select>
        </div>

        {/* Payment Filter */}
        <div className="relative">
          <select
            value={selectedPaymentStatus}
            onChange={(e) => setSelectedPaymentStatus(e.target.value)}
            className="w-full md:w-auto pl-3 pr-8 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-200 focus:outline-none focus:border-brand-500 font-medium"
          >
            <option value="All Payment">All Payment</option>
            <option value="Paid">Paid</option>
            <option value="Pending">Pending</option>
            <option value="Partially Paid">Partially Paid</option>
          </select>
        </div>

        {/* Clear filter button */}
        <button
          onClick={handleClearFilters}
          className="p-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 text-slate-500 rounded-lg transition-colors flex items-center justify-center cursor-pointer"
          title="Reset Filters"
        >
          <Filter className="w-4 h-4" />
        </button>
      </div>

      {/* Orders Table */}
      {isLoading ? (
        <LoadingState message="Fetching sales orders..." />
      ) : orders.length === 0 ? (
        <EmptyState
          title="No Sales Orders Found"
          description={`No orders match your filter criteria.`}
          actionLabel="Clear Filters"
          onAction={handleClearFilters}
        />
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
                  <th className="py-2 px-3">Order Number</th>
                  <th className="py-2 px-3">Date</th>
                  <th className="py-2 px-3">Customer</th>
                  <th className="py-2 px-3">Region</th>
                  <th className="py-2 px-3">Amount</th>
                  <th className="py-2 px-3">Payment</th>
                  <th className="py-2 px-3">Fulfillment</th>
                  <th className="py-2 px-3">Sales Rep</th>
                  <th className="py-2 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100/80 dark:divide-slate-800/60 text-xs">
                {paginatedOrders.map((so) => {
                  const isChecked = selectedRows.includes(so.id);

                  return (
                    <tr
                      key={so.id}
                      onClick={() => navigate(`/sales/orders/${so.id}`)}
                      className={`hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors group cursor-pointer ${
                        isChecked ? 'bg-blue-50/40 dark:bg-blue-950/20' : ''
                      }`}
                    >
                      {/* Checkbox */}
                      <td className="py-3.5 px-3" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onClick={(e) => handleSelectRow(so.id, e)}
                          onChange={() => {}}
                          className="rounded border-slate-300 dark:border-slate-700 text-brand-600 focus:ring-brand-500"
                        />
                      </td>

                      {/* Order Number */}
                      <td className="py-3.5 px-3 font-semibold text-brand-600 hover:text-brand-700 group-hover:underline whitespace-nowrap">
                        {so.order_number}
                      </td>

                      {/* Date */}
                      <td className="py-3.5 px-3 text-slate-500 whitespace-nowrap">
                        {so.date}
                      </td>

                      {/* Customer */}
                      <td className="py-3.5 px-3">
                        <div className="flex items-center gap-2">
                          <div className="w-6.5 h-6.5 rounded bg-purple-50 dark:bg-purple-950 text-purple-700 dark:text-purple-300 flex items-center justify-center font-bold text-[10px] shrink-0">
                            {so.customer_initials}
                          </div>
                          <span className="font-semibold text-slate-900 dark:text-white">
                            {so.customer_name}
                          </span>
                        </div>
                      </td>

                      {/* Region */}
                      <td className="py-3.5 px-3 text-slate-600 dark:text-slate-400 whitespace-nowrap">
                        {so.region}
                      </td>

                      {/* Amount */}
                      <td className="py-3.5 px-3 font-bold text-slate-900 dark:text-white whitespace-nowrap">
                        {so.formatted_amount}
                      </td>

                      {/* Payment Status */}
                      <td className="py-3.5 px-3 whitespace-nowrap">
                        {renderPaymentBadge(so.payment_status)}
                      </td>

                      {/* Fulfillment Status */}
                      <td className="py-3.5 px-3 whitespace-nowrap">
                        {renderFulfillmentBadge(so.fulfillment_status)}
                      </td>

                      {/* Sales Rep */}
                      <td className="py-3.5 px-3 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          {so.sales_rep_avatar ? (
                            <img
                              src={so.sales_rep_avatar}
                              alt={so.sales_rep_name}
                              className="w-5 h-5 rounded-full object-cover shrink-0"
                            />
                          ) : (
                            <div className="w-5 h-5 rounded-full bg-slate-200 dark:bg-slate-700" />
                          )}
                          <span className="text-slate-700 dark:text-slate-300 font-medium">
                            {so.sales_rep_name}
                          </span>
                        </div>
                      </td>

                      {/* Action */}
                      <td className="py-3.5 px-3 text-right whitespace-nowrap">
                        <span className="inline-flex items-center gap-0.5 text-[11px] font-semibold text-brand-600 group-hover:text-brand-700">
                          View Order
                          <ChevronRight className="w-3.5 h-3.5" />
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            totalEntries={orders.length}
            pageSize={pageSize}
            onPageChange={(p) => setCurrentPage(p)}
          />
        </div>
      )}

      {/* Create Order Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create New Sales Order"
      >
        <form onSubmit={handleCreateOrder} className="space-y-3.5 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
              Customer / Organization Name
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Acme Worldwide"
              value={newOrderForm.customer_name}
              onChange={(e) => setNewOrderForm({ ...newOrderForm, customer_name: e.target.value })}
              className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-100"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                Sales Region
              </label>
              <select
                value={newOrderForm.region}
                onChange={(e) => setNewOrderForm({ ...newOrderForm, region: e.target.value })}
                className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-100"
              >
                <option value="North America">North America</option>
                <option value="Europe">Europe</option>
                <option value="Asia Pacific">Asia Pacific</option>
                <option value="Latin America">Latin America</option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                Estimated Amount ($)
              </label>
              <input
                type="number"
                min="100"
                required
                value={newOrderForm.amount}
                onChange={(e) => setNewOrderForm({ ...newOrderForm, amount: Number(e.target.value) })}
                className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-100"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                Expected Delivery Date
              </label>
              <input
                type="text"
                value={newOrderForm.expected_delivery}
                onChange={(e) => setNewOrderForm({ ...newOrderForm, expected_delivery: e.target.value })}
                className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-100"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                Assigned Sales Rep
              </label>
              <select
                value={newOrderForm.sales_rep_name}
                onChange={(e) => setNewOrderForm({ ...newOrderForm, sales_rep_name: e.target.value })}
                className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-100"
              >
                <option value="Sarah Jenkins">Sarah Jenkins</option>
                <option value="Amit Patel">Amit Patel</option>
                <option value="Rahul Verma">Rahul Verma</option>
                <option value="Neha Gupta">Neha Gupta</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <Button variant="outline" size="sm" type="button" onClick={() => setIsCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit">
              Submit Sales Order
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
