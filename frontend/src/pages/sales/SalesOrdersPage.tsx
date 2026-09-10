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
  Send,
} from 'lucide-react';
import { salesService } from '../../services/salesService';
import { inventoryService } from '../../services/inventoryService';
import {
  SalesOrderListItem,
  CustomerItem,
  SalesOrderCreatePayload,
} from '../../types/sales';
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

export const SalesOrdersPage: React.FC = () => {
  const [orders, setOrders] = useState<SalesOrderListItem[]>([]);
  const [customers, setCustomers] = useState<CustomerItem[]>([]);
  const [warehouses, setWarehouses] = useState<WarehouseOption[]>([]);
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [totalOrders, setTotalOrders] = useState(0);

  // Filters
  const [selectedCustomer, setSelectedCustomer] = useState('All');
  const [selectedStatus, setSelectedStatus] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create Modal
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form State
  const [formData, setFormData] = useState<SalesOrderCreatePayload>({
    customer_id: '',
    warehouse_id: '',
    order_date: new Date().toISOString().split('T')[0],
    expected_delivery_date: new Date(Date.now() + 5 * 86400000).toISOString().split('T')[0],
    payment_terms: 'Net 30',
    notes: '',
    items: [
      {
        product_id: '',
        quantity: 5,
        unit_price: 150,
        discount_amount: 0,
        tax_rate: 0,
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
  }, [selectedCustomer, selectedStatus, searchQuery, currentPage]);

  const loadMetadata = async () => {
    try {
      const [custList, whList, prodList] = await Promise.all([
        salesService.getCustomers(),
        inventoryService.getWarehouses(),
        inventoryService.getProducts({ limit: 100 }),
      ]);
      setCustomers(custList);
      setWarehouses(whList);
      setProducts(prodList.items);

      if (custList.length > 0 && !formData.customer_id) {
        setFormData((prev) => ({ ...prev, customer_id: custList[0].id }));
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
              quantity: 5,
              unit_price: prodList.items[0].selling_price || 150,
              discount_amount: 0,
              tax_rate: 0,
            },
          ],
        }));
      }
    } catch (err: any) {
      console.error('Failed to load sales metadata', err);
    }
  };

  const loadOrders = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await salesService.getSalesOrders({
        customer_id: selectedCustomer !== 'All' ? selectedCustomer : undefined,
        status: selectedStatus !== 'All' ? selectedStatus : undefined,
        search: searchQuery || undefined,
        skip: (currentPage - 1) * pageSize,
        limit: pageSize,
      });
      setOrders(res.items);
      setTotalOrders(res.total);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load sales orders');
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
          unit_price: products[0].selling_price || 150,
          discount_amount: 0,
          tax_rate: 0,
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
        updated[index].unit_price = prod.selling_price || 0;
      }
    }
    setFormData({ ...formData, items: updated });
  };

  const handleCreateOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.customer_id || formData.items.length === 0) {
      toastError('Please select a customer and configure order items');
      return;
    }

    setIsSubmitting(true);
    try {
      const created = await salesService.createSalesOrder(formData);
      success('Sales Order Created', `SO ${created.order_number} successfully registered`);
      setIsCreateModalOpen(false);
      navigate(`/sales/orders/${created.id}`);
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to create sales order');
    } finally {
      setIsSubmitting(false);
    }
  };

  const totalRevenue = orders.reduce((acc, o) => acc + (o.total_amount || 0), 0);
  const pendingCount = orders.filter((o) => o.status === 'Submitted' || o.status === 'Draft').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Sales Orders</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Customer order fulfillment, approval workflow, shipping reservations, and revenue
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
              if (customers.length > 0 && !formData.customer_id) {
                setFormData((prev) => ({ ...prev, customer_id: customers[0].id }));
              }
              if (warehouses.length > 0 && !formData.warehouse_id) {
                setFormData((prev) => ({ ...prev, warehouse_id: warehouses[0].id }));
              }
              setIsCreateModalOpen(true);
            }}
          >
            New Sales Order
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard
          title="Total Orders"
          value={totalOrders}
          icon={<ShoppingBag className="w-5 h-5 text-blue-600 dark:text-blue-400" />}
          description="Customer sales orders"
        />
        <KpiCard
          title="Pending Fulfillment"
          value={pendingCount}
          icon={<Clock className="w-5 h-5 text-amber-600 dark:text-amber-400" />}
          description="Draft or awaiting approval"
        />
        <KpiCard
          title="Order Book Value"
          value={`$${totalRevenue.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          icon={<DollarSign className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />}
          description="Sum of loaded sales"
        />
        <KpiCard
          title="Active Customers"
          value={customers.length}
          icon={<Building2 className="w-5 h-5 text-purple-600 dark:text-purple-400" />}
          description="Registered client accounts"
        />
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700 shadow-sm flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search SO # or Customer..."
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
              value={selectedCustomer}
              onChange={(e) => {
                setSelectedCustomer(e.target.value);
                setCurrentPage(1);
              }}
              className="bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="All">All Customers</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
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
            <option value="Dispatched">Dispatched</option>
            <option value="Delivered">Delivered</option>
            <option value="Cancelled">Cancelled</option>
            <option value="Closed">Closed</option>
          </select>
        </div>
      </div>

      {/* Orders Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8">
            <LoadingState message="Loading sales orders..." />
          </div>
        ) : error ? (
          <div className="p-8">
            <ErrorState title="Failed to load orders" message={error} onRetry={loadOrders} />
          </div>
        ) : orders.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No sales orders found"
              description="Create a new sales order to initiate fulfillment and revenue generation."
              action={
                <Button
                  variant="primary"
                  icon={<Plus className="w-4 h-4" />}
                  onClick={() => setIsCreateModalOpen(true)}
                >
                  Create Sales Order
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
                    <th className="px-6 py-4">SO Number</th>
                    <th className="px-6 py-4">Customer</th>
                    <th className="px-6 py-4">Fulfillment Warehouse</th>
                    <th className="px-6 py-4">Order Date</th>
                    <th className="px-6 py-4 text-right">Total Value</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4 text-right">View</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {orders.map((o) => (
                    <tr
                      key={o.id}
                      className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors cursor-pointer"
                      onClick={() => navigate(`/sales/orders/${o.id}`)}
                    >
                      <td className="px-6 py-4 font-mono font-bold text-gray-900 dark:text-white">
                        {o.order_number}
                      </td>
                      <td className="px-6 py-4 font-medium text-gray-900 dark:text-white">
                        {o.customer_name || 'Client Account'}
                      </td>
                      <td className="px-6 py-4 text-gray-700 dark:text-gray-300">
                        {o.warehouse_name || 'Central Distribution'}
                      </td>
                      <td className="px-6 py-4 text-xs text-gray-500">{o.order_date}</td>
                      <td className="px-6 py-4 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                        ${Number(o.total_amount || 0).toFixed(2)}
                      </td>
                      <td className="px-6 py-4">
                        <StatusBadge
                          status={o.status}
                          variant={
                            o.status === 'Approved' || o.status === 'Delivered' || o.status === 'Closed'
                              ? 'success'
                              : o.status === 'Submitted' || o.status === 'In Production' || o.status === 'Dispatched'
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
                            navigate(`/sales/orders/${o.id}`);
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

      {/* Modal: Create Sales Order */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create Customer Sales Order"
        size="lg"
      >
        <form onSubmit={handleCreateOrder} className="space-y-4">
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
                Fulfillment Warehouse
              </label>
              <select
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
              Delivery Notes / Remarks
            </label>
            <textarea
              rows={2}
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Special customer requests, shipping instructions..."
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
              Create Order
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
