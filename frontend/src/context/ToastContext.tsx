import React, { createContext, useContext, useState, useCallback } from 'react';
import { ToastMessage, ToastType } from '../types/common';
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';

interface ToastContextType {
  showToast: (title: string, message?: string, type?: ToastType, duration?: number) => void;
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  warning: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    (title: string, message?: string, type: ToastType = 'info', duration: number = 4000) => {
      const id = 'toast-' + Math.random().toString(36).substring(2, 9);
      const newToast: ToastMessage = { id, title, message, type, duration };

      setToasts((prev) => [...prev, newToast]);

      if (duration > 0) {
        setTimeout(() => {
          removeToast(id);
        }, duration);
      }
    },
    [removeToast]
  );

  const success = useCallback((title: string, message?: string) => showToast(title, message, 'success'), [showToast]);
  const error = useCallback((title: string, message?: string) => showToast(title, message, 'error'), [showToast]);
  const warning = useCallback((title: string, message?: string) => showToast(title, message, 'warning'), [showToast]);
  const info = useCallback((title: string, message?: string) => showToast(title, message, 'info'), [showToast]);

  return (
    <ToastContext.Provider value={{ showToast, success, error, warning, info }}>
      {children}
      {/* Toast container */}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none max-w-sm w-full">
        {toasts.map((toast) => {
          const getIcon = () => {
            switch (toast.type) {
              case 'success':
                return <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />;
              case 'error':
                return <AlertCircle className="w-5 h-5 text-rose-500 shrink-0" />;
              case 'warning':
                return <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0" />;
              default:
                return <Info className="w-5 h-5 text-blue-500 shrink-0" />;
            }
          };

          const getBg = () => {
            switch (toast.type) {
              case 'success':
                return 'border-emerald-200 bg-white dark:bg-slate-900';
              case 'error':
                return 'border-rose-200 bg-white dark:bg-slate-900';
              case 'warning':
                return 'border-amber-200 bg-white dark:bg-slate-900';
              default:
                return 'border-blue-200 bg-white dark:bg-slate-900';
            }
          };

          return (
            <div
              key={toast.id}
              className={`pointer-events-auto flex items-start gap-3 p-4 rounded-xl border shadow-lg transition-all animate-fade-in ${getBg()}`}
            >
              {getIcon()}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-900 dark:text-white leading-tight">
                  {toast.title}
                </p>
                {toast.message && (
                  <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 leading-relaxed">
                    {toast.message}
                  </p>
                )}
              </div>
              <button
                onClick={() => removeToast(toast.id)}
                className="text-slate-400 hover:text-slate-600 transition-colors p-1 -mr-1 -mt-1"
                aria-label="Close notification"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};
