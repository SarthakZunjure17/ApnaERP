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
} from 'lucide-react';
import { procurementService } from '../../services/procurementService';
import { inventoryService } from '../../services/inventoryService';
import { PurchaseOrderDetail } from '../../types/procurement';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { ErrorState } from '../../components/common/ErrorState';
import { useToast } from '../../context/ToastContext';

export const PurchaseOrderDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [po, setPo] = useState<PurchaseOrderDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals & Action States
  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [isReceiveModalOpen, setIsReceiveModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  useEffect(() => {
    loadPo();
  }, [id]);

  const loadPo = async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await procurementService.getPurchaseOrderById(id);
      setPo(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load purchase order details');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!po) return;
    setIsSubmitting(true);
    try {
      const updated = await procurementService.submitPurchaseOrder(po.id);
      setPo(updated);
      success('PO Submitted', `${po.po_number} is now submitted for approval.`);
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to submit PO');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleApprove = async () => {
    if (!po) return;
    setIsSubmitting(true);
    try {
      const updated = await procurementService.approvePurchaseOrder(po.id);
      setPo(updated);
      success('PO Approved', `${po.po_number} has been approved.`);
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to approve PO');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!po) return;
    setIsSubmitting(true);
    try {
      const updated = await procurementService.rejectPurchaseOrder(po.id, rejectReason);
      setPo(updated);
      setIsRejectModalOpen(false);
      success('PO Rejected', `${po.po_number} was rejected.`);
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to reject PO');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = async () => {
    if (!po || !window.confirm('Are you sure you want to cancel this purchase order?')) return;
    setIsSubmitting(true);
    try {
      const updated = await procurementService.cancelPurchaseOrder(po.id);
      setPo(updated);
      success('PO Cancelled', `${po.po_number} has been cancelled.`);
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to cancel PO');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReceiveGoods = async () => {
    if (!po || !po.items || po.items.length === 0) return;
    setIsSubmitting(true);
    try {
      await inventoryService.createGoodsReceipt({
        warehouse_id: po.warehouse_id || '',
        supplier_id: po.supplier_id,
        po_id: po.id,
        receipt_date: new Date().toISOString().split('T')[0],
        items: po.items.map((item) => ({
          product_id: item.product_id,
          received_quantity: item.quantity,
          unit_cost: item.unit_price,
        })),
      });
      success('Goods Received', 'Stock has been booked into warehouse inventory.');
      setIsReceiveModalOpen(false);
      loadPo();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to receive goods');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-8">
        <LoadingState message="Loading purchase order details..." />
      </div>
    );
  }

  if (error || !po) {
    return (
      <div className="p-8">
        <ErrorState
          title="Purchase Order Not Found"
          message={error || 'The requested purchase order could not be located.'}
          onRetry={() => navigate('/procurement/orders')}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          <Link to="/procurement/orders" className="hover:text-blue-600 flex items-center gap-1">
            <ArrowLeft className="w-4 h-4" /> Purchase Orders
          </Link>
          <ChevronRight className="w-4 h-4" />
          <span className="font-mono font-bold text-gray-900 dark:text-white">{po.po_number}</span>
        </div>

        <div className="flex items-center gap-2">
          {po.status === 'Draft' && (
            <Button
              variant="primary"
              icon={<Send className="w-4 h-4" />}
              loading={isSubmitting}
              onClick={handleSubmit}
            >
              Submit for Approval
            </Button>
          )}

          {po.status === 'Submitted' && (
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
                Approve PO
              </Button>
            </>
          )}

          {po.status === 'Approved' && (
            <Button
              variant="primary"
              icon={<Boxes className="w-4 h-4" />}
              onClick={() => setIsReceiveModalOpen(true)}
            >
              Receive Goods (GRN)
            </Button>
          )}

          {['Draft', 'Submitted', 'Approved'].includes(po.status) && (
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

      {/* PO Overview Header Card */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold font-mono text-gray-900 dark:text-white">{po.po_number}</h1>
              <StatusBadge
                status={po.status}
                variant={
                  po.status === 'Approved' || po.status === 'Received'
                    ? 'success'
                    : po.status === 'Submitted'
                    ? 'info'
                    : po.status === 'Rejected' || po.status === 'Cancelled'
                    ? 'error'
                    : 'default'
                }
              />
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Order Date: {po.order_date} • Expected: {po.expected_delivery_date || 'Standard'}
            </p>
          </div>

          <div className="text-right">
            <span className="text-xs font-semibold uppercase text-gray-400">Total Purchase Value</span>
            <div className="text-3xl font-mono font-bold text-emerald-600 dark:text-emerald-400">
              ${Number(po.total_amount || 0).toFixed(2)}
            </div>
          </div>
        </div>

        {/* Info Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 pt-6">
          <div className="flex items-start gap-3">
            <Building2 className="w-5 h-5 text-blue-500 mt-0.5" />
            <div>
              <span className="text-xs text-gray-400 uppercase font-semibold">Vendor / Supplier</span>
              <p className="font-semibold text-gray-900 dark:text-white">{po.supplier_name || 'Vendor'}</p>
              <p className="text-xs text-gray-400">ID: {po.supplier_id}</p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <Truck className="w-5 h-5 text-purple-500 mt-0.5" />
            <div>
              <span className="text-xs text-gray-400 uppercase font-semibold">Destination Facility</span>
              <p className="font-semibold text-gray-900 dark:text-white">{po.warehouse_name || 'Warehouse'}</p>
              <p className="text-xs text-gray-400">Terms: {po.payment_terms || 'Net 30'}</p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <DollarSign className="w-5 h-5 text-emerald-500 mt-0.5" />
            <div>
              <span className="text-xs text-gray-400 uppercase font-semibold">Currency & Taxes</span>
              <p className="font-semibold text-gray-900 dark:text-white">{po.currency_code || 'USD'}</p>
              <p className="text-xs text-gray-400">Tax: ${Number(po.tax_amount || 0).toFixed(2)}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Line Items Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
          <h3 className="font-bold text-gray-900 dark:text-white">Order Line Items</h3>
          <span className="text-xs font-mono text-gray-500">{po.items?.length || 0} items</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
            <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
              <tr>
                <th className="px-6 py-4">Item / Product</th>
                <th className="px-6 py-4 text-right">Ordered Qty</th>
                <th className="px-6 py-4 text-right">Unit Cost</th>
                <th className="px-6 py-4 text-right">Tax Rate</th>
                <th className="px-6 py-4 text-right">Line Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {po.items?.map((item, idx) => (
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
                  <td className="px-6 py-4 text-right font-mono text-gray-500">{item.tax_rate || 0}%</td>
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
      {po.notes && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700 shadow-sm">
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Order Notes</h4>
          <p className="text-sm text-gray-600 dark:text-gray-300">{po.notes}</p>
        </div>
      )}

      {/* Modal: Reject PO */}
      <Modal
        isOpen={isRejectModalOpen}
        onClose={() => setIsRejectModalOpen(false)}
        title="Reject Purchase Order"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-300">
            Please provide an audit justification for rejecting order {po.po_number}:
          </p>
          <textarea
            rows={3}
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="Reason for rejection (e.g. over-budget, supplier mismatch)..."
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

      {/* Modal: Receive Goods Confirmation */}
      <Modal
        isOpen={isReceiveModalOpen}
        onClose={() => setIsReceiveModalOpen(false)}
        title="Receive Goods into Inventory"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-300">
            This action will generate a formal <strong>Goods Receipt Note (GRN)</strong> and update
            on-hand stock balances across the designated warehouse for all items in order{' '}
            <strong>{po.po_number}</strong>.
          </p>
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button variant="secondary" onClick={() => setIsReceiveModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" loading={isSubmitting} onClick={handleReceiveGoods}>
              Confirm & Book Inbound Stock
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
