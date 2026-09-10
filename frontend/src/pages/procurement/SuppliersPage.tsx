import React, { useState, useEffect } from 'react';
import {
  Building2,
  FileText,
  FileCheck2,
  Plus,
  RefreshCw,
  Search,
  Mail,
  Phone,
  CheckCircle2,
  XCircle,
  Clock,
  Layers,
} from 'lucide-react';
import { procurementService } from '../../services/procurementService';
import {
  SupplierItem,
  PurchaseRequisitionItem,
  RFQItem,
} from '../../types/procurement';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { EmptyState } from '../../components/common/EmptyState';
import { ErrorState } from '../../components/common/ErrorState';
import { KpiCard } from '../../components/common/KpiCard';
import { useToast } from '../../context/ToastContext';

type TabType = 'suppliers' | 'requisitions' | 'rfqs';

export const SuppliersPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('suppliers');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Data
  const [suppliers, setSuppliers] = useState<SupplierItem[]>([]);
  const [requisitions, setRequisitions] = useState<PurchaseRequisitionItem[]>([]);
  const [rfqs, setRfqs] = useState<RFQItem[]>([]);

  // Modals
  const [isAddSupplierModalOpen, setIsAddSupplierModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // New Supplier Form
  const [supplierForm, setSupplierForm] = useState({
    name: '',
    code: '',
    contact_person: '',
    email: '',
    phone: '',
    tax_identifier: '',
  });

  const [searchQuery, setSearchQuery] = useState('');
  const { success, error: toastError } = useToast();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [supList, prList, rfqList] = await Promise.all([
        procurementService.getSuppliers(),
        procurementService.getRequisitions(),
        procurementService.getRFQs(),
      ]);
      setSuppliers(supList);
      setRequisitions(prList);
      setRfqs(rfqList);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load procurement vendors and requests');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateSupplier = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!supplierForm.name || !supplierForm.code) {
      toastError('Vendor name and code are required');
      return;
    }
    setIsSubmitting(true);
    try {
      await procurementService.createSupplier({
        ...supplierForm,
        is_active: true,
      });
      success('Supplier Registered', `${supplierForm.name} added to vendor directory.`);
      setIsAddSupplierModalOpen(false);
      setSupplierForm({
        name: '',
        code: '',
        contact_person: '',
        email: '',
        phone: '',
        tax_identifier: '',
      });
      loadData();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to register supplier');
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredSuppliers = suppliers.filter(
    (s) =>
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.email?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Vendor Directory & Inbound RFQs</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Supplier master records, purchase requisitions, and vendor quotation requests
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" icon={<RefreshCw className="w-4 h-4" />} onClick={loadData}>
            Refresh
          </Button>
          {activeTab === 'suppliers' && (
            <Button
              variant="primary"
              icon={<Plus className="w-4 h-4" />}
              onClick={() => setIsAddSupplierModalOpen(true)}
            >
              Add Vendor
            </Button>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KpiCard
          title="Active Vendors"
          value={suppliers.filter((s) => s.is_active).length}
          icon={<Building2 className="w-5 h-5 text-blue-600 dark:text-blue-400" />}
          description="Approved procurement partners"
        />
        <KpiCard
          title="Purchase Requisitions"
          value={requisitions.length}
          icon={<FileText className="w-5 h-5 text-purple-600 dark:text-purple-400" />}
          description="Internal department requests"
        />
        <KpiCard
          title="Active RFQs"
          value={rfqs.length}
          icon={<FileCheck2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />}
          description="Vendor quotation tenders"
        />
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 space-x-2">
        <button
          onClick={() => setActiveTab('suppliers')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'suppliers'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <Building2 className="w-4 h-4" /> Vendors & Suppliers ({suppliers.length})
        </button>
        <button
          onClick={() => setActiveTab('requisitions')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'requisitions'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <FileText className="w-4 h-4" /> Requisitions ({requisitions.length})
        </button>
        <button
          onClick={() => setActiveTab('rfqs')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'rfqs'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <FileCheck2 className="w-4 h-4" /> RFQ Tenders ({rfqs.length})
        </button>
      </div>

      {/* Main Content Area */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8">
            <LoadingState message="Loading procurement records..." />
          </div>
        ) : error ? (
          <div className="p-8">
            <ErrorState title="Failed to load data" message={error} onRetry={loadData} />
          </div>
        ) : (
          <>
            {/* Tab: Suppliers */}
            {activeTab === 'suppliers' && (
              <div className="p-4 space-y-4">
                <div className="relative w-full md:w-80">
                  <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search vendor by name, code, email..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-4 py-2 bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                    <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                      <tr>
                        <th className="px-6 py-4">Code</th>
                        <th className="px-6 py-4">Supplier Name</th>
                        <th className="px-6 py-4">Contact Person</th>
                        <th className="px-6 py-4">Contact Details</th>
                        <th className="px-6 py-4">Tax ID</th>
                        <th className="px-6 py-4">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                      {filteredSuppliers.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="px-6 py-8 text-center text-gray-400">
                            No suppliers found. Click "Add Vendor" to register a supplier.
                          </td>
                        </tr>
                      ) : (
                        filteredSuppliers.map((s) => (
                          <tr key={s.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                            <td className="px-6 py-4 font-mono font-bold text-gray-900 dark:text-white">{s.code}</td>
                            <td className="px-6 py-4 font-semibold text-gray-900 dark:text-white">{s.name}</td>
                            <td className="px-6 py-4">{s.contact_person || '-'}</td>
                            <td className="px-6 py-4 space-y-0.5">
                              {s.email && (
                                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                                  <Mail className="w-3.5 h-3.5 text-gray-400" /> {s.email}
                                </div>
                              )}
                              {s.phone && (
                                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                                  <Phone className="w-3.5 h-3.5 text-gray-400" /> {s.phone}
                                </div>
                              )}
                            </td>
                            <td className="px-6 py-4 font-mono text-xs text-gray-500">{s.tax_identifier || '-'}</td>
                            <td className="px-6 py-4">
                              <StatusBadge
                                status={s.is_active ? 'Active' : 'Inactive'}
                                variant={s.is_active ? 'success' : 'default'}
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

            {/* Tab: Requisitions */}
            {activeTab === 'requisitions' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                  <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                    <tr>
                      <th className="px-6 py-4">PR Number</th>
                      <th className="px-6 py-4">Department</th>
                      <th className="px-6 py-4">Requisition Date</th>
                      <th className="px-6 py-4 text-right">Est. Total Amount</th>
                      <th className="px-6 py-4">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {requisitions.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-6 py-8 text-center text-gray-400">
                          No internal purchase requisitions found.
                        </td>
                      </tr>
                    ) : (
                      requisitions.map((pr) => (
                        <tr key={pr.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                          <td className="px-6 py-4 font-mono font-bold text-gray-900 dark:text-white">{pr.pr_number}</td>
                          <td className="px-6 py-4">{pr.department_name || 'General Dept'}</td>
                          <td className="px-6 py-4 text-xs text-gray-500">{pr.requisition_date}</td>
                          <td className="px-6 py-4 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                            ${Number(pr.total_estimated_amount || 0).toFixed(2)}
                          </td>
                          <td className="px-6 py-4">
                            <StatusBadge status={pr.status} variant={pr.status === 'Approved' ? 'success' : 'default'} />
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* Tab: RFQs */}
            {activeTab === 'rfqs' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                  <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                    <tr>
                      <th className="px-6 py-4">RFQ Number</th>
                      <th className="px-6 py-4">Title / Specification</th>
                      <th className="px-6 py-4">Issue Date</th>
                      <th className="px-6 py-4">Close Date</th>
                      <th className="px-6 py-4">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {rfqs.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-6 py-8 text-center text-gray-400">
                          No active RFQ tenders found.
                        </td>
                      </tr>
                    ) : (
                      rfqs.map((rfq) => (
                        <tr key={rfq.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                          <td className="px-6 py-4 font-mono font-bold text-gray-900 dark:text-white">
                            {rfq.rfq_number}
                          </td>
                          <td className="px-6 py-4 font-medium text-gray-900 dark:text-white">{rfq.title}</td>
                          <td className="px-6 py-4 text-xs text-gray-500">{rfq.issue_date}</td>
                          <td className="px-6 py-4 text-xs text-gray-500">{rfq.close_date || '-'}</td>
                          <td className="px-6 py-4">
                            <StatusBadge
                              status={rfq.status}
                              variant={rfq.status === 'Sent' ? 'info' : 'default'}
                            />
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>

      {/* Modal: Add Supplier */}
      <Modal
        isOpen={isAddSupplierModalOpen}
        onClose={() => setIsAddSupplierModalOpen(false)}
        title="Register Vendor / Supplier"
        size="md"
      >
        <form onSubmit={handleCreateSupplier} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Vendor Code *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. SUP-001"
                value={supplierForm.code}
                onChange={(e) => setSupplierForm({ ...supplierForm, code: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Company Name *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Apex Industrial Supplies"
                value={supplierForm.name}
                onChange={(e) => setSupplierForm({ ...supplierForm, name: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
              Primary Contact Person
            </label>
            <input
              type="text"
              placeholder="e.g. Sarah Jenkins"
              value={supplierForm.contact_person}
              onChange={(e) => setSupplierForm({ ...supplierForm, contact_person: e.target.value })}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Email
              </label>
              <input
                type="email"
                placeholder="vendor@company.com"
                value={supplierForm.email}
                onChange={(e) => setSupplierForm({ ...supplierForm, email: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Phone
              </label>
              <input
                type="tel"
                placeholder="+1 555-0199"
                value={supplierForm.phone}
                onChange={(e) => setSupplierForm({ ...supplierForm, phone: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
              Tax ID / VAT
            </label>
            <input
              type="text"
              placeholder="e.g. US-99887766"
              value={supplierForm.tax_identifier}
              onChange={(e) => setSupplierForm({ ...supplierForm, tax_identifier: e.target.value })}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsAddSupplierModalOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={isSubmitting}>
              Register Vendor
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
