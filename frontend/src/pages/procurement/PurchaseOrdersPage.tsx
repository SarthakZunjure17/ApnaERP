import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShoppingBag,
  Plus,
  Building2,
  Calendar,
  Filter,
  RefreshCw,
  Search,
  Eye,
  Trash2,
  DollarSign,
  Truck,
  CheckCircle2,
  Clock,
} from 'lucide-react';
import { procurementService } from '../../services/procurementService';
import { inventoryService } from '../../services/inventoryService';
import {
  PurchaseOrderListItem,
  SupplierItem,
  PurchaseOrderCreatePayload,
} from '../../types/procurement';
import { WarehouseOption, ProductItem } from '../../types/inventory';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Pagination } from '../../components/common/Pagination';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { EmptyState } from '../../components/common/EmptyState';
import { ErrorState } from '../../components/common/ErrorState';
import { KpiCard } from '../../components/common/KpiCard';
import { useToast } from '../../context/ToastContext';

export const PurchaseOrdersPage: React.FC = () => {
  const [orders, setOrders] = useState<PurchaseOrderListItem[]>([]);
  const [suppliers, setSuppliers] = useState<SupplierItem[]>([]);
  const [warehouses, setWarehouses] = useState<WarehouseOption[]>([]);
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [totalOrders, setTotalOrders] = useState(0);

  // Filters
  const [selectedSupplier, setSelectedSupplier] = useState('All');
  const [selectedStatus, setSelectedStatus] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create Modal
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form State
  const [formData, setFormData] = useState<PurchaseOrderCreatePayload>({
    supplier_id: '',
    warehouse_id: '',
    order_date: new Date().toISOString().split('T')[0],
    expected_delivery_date: new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0],
    payment_terms: 'Net 30',
    notes: '',
    items: [
      {
        product_id: '',
        quantity: 10,
        unit_price: 100,
        tax_rate: 0,
        discount_amount: 0,
      },
    ],
  });

  const pageSize = 10;
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  useEffect(() => {
    loadMetadata();
  }, []);

  useEffect(() => {
    loadOrders();
  }, [selectedSupplier, selectedStatus, searchQuery, currentPage]);

  const loadMetadata = async () => {
    try {
      const [supList, whList, prodList] = await Promise.all([
        procurementService.getSuppliers(),
        inventoryService.getWarehouses(),
        inventoryService.getProducts({ limit: 100 }),
      ]);
      setSuppliers(supList);
      setWarehouses(whList);
      setProducts(prodList.items);

      if (supList.length > 0 && !formData.supplier_id) {
        setFormData((prev) => ({ ...prev, supplier_id: supList[0].id }));
      }
      if (whList.length > 0 && !formData.warehouse_id) {
        setFormData((prev) => ({ ...prev, warehouse_id: whList[0].id }));
      }
      if (prodList.items.length > 0 && !formData.items[0]?.product_id) {
        setFormData((prev) => ({
          ...prev,
          items: [
            {
              product_id: prodList.items[0].id,
              quantity: 10,
              unit_price: prodList.items[0].cost_price || 50,
              tax_rate: 0,
              discount_amount: 0,
            },
          ],
        }));
      }
    } catch (err: any) {
      console.error('Failed to load procurement metadata', err);
    }
  };

  const loadOrders = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await procurementService.getPurchaseOrders({
        supplier_id: selectedSupplier !== 'All' ? selectedSupplier : undefined,
        status: selectedStatus !== 'All' ? selectedStatus : undefined,
        search: searchQuery || undefined,
        page: currentPage,
        size: pageSize,
      });
      setOrders(res.items);
      setTotalOrders(res.total);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load purchase orders');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddItem = () => {
    if (products.length === 0) return;
    setFormData({
      ...formData,
      items: [
        ...formData.items,
        {
          product_id: products[0].id,
          quantity: 1,
          unit_price: products[0].cost_price || 50,
          tax_rate: 0,
          discount_amount: 0,
        },
      ],
    });
  };

  const handleRemoveItem = (index: number) => {
    if (formData.items.length <= 1) return;
    setFormData({
      ...formData,
      items: formData.items.filter((_, i) => i !== index),
    });
  };

  const handleItemChange = (index: number, field: string, value: any) => {
    const updated = [...formData.items];
    updated[index] = { ...updated[index], [field]: value };

    if (field === 'product_id') {
      const prod = products.find((p) => p.id === value);
      if (prod) {
        updated[index].unit_price = prod.cost_price || 0;
      }
    }
    setFormData({ ...formData, items: updated });
  };

  const handleCreatePO = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.supplier_id || !formData.warehouse_id || formData.items.length === 0) {
      toastError('Please specify supplier, warehouse, and at least one item');
      return;
    }

    setIsSubmitting(true);
    try {
      const created = await procurementService.createPurchaseOrder(formData);
      success('Purchase Order Created', `PO ${created.po_number} successfully registered`);
      setIsCreateModalOpen(false);
      navigate(`/procurement/orders/${created.id}`);
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to create purchase order');
    } finally {
      setIsSubmitting(false);
    }
  };

  const totalSpend = orders.reduce((acc, o) => acc + (o.total_amount || 0), 0);
  const pendingCount = orders.filter((o) => o.status === 'Submitted' || o.status === 'Draft').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Purchase Orders</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Manage inbound vendor orders, track fulfillment, approvals, and stock deliveries
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            icon={<RefreshCw className="w-4 h-4" />}
            onClick={() => {
              loadMetadata();
              loadOrders();
            }}
          >
            Refresh
          </Button>
          <Button
            variant="primary"
            icon={<Plus className="w-4 h-4" />}
            onClick={() => {
              if (suppliers.length > 0 && !formData.supplier_id) {
                setFormData((prev) => ({ ...prev, supplier_id: suppliers[0].id }));
              }
              if (warehouses.length > 0 && !formData.warehouse_id) {
                setFormData((prev) => ({ ...prev, warehouse_id: warehouses[0].id }));
              }
              setIsCreateModalOpen(true);
            }}
          >
            New Purchase Order
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard
          title="Total Orders"
          value={totalOrders}
          icon={<ShoppingBag className="w-5 h-5 text-blue-600 dark:text-blue-400" />}
          description="Total purchase orders"
        />
        <KpiCard
          title="Pending / Draft"
          value={pendingCount}
          icon={<Clock className="w-5 h-5 text-amber-600 dark:text-amber-400" />}
          description="Awaiting approval / action"
        />
        <KpiCard
          title="Total Order Value"
          value={`$${totalSpend.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          icon={<DollarSign className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />}
          description="Sum of loaded orders"
        />
        <KpiCard
          title="Active Vendors"
          value={suppliers.length}
          icon={<Building2 className="w-5 h-5 text-purple-600 dark:text-purple-400" />}
          description="Registered suppliers"
        />
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700 shadow-sm flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search PO # or Supplier..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full pl-9 pr-4 py-2 bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={selectedSupplier}
              onChange={(e) => {
                setSelectedSupplier(e.target.value);
                setCurrentPage(1);
              }}
              className="bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="All">All Suppliers</option>
              {suppliers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>

          <select
            value={selectedStatus}
            onChange={(e) => {
              setSelectedStatus(e.target.value);
              setCurrentPage(1);
            }}
            className="bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="All">All Statuses</option>
            <option value="Draft">Draft</option>
            <option value="Submitted">Submitted</option>
            <option value="Approved">Approved</option>
            <option value="Received">Received</option>
            <option value="Cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      {/* Orders Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8">
            <LoadingState message="Loading purchase orders..." />
          </div>
        ) : error ? (
          <div className="p-8">
            <ErrorState title="Failed to load orders" message={error} onRetry={loadOrders} />
          </div>
        ) : orders.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No purchase orders found"
              description="Create a new purchase order to initiate procurement with suppliers."
              action={
                <Button
                  variant="primary"
                  icon={<Plus className="w-4 h-4" />}
                  onClick={() => setIsCreateModalOpen(true)}
                >
                  Create Purchase Order
                </Button>
              }
            />
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                  <tr>
                    <th className="px-6 py-4">PO Number</th>
                    <th className="px-6 py-4">Supplier</th>
                    <th className="px-6 py-4">Destination Warehouse</th>
                    <th className="px-6 py-4">Order Date</th>
                    <th className="px-6 py-4">Expected Date</th>
                    <th className="px-6 py-4 text-right">Total Amount</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4 text-right">View</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {orders.map((o) => (
                    <tr
                      key={o.id}
                      className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors cursor-pointer"
                      onClick={() => navigate(`/procurement/orders/${o.id}`)}
                    >
                      <td className="px-6 py-4 font-mono font-bold text-gray-900 dark:text-white">
                        {o.po_number}
                      </td>
                      <td className="px-6 py-4 font-medium text-gray-900 dark:text-white">
                        {o.supplier_name || 'Standard Supplier'}
                      </td>
                      <td className="px-6 py-4 text-gray-700 dark:text-gray-300">
                        {o.warehouse_name || 'Main Warehouse'}
                      </td>
                      <td className="px-6 py-4 text-xs text-gray-500">{o.order_date}</td>
                      <td className="px-6 py-4 text-xs text-gray-500">{o.expected_delivery_date || '-'}</td>
                      <td className="px-6 py-4 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                        ${Number(o.total_amount || 0).toFixed(2)}
                      </td>
                      <td className="px-6 py-4">
                        <StatusBadge
                          status={o.status}
                          variant={
                            o.status === 'Approved' || o.status === 'Received'
                              ? 'success'
                              : o.status === 'Submitted'
                              ? 'info'
                              : o.status === 'Rejected' || o.status === 'Cancelled'
                              ? 'error'
                              : 'default'
                          }
                        />
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/procurement/orders/${o.id}`);
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

            <div className="p-4 border-t border-gray-200 dark:border-gray-700">
              <Pagination
                currentPage={currentPage}
                totalItems={totalOrders}
                pageSize={pageSize}
                onPageChange={(page) => setCurrentPage(page)}
              />
            </div>
          </>
        )}
      </div>

      {/* Modal: Create Purchase Order */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create Purchase Order"
        size="lg"
      >
        <form onSubmit={handleCreatePO} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Supplier / Vendor *
              </label>
              <select
                required
                value={formData.supplier_id}
                onChange={(e) => setFormData({ ...formData, supplier_id: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                {suppliers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Destination Warehouse *
              </label>
              <select
                required
                value={formData.warehouse_id}
                onChange={(e) => setFormData({ ...formData, warehouse_id: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                {warehouses.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name} ({w.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Order Date *
              </label>
              <input
                type="date"
                required
                value={formData.order_date}
                onChange={(e) => setFormData({ ...formData, order_date: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Expected Delivery Date
              </label>
              <input
                type="date"
                value={formData.expected_delivery_date}
                onChange={(e) => setFormData({ ...formData, expected_delivery_date: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Line Items */}
          <div className="pt-2">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-semibold uppercase text-gray-700 dark:text-gray-300">
                Order Line Items
              </h4>
              <Button type="button" size="sm" variant="secondary" onClick={handleAddItem}>
                + Add Line Item
              </Button>
            </div>

            <div className="space-y-3">
              {formData.items.map((item, index) => (
                <div
                  key={index}
                  className="grid grid-cols-12 gap-2 items-center bg-gray-50 dark:bg-gray-700/40 p-3 rounded-lg border border-gray-200 dark:border-gray-700"
                >
                  <div className="col-span-5">
                    <label className="block text-[10px] uppercase text-gray-500 mb-0.5">Product</label>
                    <select
                      value={item.product_id}
                      onChange={(e) => handleItemChange(index, 'product_id', e.target.value)}
                      className="w-full px-2 py-1.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-xs text-gray-900 dark:text-white"
                    >
                      {products.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name} (${p.cost_price})
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
                      onChange={(e) =>
                        handleItemChange(index, 'quantity', parseInt(e.target.value, 10) || 1)
                      }
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
                      onChange={(e) =>
                        handleItemChange(index, 'unit_price', parseFloat(e.target.value) || 0)
                      }
                      className="w-full px-2 py-1.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-xs text-gray-900 dark:text-white"
                    />
                  </div>

                  <div className="col-span-1 text-right pt-4">
                    <button
                      type="button"
                      disabled={formData.items.length <= 1}
                      onClick={() => handleRemoveItem(index)}
                      className="text-gray-400 hover:text-red-500 disabled:opacity-30"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
              Internal Notes
            </label>
            <textarea
              rows={2}
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Delivery instructions, quotation references..."
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
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
              Submit Order
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
