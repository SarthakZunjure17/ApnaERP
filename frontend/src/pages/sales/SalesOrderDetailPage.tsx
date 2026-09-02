import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  FileText,
  Building2,
  Truck,
  CheckCircle2,
  XCircle,
  Pencil,
  Send,
  ChevronRight,
  Clock,
  Mail,
  MapPin,
  Calendar,
  CreditCard,
  User,
  AlertCircle,
  PackageCheck,
  Printer,
  ShieldCheck,
} from 'lucide-react';
import { salesService } from '../../services/salesService';
import { SalesOrderDetail } from '../../types/sales';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { useToast } from '../../context/ToastContext';

export const SalesOrderDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [order, setOrder] = useState<SalesOrderDetail | null>(null);
  const [newComment, setNewComment] = useState('');
  const [isCancelModalOpen, setIsCancelModalOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const navigate = useNavigate();
  const { success, info } = useToast();

  useEffect(() => {
    loadOrderDetail();
  }, [id]);

  const loadOrderDetail = async () => {
    setIsLoading(true);
    if (!id) {
      setOrder(null);
      setIsLoading(false);
      return;
    }
    const data = await salesService.getSalesOrderById(id);
    setOrder(data);
    setIsLoading(false);
  };

  const handleConfirmOrder = async () => {
    if (!order) return;
    const updated = await salesService.updateOrderStatus(order.id, 'Confirmed');
    if (updated) {
      setOrder(updated);
      success('Order Confirmed', `${order.order_number} has been confirmed.`);
    }
  };

  const handleFulfillOrder = async () => {
    if (!order) return;
    const updated = await salesService.updateOrderStatus(order.id, 'Completed', 'Delivered');
    if (updated) {
      setOrder(updated);
      success('Fulfillment Updated', `${order.order_number} marked as Delivered.`);
    }
  };

  const handleCancelOrder = async () => {
    if (!order) return;
    const updated = await salesService.updateOrderStatus(order.id, 'Cancelled', 'Cancelled');
    if (cancelReason.trim()) {
      await salesService.addComment(order.id, `Order Cancelled: ${cancelReason}`);
    }
    if (updated) {
      setOrder(updated);
      setIsCancelModalOpen(false);
      success('Order Cancelled', `${order.order_number} has been cancelled.`);
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!order || !newComment.trim()) return;

    const updated = await salesService.addComment(order.id, newComment.trim());
    if (updated) {
      setOrder(updated);
      setNewComment('');
      success('Note Added', 'Internal sales note recorded.');
    }
  };

  const handlePrint = () => {
    info('Generating Invoice', `Preparing printable invoice for ${order?.order_number}...`);
    window.print();
  };

  if (isLoading) {
    return <LoadingState message="Loading sales order..." />;
  }

  if (!order) {
    return (
      <div className="space-y-4 sm:space-y-5 animate-fade-in pb-10">
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <Link to="/sales/orders" className="hover:text-brand-600 transition-colors">
            Sales
          </Link>
          <ChevronRight className="w-3.5 h-3.5" />
          <Link to="/sales/orders" className="hover:text-brand-600 transition-colors">
            Orders
          </Link>
          <ChevronRight className="w-3.5 h-3.5" />
          <span className="font-semibold text-slate-700 dark:text-slate-200">Not Found</span>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800 rounded-2xl p-8 sm:p-12 text-center max-w-lg mx-auto shadow-xs">
          <div className="w-12 h-12 rounded-full bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 flex items-center justify-center mx-auto mb-4 border border-rose-100 dark:border-rose-900/40">
            <FileText className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Sales Order Not Found</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1.5 max-w-xs mx-auto">
            No sales order was found matching ID <span className="font-mono font-semibold text-slate-700 dark:text-slate-300">"{id}"</span>.
          </p>
          <div className="mt-6">
            <Link
              to="/sales/orders"
              className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors"
            >
              Back to Sales Orders
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-5 animate-fade-in pb-10">
      {/* Top Breadcrumb & Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          {/* Breadcrumb line with Order Badge and Status */}
          <div className="flex items-center gap-2 text-xs flex-wrap">
            <Link to="/sales/orders" className="text-slate-400 hover:text-brand-600 transition-colors font-bold uppercase tracking-wider text-[10px]">
              SALES ORDERS
            </Link>
            <span className="text-slate-300 dark:text-slate-700">/</span>
            <span className="px-2 py-0.5 rounded bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300 font-mono font-semibold text-[11px]">
              {order.order_number}
            </span>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />
              {order.status}
            </span>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              {order.payment_status}
            </span>
          </div>

          {/* Customer Title */}
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white mt-1.5">
            {order.customer_name}
          </h1>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 self-start md:self-center flex-wrap">
          <button
            onClick={() => navigate('/sales/orders')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-200 rounded-lg text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            <ChevronRight className="w-3.5 h-3.5 rotate-180 text-slate-400" />
            Back to List
          </button>

          <button
            onClick={handlePrint}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-200 rounded-lg text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            <Printer className="w-3.5 h-3.5 text-slate-400" />
            Invoice
          </button>

          {order.status !== 'Cancelled' && (
            <button
              onClick={() => setIsCancelModalOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-100 hover:bg-rose-200 dark:bg-rose-950 dark:hover:bg-rose-900 text-rose-700 dark:text-rose-300 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
            >
              <XCircle className="w-3.5 h-3.5" />
              Cancel Order
            </button>
          )}

          {order.fulfillment_status !== 'Delivered' && order.status !== 'Cancelled' && (
            <button
              onClick={handleFulfillOrder}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors cursor-pointer"
            >
              <PackageCheck className="w-3.5 h-3.5" />
              Mark Delivered
            </button>
          )}
        </div>
      </div>

      {/* Top 3 Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        {/* Card 1: Customer Details (Col span 4) */}
        <div className="md:col-span-4 bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-3.5">
              <div className="w-6 h-6 rounded-md bg-purple-50 dark:bg-purple-950 flex items-center justify-center text-purple-600 dark:text-purple-300">
                <Building2 className="w-3.5 h-3.5" />
              </div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Customer & Account
              </h3>
            </div>

            <div className="space-y-2.5 text-xs">
              <div>
                <span className="text-[10px] font-semibold text-slate-400 uppercase block">
                  Organization
                </span>
                <p className="font-semibold text-slate-900 dark:text-white mt-0.5">
                  {order.customer_company || order.customer_name}
                </p>
              </div>

              <div>
                <span className="text-[10px] font-semibold text-slate-400 uppercase block">
                  Contact
                </span>
                <div className="flex items-center justify-between mt-0.5">
                  <span className="text-slate-800 dark:text-slate-200 font-medium">
                    {order.customer_phone}
                  </span>
                  <a
                    href={`mailto:${order.customer_email}`}
                    className="text-brand-600 hover:underline font-mono text-[11px]"
                  >
                    {order.customer_email}
                  </a>
                </div>
              </div>

              <div>
                <span className="text-[10px] font-semibold text-slate-400 uppercase block">
                  Sales Representative
                </span>
                <div className="flex items-center gap-2 mt-1 p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                  <img
                    src={order.sales_rep.avatar_url}
                    alt={order.sales_rep.name}
                    className="w-7 h-7 rounded-full object-cover shrink-0 ring-1 ring-white"
                  />
                  <div>
                    <p className="font-semibold text-slate-900 dark:text-white leading-tight">
                      {order.sales_rep.name}
                    </p>
                    <p className="text-[10px] text-slate-400 mt-0.5 leading-tight">
                      {order.sales_rep.designation}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Card 2: Shipping & Terms (Col span 4) */}
        <div className="md:col-span-4 bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-3.5">
              <div className="w-6 h-6 rounded-md bg-blue-50 dark:bg-blue-950 flex items-center justify-center text-blue-600 dark:text-blue-400">
                <Truck className="w-3.5 h-3.5" />
              </div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Fulfillment & Logistics
              </h3>
            </div>

            <div className="space-y-2.5 text-xs">
              <div>
                <span className="text-[10px] font-semibold text-slate-400 uppercase block">
                  Shipping Destination
                </span>
                <p className="text-slate-800 dark:text-slate-200 mt-0.5 leading-relaxed whitespace-pre-line">
                  {order.shipping_address}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-1">
                <div>
                  <span className="text-[10px] font-semibold text-slate-400 uppercase block">
                    Expected Delivery
                  </span>
                  <span className="text-slate-800 dark:text-slate-200 font-medium mt-0.5 block">
                    {order.expected_delivery}
                  </span>
                </div>

                <div>
                  <span className="text-[10px] font-semibold text-slate-400 uppercase block">
                    Tracking Number
                  </span>
                  <span className="font-mono text-brand-600 dark:text-blue-400 font-semibold mt-0.5 block">
                    {order.tracking_number || 'TRK-PENDING'}
                  </span>
                </div>
              </div>

              <div className="pt-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase block">
                  Payment Terms
                </span>
                <span className="text-slate-800 dark:text-slate-200 font-medium mt-0.5 block">
                  {order.payment_terms}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Card 3: Order Timeline (Col span 4) */}
        <div className="md:col-span-4 bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-3.5">
            Order Status & History
          </h3>

          <div className="space-y-3.5 relative pl-4 border-l-2 border-slate-100 dark:border-slate-800 text-xs">
            {(order.timeline || []).map((step) => {
              const isCompleted = step.status === 'completed';
              const isCurrent = step.status === 'current';

              return (
                <div key={step.id} className="relative">
                  <div
                    className={`absolute -left-[23px] top-0.5 w-3 h-3 rounded-full ring-2 ring-white dark:ring-slate-900 ${
                      isCompleted
                        ? 'bg-purple-600'
                        : isCurrent
                        ? 'bg-amber-500'
                        : 'bg-slate-300'
                    }`}
                  />

                  <div>
                    <span className="text-[10px] text-slate-400 font-medium block">
                      {step.timestamp}
                    </span>
                    <p className="font-bold text-slate-900 dark:text-white mt-0.5">
                      {step.title}
                    </p>
                    <span className="text-[11px] text-slate-500 dark:text-slate-400">
                      {step.description}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom Grid: Line Items Table & Internal Notes */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        {/* Line Items Table & Financial Totals (Col span 8) */}
        <div className="md:col-span-8 space-y-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-3.5">
              Ordered Products & Services
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-100 dark:border-slate-800 text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                    <th className="py-2 px-2.5">Item & Specification</th>
                    <th className="py-2 px-2.5">SKU</th>
                    <th className="py-2 px-2.5 text-center">Qty</th>
                    <th className="py-2 px-2.5 text-right">Unit Price</th>
                    <th className="py-2 px-2.5 text-center">Tax</th>
                    <th className="py-2 px-2.5 text-right">Subtotal</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100/80 dark:divide-slate-800/60 text-xs">
                  {(order.items || []).map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50/50">
                      <td className="py-3 px-2.5">
                        <p className="font-semibold text-slate-900 dark:text-white">
                          {item.item_name}
                        </p>
                        <p className="text-[11px] text-slate-400">{item.description}</p>
                      </td>
                      <td className="py-3 px-2.5 font-mono text-[11px] text-slate-600 dark:text-slate-400">
                        {item.sku}
                      </td>
                      <td className="py-3 px-2.5 text-center font-medium text-slate-800 dark:text-slate-200">
                        {item.quantity}
                      </td>
                      <td className="py-3 px-2.5 text-right text-slate-800 dark:text-slate-200">
                        {item.formatted_unit_price}
                      </td>
                      <td className="py-3 px-2.5 text-center text-slate-500">
                        {item.tax_rate}%
                      </td>
                      <td className="py-3 px-2.5 text-right font-medium text-slate-900 dark:text-white">
                        {item.formatted_subtotal}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Financial Summary Box */}
            <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 flex justify-end">
              <div className="w-full sm:w-64 space-y-1.5 text-xs">
                <div className="flex justify-between text-slate-500">
                  <span>Subtotal</span>
                  <span className="font-medium text-slate-800 dark:text-slate-200">
                    {order.formatted_subtotal}
                  </span>
                </div>
                <div className="flex justify-between text-slate-500">
                  <span>Estimated Tax</span>
                  <span className="font-medium text-slate-800 dark:text-slate-200">
                    {order.formatted_tax}
                  </span>
                </div>
                <div className="flex justify-between text-slate-500">
                  <span>Shipping & Handling</span>
                  <span className="font-medium text-slate-800 dark:text-slate-200">
                    {order.formatted_shipping}
                  </span>
                </div>
                {order.discount_amount > 0 && (
                  <div className="flex justify-between text-emerald-600">
                    <span>Discount Applied</span>
                    <span className="font-medium">{order.formatted_discount}</span>
                  </div>
                )}
                <div className="flex justify-between pt-2 border-t border-slate-200 dark:border-slate-700 text-sm font-bold text-slate-900 dark:text-white">
                  <span>Total Amount</span>
                  <span className="text-base font-bold text-slate-900 dark:text-white">
                    {order.formatted_total}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Internal Comments Section (Col span 4) */}
        <div className="md:col-span-4 bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3.5">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Internal Sales Notes
              </h3>
              <span className="w-5 h-5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 flex items-center justify-center font-bold text-[10px]">
                {(order.comments || []).length}
              </span>
            </div>

            <div className="space-y-3 max-h-72 overflow-y-auto">
              {(order.comments || []).map((comment) => (
                <div
                  key={comment.id}
                  className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 text-xs"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-slate-900 dark:text-white">
                      {comment.author_name}
                    </span>
                    <span className="text-[10px] text-slate-400">{comment.time_ago}</span>
                  </div>
                  <p className="text-slate-600 dark:text-slate-300 leading-relaxed italic text-[11px]">
                    {comment.content}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Comment Input */}
          <form onSubmit={handleAddComment} className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800">
            <div className="relative">
              <textarea
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder="Add an internal note..."
                rows={3}
                className="w-full p-2.5 pb-8 bg-blue-50/40 dark:bg-slate-800/80 border border-blue-100 dark:border-slate-700 rounded-lg text-xs text-slate-800 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-brand-500 resize-none"
              />
              <button
                type="submit"
                disabled={!newComment.trim()}
                className="absolute bottom-2 right-2 p-1.5 bg-brand-600 hover:bg-brand-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 text-white rounded-md transition-colors cursor-pointer"
                title="Send Note"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Cancel Modal */}
      <Modal
        isOpen={isCancelModalOpen}
        onClose={() => setIsCancelModalOpen(false)}
        title="Cancel Sales Order"
      >
        <div className="space-y-3.5 text-xs">
          <p className="text-slate-600 dark:text-slate-300">
            Are you sure you want to cancel order <strong className="text-slate-900 dark:text-white">{order.order_number}</strong>? This will release reserved inventory back to warehouse stock.
          </p>
          <textarea
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
            placeholder="Reason for cancellation..."
            rows={3}
            className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-100"
          />
          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <Button variant="outline" size="sm" onClick={() => setIsCancelModalOpen(false)}>
              Back
            </Button>
            <Button variant="danger" size="sm" onClick={handleCancelOrder}>
              Confirm Cancellation
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
