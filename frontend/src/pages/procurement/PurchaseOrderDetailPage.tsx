import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
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
  FileCheck,
  FileText,
} from 'lucide-react';
import { procurementService } from '../../services/procurementService';
import { PurchaseOrderDetail } from '../../types/procurement';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { useToast } from '../../context/ToastContext';

export const PurchaseOrderDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [po, setPo] = useState<PurchaseOrderDetail | null>(null);
  const [newComment, setNewComment] = useState('');
  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const navigate = useNavigate();
  const { success, info } = useToast();

  useEffect(() => {
    loadPoDetail();
  }, [id]);

  const loadPoDetail = async () => {
    setIsLoading(true);
    if (!id) {
      setPo(null);
      setIsLoading(false);
      return;
    }
    const data = await procurementService.getPurchaseOrderById(id);
    setPo(data);
    setIsLoading(false);
  };

  const handleApprove = async () => {
    if (!po) return;
    const updated = await procurementService.approvePurchaseOrder(po.id);
    if (updated) {
      setPo(updated);
      success('Purchase Order Approved', `${po.po_number} has been approved successfully.`);
    }
  };

  const handleReject = async () => {
    if (!po) return;
    const updated = await procurementService.rejectPurchaseOrder(po.id, rejectReason);
    if (updated) {
      setPo(updated);
      setIsRejectModalOpen(false);
      success('Purchase Order Rejected', `${po.po_number} has been rejected.`);
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!po || !newComment.trim()) return;

    const updated = await procurementService.addComment(po.id, newComment.trim());
    if (updated) {
      setPo(updated);
      setNewComment('');
      success('Note Added', 'Internal comment recorded.');
    }
  };

  if (isLoading) {
    return <LoadingState message="Loading purchase order..." />;
  }

  if (!po) {
    return (
      <div className="space-y-4 sm:space-y-5 animate-fade-in pb-10">
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <Link to="/procurement/orders" className="hover:text-brand-600 transition-colors">
            Procurement
          </Link>
          <ChevronRight className="w-3.5 h-3.5" />
          <Link to="/procurement/orders" className="hover:text-brand-600 transition-colors">
            Orders
          </Link>
          <ChevronRight className="w-3.5 h-3.5" />
          <span className="font-semibold text-slate-700 dark:text-slate-200">Not Found</span>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800 rounded-2xl p-8 sm:p-12 text-center max-w-lg mx-auto shadow-xs">
          <div className="w-12 h-12 rounded-full bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 flex items-center justify-center mx-auto mb-4 border border-rose-100 dark:border-rose-900/40">
            <FileText className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Purchase Order Not Found</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1.5 max-w-xs mx-auto">
            No purchase order was found matching ID <span className="font-mono font-semibold text-slate-700 dark:text-slate-300">"{id}"</span>.
          </p>
          <div className="mt-6">
            <Link
              to="/procurement/orders"
              className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors"
            >
              Back to Purchase Orders
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-5 animate-fade-in pb-10">
      {/* Top Breadcrumbs & Header (Matching Screenshot 3) */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          {/* Breadcrumb line with PO Badge and Status */}
          <div className="flex items-center gap-2 text-xs flex-wrap">
            <span className="font-bold text-[10px] tracking-wider text-slate-400 uppercase">
              PURCHASE ORDER
            </span>
            <span className="px-2 py-0.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300 font-mono font-semibold text-[11px]">
              {po.po_number}
            </span>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-600" />
              {po.status}
            </span>
          </div>

          {/* Supplier Title */}
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white mt-1.5">
            {po.supplier_name}
          </h1>
        </div>

        {/* Action buttons (Cancel, Edit, Reject, Approve PO) */}
        <div className="flex items-center gap-2 self-start md:self-center flex-wrap">
          <button
            onClick={() => navigate('/procurement/orders')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-200 rounded-lg text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            <XCircle className="w-3.5 h-3.5 text-slate-400" />
            Cancel
          </button>

          <button
            onClick={() => info('Edit Mode', 'PO editing is enabled for draft/pending states.')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-200 rounded-lg text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            <Pencil className="w-3.5 h-3.5 text-slate-400" />
            Edit
          </button>

          <button
            onClick={() => setIsRejectModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-rose-100 hover:bg-rose-200 dark:bg-rose-950 dark:hover:bg-rose-900 text-rose-700 dark:text-rose-300 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
          >
            Reject
          </button>

          <button
            onClick={handleApprove}
            disabled={po.status === 'Approved'}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 bg-brand-600 hover:bg-brand-700 disabled:bg-emerald-600 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            {po.status === 'Approved' ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5" />
                Approved
              </>
            ) : (
              'Approve PO'
            )}
          </button>
        </div>
      </div>

      {/* Top 3 Cards Grid (Supplier Details, Shipping & Terms, Approval Timeline) */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        {/* Card 1: Supplier Details (Col span 4) */}
        <div className="md:col-span-4 bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-3.5">
              <div className="w-6 h-6 rounded-md bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-300">
                <Building2 className="w-3.5 h-3.5" />
              </div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Supplier Details
              </h3>
            </div>

            <div className="space-y-2.5 text-xs">
              <div>
                <span className="text-[10px] font-semibold text-slate-400 uppercase block">
                  Company
                </span>
                <p className="font-semibold text-slate-900 dark:text-white mt-0.5">
                  {po.supplier_name}
                </p>
              </div>

              <div>
                <span className="text-[10px] font-semibold text-slate-400 uppercase block">
                  Contact Person
                </span>
                <div className="flex items-center justify-between mt-0.5">
                  <span className="text-slate-800 dark:text-slate-200 font-medium">
                    {po.contact_person}
                  </span>
                  <a
                    href={`mailto:${po.contact_email}`}
                    className="text-brand-600 hover:underline font-mono text-[11px]"
                  >
                    {po.contact_email}
                  </a>
                </div>
              </div>

              <div>
                <span className="text-[10px] font-semibold text-slate-400 uppercase block">
                  Address
                </span>
                <p className="text-slate-600 dark:text-slate-300 mt-0.5 leading-relaxed whitespace-pre-line">
                  {po.supplier_address}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Card 2: Shipping & Terms (Col span 4) */}
        <div className="md:col-span-4 bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-3.5">
              <div className="w-6 h-6 rounded-md bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-300">
                <Truck className="w-3.5 h-3.5" />
              </div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Shipping & Terms
              </h3>
            </div>

            <div className="space-y-2.5 text-xs">
              <div>
                <span className="text-[10px] font-semibold text-slate-400 uppercase block">
                  Ship To
                </span>
                <p className="text-slate-800 dark:text-slate-200 mt-0.5 leading-relaxed whitespace-pre-line">
                  {po.ship_to_address}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-1">
                <div>
                  <span className="text-[10px] font-semibold text-slate-400 uppercase block">
                    Expected Delivery
                  </span>
                  <span className="text-slate-800 dark:text-slate-200 font-medium mt-0.5 block">
                    {po.expected_delivery}
                  </span>
                </div>

                <div>
                  <span className="text-[10px] font-semibold text-slate-400 uppercase block">
                    Payment Terms
                  </span>
                  <span className="text-slate-800 dark:text-slate-200 font-medium mt-0.5 block">
                    {po.payment_terms}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Card 3: Approval Timeline (Col span 4, Matching Screenshot 3) */}
        <div className="md:col-span-4 bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-3.5">
            Approval Timeline
          </h3>

          <div className="space-y-3.5 relative pl-4 border-l-2 border-slate-100 dark:border-slate-800 text-xs">
            {po.timeline.map((step) => {
              const isCompleted = step.status === 'completed';
              const isCurrent = step.status === 'current';

              return (
                <div key={step.id} className="relative">
                  {/* Step dot on vertical line */}
                  <div
                    className={`absolute -left-[23px] top-0.5 w-3 h-3 rounded-full ring-2 ring-white dark:ring-slate-900 ${
                      isCompleted
                        ? 'bg-blue-600'
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
                    <div className="flex items-center gap-1.5 mt-0.5">
                      {step.user_avatar && (
                        <img
                          src={step.user_avatar}
                          alt={step.user_name}
                          className="w-4 h-4 rounded-full object-cover shrink-0"
                        />
                      )}
                      <span className="text-[11px] text-slate-500 dark:text-slate-400">
                        {step.description}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom Grid: Line Items Table (Left 8 cols) & Internal Comments (Right 4 cols) */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        {/* Line Items Table & Summary Box (Col span 8) */}
        <div className="md:col-span-8 space-y-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-3.5">
              Line Items
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-100 dark:border-slate-800 text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                    <th className="py-2 px-2.5">Item & Description</th>
                    <th className="py-2 px-2.5">SKU</th>
                    <th className="py-2 px-2.5 text-center">Qty</th>
                    <th className="py-2 px-2.5 text-right">Unit Price</th>
                    <th className="py-2 px-2.5 text-center">Tax</th>
                    <th className="py-2 px-2.5 text-right">Subtotal</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100/80 dark:divide-slate-800/60 text-xs">
                  {po.items.map((item) => (
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
                    {po.formatted_subtotal}
                  </span>
                </div>
                <div className="flex justify-between text-slate-500">
                  <span>Tax (8%)</span>
                  <span className="font-medium text-slate-800 dark:text-slate-200">
                    {po.formatted_tax}
                  </span>
                </div>
                <div className="flex justify-between text-slate-500">
                  <span>Shipping</span>
                  <span className="font-medium text-slate-800 dark:text-slate-200">
                    {po.formatted_shipping}
                  </span>
                </div>
                <div className="flex justify-between pt-2 border-t border-slate-200 dark:border-slate-700 text-sm font-bold text-slate-900 dark:text-white">
                  <span>Total</span>
                  <span className="text-base font-bold text-slate-900 dark:text-white">
                    {po.formatted_total}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Internal Comments Section (Col span 4, Matching Screenshot 3) */}
        <div className="md:col-span-4 bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3.5">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Internal Comments
              </h3>
              <span className="w-5 h-5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 flex items-center justify-center font-bold text-[10px]">
                {po.comments.length}
              </span>
            </div>

            {/* Comments Stream */}
            <div className="space-y-3">
              {po.comments.map((comment) => (
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

          {/* Comment Input Box with Send Button */}
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

      {/* Reject Modal */}
      <Modal
        isOpen={isRejectModalOpen}
        onClose={() => setIsRejectModalOpen(false)}
        title="Reject Purchase Order"
      >
        <div className="space-y-3.5 text-xs">
          <p className="text-slate-600 dark:text-slate-300">
            Please provide a justification for rejecting {po.po_number}. This will notify the supplier and requestor.
          </p>
          <textarea
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="Reason for rejection (e.g. over-budget, incorrect quantities...)"
            rows={3}
            className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-100"
          />
          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <Button variant="outline" size="sm" onClick={() => setIsRejectModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" size="sm" onClick={handleReject}>
              Confirm Rejection
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
