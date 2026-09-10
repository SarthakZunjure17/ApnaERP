import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  Building2,
  Truck,
  CheckCircle2,
  XCircle,
  ChevronRight,
  Clock,
  Calendar,
  DollarSign,
  Package,
  Send,
  Boxes,
  Ban,
  ArrowLeft,
  CheckCheck,
} from 'lucide-react';
import { salesService } from '../../services/salesService';
import { SalesOrderDetail } from '../../types/sales';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { ErrorState } from '../../components/common/ErrorState';
import { useToast } from '../../context/ToastContext';

export const SalesOrderDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [so, setSo] = useState<SalesOrderDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals & Action States
  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  useEffect(() => {
    loadSo();
  }, [id]);

  const loadSo = async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await salesService.getSalesOrderById(id);
      setSo(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load sales order details');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!so) return;
    setIsSubmitting(true);
    try {
      const updated = await salesService.submitSalesOrder(so.id);
      setSo(updated);
      success('Order Submitted', `${so.order_number} submitted for management approval.`);
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to submit order');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleApprove = async () => {
    if (!so) return;
    setIsSubmitting(true);
    try {
      const updated = await salesService.approveSalesOrder(so.id);
      setSo(updated);
      success('Order Approved', `${so.order_number} has been approved.`);
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to approve order');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!so) return;
    setIsSubmitting(true);
    try {
      const updated = await salesService.rejectSalesOrder(so.id, rejectReason);
      setSo(updated);
      setIsRejectModalOpen(false);
      success('Order Rejected', `${so.order_number} was rejected.`);
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to reject order');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = async () => {
    if (!so || !window.confirm('Are you sure you want to cancel this order?')) return;
    setIsSubmitting(true);
    try {
      const updated = await salesService.cancelSalesOrder(so.id);
      setSo(updated);
      success('Order Cancelled', `${so.order_number} has been cancelled.`);
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to cancel order');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = async () => {
    if (!so) return;
    setIsSubmitting(true);
    try {
      const updated = await salesService.closeSalesOrder(so.id);
      setSo(updated);
      success('Order Closed', `${so.order_number} successfully fulfilled & closed.`);
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to close order');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-8">
        <LoadingState message="Loading sales order details..." />
      </div>
    );
  }

  if (error || !so) {
    return (
      <div className="p-8">
        <ErrorState
          title="Sales Order Not Found"
          message={error || 'The requested sales order could not be located.'}
          onRetry={() => navigate('/sales/orders')}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          <Link to="/sales/orders" className="hover:text-blue-600 flex items-center gap-1">
            <ArrowLeft className="w-4 h-4" /> Sales Orders
          </Link>
          <ChevronRight className="w-4 h-4" />
          <span className="font-mono font-bold text-gray-900 dark:text-white">{so.order_number}</span>
        </div>

        <div className="flex items-center gap-2">
          {so.status === 'Draft' && (
            <Button
              variant="primary"
              icon={<Send className="w-4 h-4" />}
              loading={isSubmitting}
              onClick={handleSubmit}
            >
              Submit Order
            </Button>
          )}

          {so.status === 'Submitted' && (
            <>
              <Button
                variant="secondary"
                icon={<XCircle className="w-4 h-4 text-red-500" />}
                onClick={() => setIsRejectModalOpen(true)}
              >
                Reject
              </Button>
              <Button
                variant="primary"
                icon={<CheckCircle2 className="w-4 h-4" />}
                loading={isSubmitting}
                onClick={handleApprove}
              >
                Approve Order
              </Button>
            </>
          )}

          {so.status === 'Approved' && (
            <Button
              variant="primary"
              icon={<CheckCheck className="w-4 h-4" />}
              loading={isSubmitting}
              onClick={handleClose}
            >
              Close / Complete Order
            </Button>
          )}

          {['Draft', 'Submitted', 'Approved'].includes(so.status) && (
            <Button
              variant="secondary"
              icon={<Ban className="w-4 h-4 text-gray-400" />}
              loading={isSubmitting}
              onClick={handleCancel}
            >
              Cancel
            </Button>
          )}
        </div>
      </div>

      {/* Overview Header Card */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold font-mono text-gray-900 dark:text-white">{so.order_number}</h1>
              <StatusBadge
                status={so.status}
                variant={
                  so.status === 'Approved' || so.status === 'Delivered' || so.status === 'Closed'
                    ? 'success'
                    : so.status === 'Submitted' || so.status === 'In Production' || so.status === 'Dispatched'
                    ? 'info'
                    : so.status === 'Rejected' || so.status === 'Cancelled'
                    ? 'error'
                    : 'default'
                }
              />
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Order Date: {so.order_date} • Currency: {so.currency_code || 'USD'}
            </p>
          </div>

          <div className="text-right">
            <span className="text-xs font-semibold uppercase text-gray-400">Total Order Revenue</span>
            <div className="text-3xl font-mono font-bold text-emerald-600 dark:text-emerald-400">
              ${Number(so.total_amount || 0).toFixed(2)}
            </div>
          </div>
        </div>

        {/* Info Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 pt-6">
          <div className="flex items-start gap-3">
            <Building2 className="w-5 h-5 text-blue-500 mt-0.5" />
            <div>
              <span className="text-xs text-gray-400 uppercase font-semibold">Customer Account</span>
              <p className="font-semibold text-gray-900 dark:text-white">{so.customer_name || 'Client'}</p>
              <p className="text-xs text-gray-400">ID: {so.customer_id}</p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <Truck className="w-5 h-5 text-purple-500 mt-0.5" />
            <div>
              <span className="text-xs text-gray-400 uppercase font-semibold">Fulfillment Center</span>
              <p className="font-semibold text-gray-900 dark:text-white">{so.warehouse_name || 'Central WH'}</p>
              <p className="text-xs text-gray-400">Terms: {so.payment_terms || 'Net 30'}</p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <DollarSign className="w-5 h-5 text-emerald-500 mt-0.5" />
            <div>
              <span className="text-xs text-gray-400 uppercase font-semibold">Financial Summary</span>
              <p className="text-xs text-gray-600 dark:text-gray-300">Subtotal: ${Number(so.subtotal || 0).toFixed(2)}</p>
              <p className="text-xs text-gray-600 dark:text-gray-300">Taxes: ${Number(so.tax_amount || 0).toFixed(2)}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Line Items Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
          <h3 className="font-bold text-gray-900 dark:text-white">Order Line Items</h3>
          <span className="text-xs font-mono text-gray-500">{so.items?.length || 0} items</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
            <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
              <tr>
                <th className="px-6 py-4">Item / Product</th>
                <th className="px-6 py-4 text-right">Ordered Qty</th>
                <th className="px-6 py-4 text-right">Unit Price</th>
                <th className="px-6 py-4 text-right">Discount</th>
                <th className="px-6 py-4 text-right">Line Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {so.items?.map((item, idx) => (
                <tr key={item.id || idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                  <td className="px-6 py-4">
                    <div className="font-medium text-gray-900 dark:text-white">
                      {item.product_name || `Product (${item.product_id.substring(0, 8)})`}
                    </div>
                    {item.product_sku && (
                      <div className="text-xs font-mono text-gray-400">SKU: {item.product_sku}</div>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right font-mono font-bold text-gray-900 dark:text-white">
                    {item.quantity}
                  </td>
                  <td className="px-6 py-4 text-right font-mono text-gray-900 dark:text-white">
                    ${Number(item.unit_price || 0).toFixed(2)}
                  </td>
                  <td className="px-6 py-4 text-right font-mono text-gray-500">
                    ${Number(item.discount_amount || 0).toFixed(2)}
                  </td>
                  <td className="px-6 py-4 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                    ${Number(item.total_price || item.quantity * item.unit_price).toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Notes */}
      {so.notes && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700 shadow-sm">
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Delivery Instructions</h4>
          <p className="text-sm text-gray-600 dark:text-gray-300">{so.notes}</p>
        </div>
      )}

      {/* Modal: Reject SO */}
      <Modal
        isOpen={isRejectModalOpen}
        onClose={() => setIsRejectModalOpen(false)}
        title="Reject Sales Order"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-300">
            Please provide an audit justification for rejecting order {so.order_number}:
          </p>
          <textarea
            rows={3}
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="Reason for rejection (e.g. credit hold, inventory constraint)..."
            className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
          />
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button variant="secondary" onClick={() => setIsRejectModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" loading={isSubmitting} onClick={handleReject}>
              Confirm Rejection
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
