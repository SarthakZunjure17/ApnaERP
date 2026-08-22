import React from 'react';
import { ActivityItem } from '../../types/dashboard';

interface RecentActivityTimelineProps {
  items: ActivityItem[];
}

export const RecentActivityTimeline: React.FC<RecentActivityTimelineProps> = ({ items }) => {
  const getDotStyle = (color: ActivityItem['dot_color']) => {
    switch (color) {
      case 'blue':
        return 'bg-brand-600 ring-brand-100 dark:ring-brand-950/60';
      case 'gray':
        return 'bg-slate-400 ring-slate-100 dark:ring-slate-800';
      case 'orange':
        return 'bg-amber-500 ring-amber-100 dark:ring-amber-950/60';
      case 'green':
        return 'bg-emerald-500 ring-emerald-100 dark:ring-emerald-950/60';
      default:
        return 'bg-brand-600 ring-brand-100';
    }
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs">
      {/* Header */}
      <h3 className="text-sm font-bold text-slate-900 dark:text-white tracking-tight mb-3">
        Recent Activity
      </h3>

      {/* Activity Timeline List */}
      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.id} className="flex items-start gap-2.5 relative group">
            {/* Status Dot */}
            <div className="mt-1 shrink-0">
              <span
                className={`block w-2 h-2 rounded-full ring-2 transition-transform group-hover:scale-125 ${getDotStyle(
                  item.dot_color
                )}`}
              />
            </div>

            {/* Text details */}
            <div className="flex-1 min-w-0">
              <p className="text-xs text-slate-700 dark:text-slate-200 leading-snug">
                <span className="font-semibold text-slate-900 dark:text-white">
                  {item.user_name}{' '}
                </span>
                <span className="text-slate-600 dark:text-slate-300">{item.action}</span>
              </p>
              <span className="text-[10px] text-slate-400 dark:text-slate-500 font-medium mt-0.5 block">
                {item.time_ago}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
