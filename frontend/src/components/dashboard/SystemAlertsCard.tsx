import React, { useState } from 'react';
import { AlertTriangle, PackageX, CreditCard, X } from 'lucide-react';
import { SystemAlert } from '../../types/dashboard';

interface SystemAlertsCardProps {
  alerts: SystemAlert[];
}

export const SystemAlertsCard: React.FC<SystemAlertsCardProps> = ({ alerts: initialAlerts }) => {
  const [alerts, setAlerts] = useState<SystemAlert[]>(initialAlerts);

  const dismissAlert = (id: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  };

  const renderAlertIcon = (iconName: string) => {
    switch (iconName) {
      case 'package-alert':
        return <PackageX className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />;
      case 'wallet-alert':
        return <CreditCard className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />;
      default:
        return <AlertTriangle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />;
    }
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
        <h3 className="text-sm font-bold text-slate-900 dark:text-white tracking-tight">
          System Alerts
        </h3>
        {alerts.length > 0 && (
          <span className="ml-auto text-[10px] font-semibold bg-rose-50 text-rose-600 dark:bg-rose-950/50 dark:text-rose-400 px-1.5 py-0.5 rounded-full">
            {alerts.length} active
          </span>
        )}
      </div>

      {/* Alerts List */}
      <div className="space-y-2.5">
        {alerts.map((alert) => {
          const isPeach = alert.color_theme === 'peach';
          return (
            <div
              key={alert.id}
              className={`p-2.5 sm:p-3 rounded-lg border transition-all flex items-start gap-2.5 relative ${
                isPeach
                  ? 'bg-[#fffaf8] dark:bg-rose-950/15 border-rose-100/90 dark:border-rose-900/30'
                  : 'bg-[#f6f9ff] dark:bg-indigo-950/15 border-indigo-100/90 dark:border-indigo-900/30'
              }`}
            >
              <div className="mt-0.5 shrink-0">{renderAlertIcon(alert.icon)}</div>
              <div className="flex-1 min-w-0 pr-3.5">
                <h4 className="text-xs font-semibold text-slate-900 dark:text-white leading-tight">
                  {alert.title}
                </h4>
                <p className="text-[11px] text-slate-600 dark:text-slate-300 mt-0.5 leading-snug">
                  {alert.description}
                </p>
              </div>
              <button
                onClick={() => dismissAlert(alert.id)}
                className="absolute top-2 right-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-0.5 cursor-pointer"
                aria-label="Dismiss alert"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          );
        })}

        {alerts.length === 0 && (
          <p className="text-xs text-slate-400 text-center py-3">No active system alerts.</p>
        )}
      </div>
    </div>
  );
};
