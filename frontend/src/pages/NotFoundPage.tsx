import React from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, Home } from 'lucide-react';
import { Button } from '../components/common/Button';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center text-center p-6 animate-fade-in">
      <div className="w-16 h-16 rounded-2xl bg-brand-50 dark:bg-brand-950/60 text-brand-600 flex items-center justify-center mb-4">
        <AlertCircle className="w-8 h-8" />
      </div>
      <h1 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">404</h1>
      <h2 className="text-base font-semibold text-slate-700 dark:text-slate-300 mt-1">
        Page Not Found
      </h2>
      <p className="text-xs text-slate-500 max-w-sm mt-2 mb-6">
        The requested ERP resource could not be found or you may not have sufficient permissions.
      </p>
      <Link to="/dashboard">
        <Button variant="primary" size="md" leftIcon={<Home className="w-4 h-4" />}>
          Back to Dashboard
        </Button>
      </Link>
    </div>
  );
};
