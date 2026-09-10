import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  Plus,
  RefreshCw,
  Search,
  Building2,
  Calendar,
  DollarSign,
  CheckCircle2,
  XCircle,
  ArrowRightCircle,
  Eye,
  Send,
  Trash2,
} from 'lucide-react';
import { salesService } from '../../services/salesService';
import { inventoryService } from '../../services/inventoryService';
import { SalesQuotationItem, CustomerItem } from '../../types/sales';
import { ProductItem } from '../../types/inventory';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { EmptyState } from '../../components/common/EmptyState';
import { ErrorState } from '../../components/common/ErrorState';
import { KpiCard } from '../../components/common/KpiCard';
import { useToast } from '../../context/ToastContext';

export const QuotationsPage: React.FC = () => {
  const [quotations, setQuotations] = useState<SalesQuotationItem[]>([]);
  const [customers, setCustomers] = useState<CustomerItem[]>([]);
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form State
  const [formData, setFormData] = useState({
    customer_id: '',
    quotation_date: new Date().toISOString().split('T')[0],
    expiry_date: new Date(Date.now() + 14 * 86400000).toISOString().split('T')[0],
    notes: '',
    items: [
      {
        product_id: '',
        quantity: 5,
        unit_price: 150,
      },
    ],
  });

  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  useEffect(() => {
    loadMetadata();
    loadQuotations();
  }, []);

  const loadMetadata = async () => {
    try {
      const [custList, prodList] = await Promise.all([
        salesService.getCustomers(),
        inventoryService.getProducts({ limit: 100 }),
      ]);
      setCustomers(custList);
      setProducts(prodList.items);
      if (custList.length > 0 && !formData.customer_id) {
        setFormData((prev) => ({ ...prev, customer_id: custList[0].id }));
      }
      if (prodList.items.length > 0 && !formData.items[0]?.product_id) {
        setFormData((prev) => ({
          ...prev,
          items: [{ product_id: prodList.items[0].id, quantity: 5, unit_price: prodList.items[0].selling_price || 150 }],
        }));
      }
    } catch (err: any) {
      console.error('Failed to load metadata', err);
    }
  };

  const loadQuotations = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const list = await salesService.getQuotations();
      setQuotations(list);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load sales quotations');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateQuotation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.customer_id || formData.items.length === 0) {
      toastError('Customer and items are required');
      return;
    }
    setIsSubmitting(true);
    try {
      await salesService.createQuotation(formData);
      success('Quotation Created', 'Proposal successfully generated.');
      setIsCreateModalOpen(false);
      loadQuotations();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to create quotation');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmitQuotation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await salesService.submitQuotation(id);
      success('Quotation Sent', 'Quotation marked as sent to customer.');
      loadQuotations();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to submit quotation');
    }
  };

  const handleApproveQuotation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await salesService.approveQuotation(id);
      success('Quotation Approved', 'Client approval recorded.');
      loadQuotations();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to approve quotation');
    }
  };

  const handleConvertToOrder = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const so = await salesService.convertQuotationToOrder(id);
      success('Converted to Sales Order', `Order ${so.order_number} generated.`);
      navigate(`/sales/orders/${so.id}`);
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to convert quotation');
    }
  };

  const filtered = quotations.filter(
    (q) =>
      q.quotation_number?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      q.customer_name?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const totalValue = quotations.reduce((acc, q) => acc + (q.total_amount || 0), 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Sales Quotations & Proposals</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Price estimates, formal client tenders, validity periods, and conversion to active orders
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" icon={<RefreshCw className="w-4 h-4" />} onClick={loadQuotations}>
            Refresh
          </Button>
          <Button
            variant="primary"
            icon={<Plus className="w-4 h-4" />}
            onClick={() => setIsCreateModalOpen(true)}
          >
            Create Quotation
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KpiCard
          title="Total Quotations"
          value={quotations.length}
          icon={<FileText className="w-5 h-5 text-blue-600 dark:text-blue-400" />}
          description="Issued proposals"
        />
        <KpiCard
          title="Proposal Pipeline Value"
          value={`$${totalValue.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          icon={<DollarSign className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />}
          description="Total estimated value"
        />
        <KpiCard
          title="Converted to Orders"
          value={quotations.filter((q) => q.status === 'Converted').length}
          icon={<ArrowRightCircle className="w-5 h-5 text-purple-600 dark:text-purple-400" />}
          description="Closed-won quotations"
        />
      </div>

      {/* Search */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700 shadow-sm flex items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search quotation # or customer..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8">
            <LoadingState message="Loading quotations..." />
          </div>
        ) : error ? (
          <div className="p-8">
            <ErrorState title="Failed to load quotations" message={error} onRetry={loadQuotations} />
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No quotations found"
              description="Create a new quote to send pricing and proposals to clients."
              action={
                <Button
                  variant="primary"
                  icon={<Plus className="w-4 h-4" />}
                  onClick={() => setIsCreateModalOpen(true)}
                >
                  Create Quotation
                </Button>
              }
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
              <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <th className="px-6 py-4">Quote #</th>
                  <th className="px-6 py-4">Customer</th>
                  <th className="px-6 py-4">Quote Date</th>
                  <th className="px-6 py-4">Valid Until</th>
                  <th className="px-6 py-4 text-right">Total Amount</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {filtered.map((q) => (
                  <tr key={q.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                    <td className="px-6 py-4 font-mono font-bold text-gray-900 dark:text-white">
                      {q.quotation_number}
                    </td>
                    <td className="px-6 py-4 font-semibold text-gray-900 dark:text-white">{q.customer_name}</td>
                    <td className="px-6 py-4 text-xs text-gray-500">{q.quotation_date}</td>
                    <td className="px-6 py-4 text-xs text-gray-500">{q.expiry_date || '-'}</td>
                    <td className="px-6 py-4 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                      ${Number(q.total_amount || 0).toFixed(2)}
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge
                        status={q.status}
                        variant={
                          q.status === 'Converted' || q.status === 'Approved'
                            ? 'success'
                            : q.status === 'Sent'
                            ? 'info'
                            : 'default'
                        }
                      />
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {q.status === 'Draft' && (
                          <Button
                            size="sm"
                            variant="secondary"
                            icon={<Send className="w-3.5 h-3.5" />}
                            onClick={(e) => handleSubmitQuotation(q.id, e)}
                          >
                            Send
                          </Button>
                        )}
                        {q.status === 'Sent' && (
                          <Button
                            size="sm"
                            variant="secondary"
                            icon={<CheckCircle2 className="w-3.5 h-3.5" />}
                            onClick={(e) => handleApproveQuotation(q.id, e)}
                          >
                            Approve
                          </Button>
                        )}
                        {q.status === 'Approved' && (
                          <Button
                            size="sm"
                            variant="primary"
                            icon={<ArrowRightCircle className="w-3.5 h-3.5" />}
                            onClick={(e) => handleConvertToOrder(q.id, e)}
                          >
                            Convert to Order
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

      {/* Modal: Create Quotation */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create Sales Quotation"
        size="lg"
      >
        <form onSubmit={handleCreateQuotation} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Customer Account *
              </label>
              <select
                required
                value={formData.customer_id}
                onChange={(e) => setFormData({ ...formData, customer_id: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Quotation Date *
              </label>
              <input
                type="date"
                required
                value={formData.quotation_date}
                onChange={(e) => setFormData({ ...formData, quotation_date: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Expiry / Validity Date
              </label>
              <input
                type="date"
                value={formData.expiry_date}
                onChange={(e) => setFormData({ ...formData, expiry_date: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="pt-2">
            <h4 className="text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-2">
              Quotation Line Items
            </h4>
            <div className="space-y-3">
              {formData.items.map((item, index) => (
                <div
                  key={index}
                  className="grid grid-cols-12 gap-2 items-center bg-gray-50 dark:bg-gray-700/40 p-3 rounded-lg border border-gray-200 dark:border-gray-700"
                >
                  <div className="col-span-6">
                    <label className="block text-[10px] uppercase text-gray-500 mb-0.5">Product</label>
                    <select
                      value={item.product_id}
                      onChange={(e) => {
                        const updated = [...formData.items];
                        const prod = products.find((p) => p.id === e.target.value);
                        updated[index] = {
                          ...updated[index],
                          product_id: e.target.value,
                          unit_price: prod?.selling_price || 0,
                        };
                        setFormData({ ...formData, items: updated });
                      }}
                      className="w-full px-2 py-1.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-xs text-gray-900 dark:text-white"
                    >
                      {products.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name} (${p.selling_price})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="col-span-3">
                    <label className="block text-[10px] uppercase text-gray-500 mb-0.5">Qty</label>
                    <input
                      type="number"
                      min="1"
                      value={item.quantity}
                      onChange={(e) => {
                        const updated = [...formData.items];
                        updated[index] = {
                          ...updated[index],
                          quantity: parseInt(e.target.value, 10) || 1,
                        };
                        setFormData({ ...formData, items: updated });
                      }}
                      className="w-full px-2 py-1.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-xs text-gray-900 dark:text-white"
                    />
                  </div>

                  <div className="col-span-3">
                    <label className="block text-[10px] uppercase text-gray-500 mb-0.5">Unit Price ($)</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={item.unit_price}
                      onChange={(e) => {
                        const updated = [...formData.items];
                        updated[index] = {
                          ...updated[index],
                          unit_price: parseFloat(e.target.value) || 0,
                        };
                        setFormData({ ...formData, items: updated });
                      }}
                      className="w-full px-2 py-1.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-xs text-gray-900 dark:text-white"
                    />
                  </div>
                </div>
              ))}
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
            <Button type="submit" variant="primary" loading={isSubmitting}>
              Generate Quotation
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
