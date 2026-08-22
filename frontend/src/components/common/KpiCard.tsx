import React from 'react';
import { DollarSign, Wallet, Package, Receipt, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { KpiMetric } from '../../types/dashboard';

interface KpiCardProps {
  metric: KpiMetric;
}

export const KpiCard: React.FC<KpiCardProps> = ({ metric }) => {
  const renderIcon = () => {
    switch (metric.icon_name) {
      case 'dollar':
        return <DollarSign className="w-4 h-4" />;
      case 'wallet':
        return <Wallet className="w-4 h-4" />;
      case 'package':
        return <Package className="w-4 h-4" />;
      case 'receipt':
        return <Receipt className="w-4 h-4" />;
      default:
        return <DollarSign className="w-4 h-4" />;
    }
  };

  const getIconContainerStyle = () => {
    switch (metric.badge_color) {
      case 'blue':
        return 'bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400';
      case 'peach':
        return 'bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-400';
      case 'cyan':
        return 'bg-sky-50 text-sky-600 dark:bg-sky-950/50 dark:text-sky-400';
      case 'red':
        return 'bg-rose-50 text-rose-600 dark:bg-rose-950/50 dark:text-rose-400';
      default:
        return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300';
    }
  };

  const renderTrendBadge = () => {
    if (metric.trend === 'up') {
      const isNegativeContext = metric.comparison_text.toLowerCase().includes('requires attention');
      return (
        <span
          className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[11px] font-semibold ${
            isNegativeContext
              ? 'bg-rose-50 text-rose-700 dark:bg-rose-950/50 dark:text-rose-400'
              : 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400'
          }`}
        >
          <TrendingUp className="w-3 h-3" />
          {metric.change}
        </span>
      );
    }
    if (metric.trend === 'down') {
      return (
        <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[11px] font-semibold bg-rose-50 text-rose-700 dark:bg-rose-950/50 dark:text-rose-400">
          <TrendingDown className="w-3 h-3" />
          {metric.change}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
        <Minus className="w-3 h-3" />
        {metric.change}
      </span>
    );
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-4.5 shadow-xs hover:shadow-sm transition-all duration-150">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold tracking-wider text-slate-400 dark:text-slate-500 uppercase">
          {metric.title}
        </span>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${getIconContainerStyle()}`}>
          {renderIcon()}
        </div>
      </div>

      <div className="mt-2.5 mb-1.5">
        <h3 className="text-2xl sm:text-[26px] font-bold tracking-tight text-slate-900 dark:text-white leading-none">
          {metric.value}
        </h3>
      </div>

      <div className="flex items-center gap-1.5 text-xs">
        {renderTrendBadge()}
        <span className="text-[11px] text-slate-400 dark:text-slate-500 font-normal">
          {metric.comparison_text}
        </span>
      </div>
    </div>
  );
};
