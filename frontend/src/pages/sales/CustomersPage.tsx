import React, { useState, useEffect } from 'react';
import {
  Users,
  Plus,
  RefreshCw,
  Search,
  Building2,
  Mail,
  Phone,
  DollarSign,
  ShieldCheck,
  Tag,
  CheckCircle2,
  XCircle,
  Eye,
} from 'lucide-react';
import { salesService } from '../../services/salesService';
import { CustomerItem } from '../../types/sales';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { EmptyState } from '../../components/common/EmptyState';
import { ErrorState } from '../../components/common/ErrorState';
import { KpiCard } from '../../components/common/KpiCard';
import { useToast } from '../../context/ToastContext';

export const CustomersPage: React.FC = () => {
  const [customers, setCustomers] = useState<CustomerItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals & Details
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerItem | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form State
  const [formData, setFormData] = useState<Partial<CustomerItem>>({
    name: '',
    code: '',
    customer_type: 'Corporate',
    email: '',
    phone: '',
    tax_identifier: '',
    credit_limit: 50000,
    credit_days: 30,
    city: '',
    country: 'USA',
  });

  const [searchQuery, setSearchQuery] = useState('');
  const { success, error: toastError } = useToast();

  useEffect(() => {
    loadCustomers();
  }, []);

  const loadCustomers = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const list = await salesService.getCustomers();
      setCustomers(list);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load customer directory');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateCustomer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name || !formData.code) {
      toastError('Customer name and code are required');
      return;
    }
    setIsSubmitting(true);
    try {
      await salesService.createCustomer({
        ...formData,
        is_active: true,
      });
      success('Customer Registered', `${formData.name} successfully created.`);
      setIsAddModalOpen(false);
      setFormData({
        name: '',
        code: '',
        customer_type: 'Corporate',
        email: '',
        phone: '',
        tax_identifier: '',
        credit_limit: 50000,
        credit_days: 30,
        city: '',
        country: 'USA',
      });
      loadCustomers();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to register customer');
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredCustomers = customers.filter(
    (c) =>
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.city?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const totalCreditLimit = customers.reduce((acc, c) => acc + (Number(c.credit_limit) || 0), 0);
  const enterpriseCount = customers.filter((c) => c.customer_type === 'Enterprise').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Customer Accounts</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Client directory, billing profiles, risk terms, and credit facilities
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" icon={<RefreshCw className="w-4 h-4" />} onClick={loadCustomers}>
            Refresh
          </Button>
          <Button
            variant="primary"
            icon={<Plus className="w-4 h-4" />}
            onClick={() => setIsAddModalOpen(true)}
          >
            Add Customer
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard
          title="Total Customers"
          value={customers.length}
          icon={<Users className="w-5 h-5 text-blue-600 dark:text-blue-400" />}
          description="Active client accounts"
        />
        <KpiCard
          title="Enterprise Tier"
          value={enterpriseCount}
          icon={<Building2 className="w-5 h-5 text-purple-600 dark:text-purple-400" />}
          description="Key strategic accounts"
        />
        <KpiCard
          title="Total Credit Extended"
          value={`$${totalCreditLimit.toLocaleString()}`}
          icon={<DollarSign className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />}
          description="Authorized credit pool"
        />
        <KpiCard
          title="Active Standing"
          value={customers.filter((c) => c.is_active).length}
          icon={<ShieldCheck className="w-5 h-5 text-amber-600 dark:text-amber-400" />}
          description="Approved for order creation"
        />
      </div>

      {/* Search & Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700 shadow-sm flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search customer by name, code, email..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Customers Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8">
            <LoadingState message="Loading customers..." />
          </div>
        ) : error ? (
          <div className="p-8">
            <ErrorState title="Failed to load customers" message={error} onRetry={loadCustomers} />
          </div>
        ) : filteredCustomers.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No customers found"
              description="Register customer accounts to generate sales quotations and orders."
              action={
                <Button
                  variant="primary"
                  icon={<Plus className="w-4 h-4" />}
                  onClick={() => setIsAddModalOpen(true)}
                >
                  Create Customer
                </Button>
              }
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
              <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <th className="px-6 py-4">Account Code</th>
                  <th className="px-6 py-4">Customer Name</th>
                  <th className="px-6 py-4">Tier</th>
                  <th className="px-6 py-4">Contact</th>
                  <th className="px-6 py-4 text-right">Credit Limit</th>
                  <th className="px-6 py-4">Credit Terms</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4 text-right">Profile</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {filteredCustomers.map((c) => (
                  <tr
                    key={c.id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors cursor-pointer"
                    onClick={() => setSelectedCustomer(c)}
                  >
                    <td className="px-6 py-4 font-mono font-bold text-gray-900 dark:text-white">{c.code}</td>
                    <td className="px-6 py-4 font-semibold text-gray-900 dark:text-white">
                      <div>{c.name}</div>
                      {c.city && (
                        <div className="text-xs text-gray-400">
                          {c.city}, {c.country}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
                        {c.customer_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 space-y-0.5">
                      {c.email && (
                        <div className="flex items-center gap-1.5 text-xs text-gray-500">
                          <Mail className="w-3.5 h-3.5 text-gray-400" /> {c.email}
                        </div>
                      )}
                      {c.phone && (
                        <div className="flex items-center gap-1.5 text-xs text-gray-500">
                          <Phone className="w-3.5 h-3.5 text-gray-400" /> {c.phone}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                      ${Number(c.credit_limit || 0).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-xs font-medium text-gray-700 dark:text-gray-300">
                      Net {c.credit_days || 30} Days
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge
                        status={c.is_active ? 'Active' : 'Inactive'}
                        variant={c.is_active ? 'success' : 'default'}
                      />
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedCustomer(c);
                        }}
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal: Customer Details */}
      {selectedCustomer && (
        <Modal
          isOpen={!!selectedCustomer}
          onClose={() => setSelectedCustomer(null)}
          title={`Customer: ${selectedCustomer.name}`}
          size="lg"
        >
          <div className="space-y-6">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 bg-gray-50 dark:bg-gray-700/50 p-4 rounded-xl border border-gray-200 dark:border-gray-600">
              <div>
                <span className="text-xs text-gray-400 uppercase font-semibold">Account Code</span>
                <p className="font-mono font-bold text-gray-900 dark:text-white mt-0.5">{selectedCustomer.code}</p>
              </div>
              <div>
                <span className="text-xs text-gray-400 uppercase font-semibold">Tier</span>
                <p className="font-medium text-gray-900 dark:text-white mt-0.5">{selectedCustomer.customer_type}</p>
              </div>
              <div>
                <span className="text-xs text-gray-400 uppercase font-semibold">Status</span>
                <div className="mt-0.5">
                  <StatusBadge
                    status={selectedCustomer.is_active ? 'Active' : 'Inactive'}
                    variant={selectedCustomer.is_active ? 'success' : 'default'}
                  />
                </div>
              </div>
              <div>
                <span className="text-xs text-gray-400 uppercase font-semibold">Credit Limit</span>
                <p className="font-mono font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">
                  ${Number(selectedCustomer.credit_limit || 0).toLocaleString()}
                </p>
              </div>
              <div>
                <span className="text-xs text-gray-400 uppercase font-semibold">Payment Terms</span>
                <p className="font-medium text-gray-900 dark:text-white mt-0.5">
                  Net {selectedCustomer.credit_days || 30} Days
                </p>
              </div>
              <div>
                <span className="text-xs text-gray-400 uppercase font-semibold">Tax Identifier</span>
                <p className="font-mono text-gray-900 dark:text-white mt-0.5">
                  {selectedCustomer.tax_identifier || 'N/A'}
                </p>
              </div>
            </div>

            <div className="p-4 bg-gray-50 dark:bg-gray-700/30 rounded-xl space-y-2">
              <h4 className="text-xs font-semibold uppercase text-gray-500">Contact & Address</h4>
              <p className="text-sm text-gray-900 dark:text-white">Email: {selectedCustomer.email || 'None'}</p>
              <p className="text-sm text-gray-900 dark:text-white">Phone: {selectedCustomer.phone || 'None'}</p>
              <p className="text-sm text-gray-900 dark:text-white">
                Location: {selectedCustomer.city || 'City'}, {selectedCustomer.country || 'Country'}
              </p>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <Button variant="secondary" onClick={() => setSelectedCustomer(null)}>
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal: Add Customer */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Register New Customer"
        size="lg"
      >
        <form onSubmit={handleCreateCustomer} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Customer Code *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. CUST-001"
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Company / Name *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Apex Global Logistics"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Account Tier *
              </label>
              <select
                value={formData.customer_type}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    customer_type: e.target.value as 'Individual' | 'Corporate' | 'Enterprise',
                  })
                }
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                <option value="Corporate">Corporate</option>
                <option value="Enterprise">Enterprise</option>
                <option value="Individual">Individual</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Email Address
              </label>
              <input
                type="email"
                placeholder="billing@apex.com"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Phone Number
              </label>
              <input
                type="tel"
                placeholder="+1 (555) 012-3456"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Tax ID / VAT
              </label>
              <input
                type="text"
                placeholder="US-12345678"
                value={formData.tax_identifier}
                onChange={(e) => setFormData({ ...formData, tax_identifier: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Credit Limit ($)
              </label>
              <input
                type="number"
                min="0"
                value={formData.credit_limit}
                onChange={(e) => setFormData({ ...formData, credit_limit: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Credit Terms (Days)
              </label>
              <input
                type="number"
                min="0"
                value={formData.credit_days}
                onChange={(e) => setFormData({ ...formData, credit_days: parseInt(e.target.value, 10) || 30 })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsAddModalOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={isSubmitting}>
              Register Customer
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
