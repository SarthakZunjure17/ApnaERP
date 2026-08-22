import React, { useState } from 'react';
import {
  ShoppingCart,
  Wallet,
  FileText,
  RotateCcw,
  CheckCircle,
  Clock,
  ChevronRight,
} from 'lucide-react';
import { ApprovalItem } from '../../types/dashboard';
import { StatusBadge } from '../common/StatusBadge';
import { useToast } from '../../context/ToastContext';

interface PendingApprovalsTableProps {
  items: ApprovalItem[];
  onViewAll?: () => void;
}

export const PendingApprovalsTable: React.FC<PendingApprovalsTableProps> = ({
  items: initialItems,
  onViewAll,
}) => {
  const [items, setItems] = useState<ApprovalItem[]>(initialItems);
  const { success, info } = useToast();

  const renderTypeIcon = (type: ApprovalItem['type']) => {
    switch (type) {
      case 'Purchase Order':
        return <ShoppingCart className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />;
      case 'Payroll':
        return <Wallet className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />;
      case 'Expense':
        return <FileText className="w-3.5 h-3.5 text-slate-600 dark:text-slate-400" />;
      case 'Refund':
        return <RotateCcw className="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" />;
      default:
        return <FileText className="w-3.5 h-3.5 text-slate-600 dark:text-slate-400" />;
    }
  };

  const handleQuickApprove = (id: string, subject: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, status: 'Approved' } : item))
    );
    success('Approval Successful', `${subject} has been approved.`);
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs">
      {/* Header */}
      <div className="flex items-center justify-between mb-3.5">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white tracking-tight">
          Pending Approvals
        </h3>
        <button
          onClick={onViewAll || (() => info('Workflows', 'Opening full approvals workflow list'))}
          className="text-xs font-semibold text-brand-600 hover:text-brand-700 dark:text-brand-400 hover:underline flex items-center gap-0.5 cursor-pointer"
        >
          View All
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-800 text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
              <th className="py-2 px-2.5">Type</th>
              <th className="py-2 px-2.5">Subject</th>
              <th className="py-2 px-2.5">Amount</th>
              <th className="py-2 px-2.5">Date</th>
              <th className="py-2 px-2.5">Status</th>
              <th className="py-2 px-2.5 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100/80 dark:divide-slate-800/60 text-xs">
            {items.map((item) => (
              <tr
                key={item.id}
                className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors group"
              >
                {/* Type with Icon */}
                <td className="py-2.5 px-2.5">
                  <div className="flex items-center gap-2">
                    <div className="w-6.5 h-6.5 rounded-md bg-slate-50 dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700/50 flex items-center justify-center shrink-0">
                      {renderTypeIcon(item.type)}
                    </div>
                    <span className="font-medium text-slate-700 dark:text-slate-300 text-xs whitespace-nowrap">
                      {item.type}
                    </span>
                  </div>
                </td>

                {/* Subject */}
                <td className="py-2.5 px-2.5 font-medium text-slate-900 dark:text-white max-w-[200px] truncate text-xs">
                  {item.subject}
                </td>

                {/* Amount */}
                <td className="py-2.5 px-2.5 font-medium text-slate-900 dark:text-slate-100 whitespace-nowrap text-xs">
                  {item.formatted_amount}
                </td>

                {/* Date */}
                <td className="py-2.5 px-2.5 text-slate-400 dark:text-slate-500 whitespace-nowrap text-[11px]">
                  {item.date}
                </td>

                {/* Status Badge */}
                <td className="py-2.5 px-2.5 whitespace-nowrap">
                  <StatusBadge status={item.status} />
                </td>

                {/* Action button */}
                <td className="py-2.5 px-2.5 text-right whitespace-nowrap">
                  {item.status !== 'Approved' ? (
                    <button
                      onClick={(e) => handleQuickApprove(item.id, item.subject, e)}
                      className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-semibold text-brand-700 bg-brand-50 hover:bg-brand-100 dark:bg-brand-950/60 dark:text-brand-300 dark:hover:bg-brand-900/60 rounded transition-colors cursor-pointer"
                      title="Quick Approve"
                    >
                      <CheckCircle className="w-3 h-3 text-brand-600" />
                      Approve
                    </button>
                  ) : (
                    <span className="text-[11px] text-emerald-600 font-medium inline-flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" />
                      Approved
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
