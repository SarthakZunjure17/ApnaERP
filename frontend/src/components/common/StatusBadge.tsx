import React from 'react';

export type StatusType =
  | 'Active'
  | 'Pending'
  | 'Pending Approval'
  | 'In Review'
  | 'Approved'
  | 'Rejected'
  | 'On Leave'
  | 'Draft'
  | 'Cancelled'
  | 'Completed'
  | string;

interface StatusBadgeProps {
  status: StatusType;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = '' }) => {
  const normalize = status.toLowerCase();

  if (normalize === 'active' || normalize === 'approved' || normalize === 'completed') {
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300 border border-emerald-200/70 dark:border-emerald-800/60 tracking-tight ${className}`}
      >
        {status}
      </span>
    );
  }

  if (normalize === 'pending' || normalize === 'pending approval') {
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300 border border-amber-200/70 dark:border-amber-800/60 tracking-tight ${className}`}
      >
        {status}
      </span>
    );
  }

  if (normalize === 'in review') {
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300 border border-blue-200/70 dark:border-blue-800/60 tracking-tight ${className}`}
      >
        {status}
      </span>
    );
  }

  if (normalize === 'on leave') {
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-orange-50 text-orange-700 dark:bg-orange-950/40 dark:text-orange-300 border border-orange-200/70 dark:border-orange-800/60 tracking-tight ${className}`}
      >
        {status}
      </span>
    );
  }

  if (normalize === 'rejected' || normalize === 'cancelled') {
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300 border border-rose-200/70 dark:border-rose-800/60 tracking-tight ${className}`}
      >
        {status}
      </span>
    );
  }

  // Draft / default
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-200/70 dark:border-slate-700 tracking-tight ${className}`}
    >
      {status}
    </span>
  );
};
