import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
  height?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading data...',
  height = 'h-64',
}) => {
  return (
    <div className={`flex flex-col items-center justify-center ${height} gap-3 text-slate-500`}>
      <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
      <p className="text-sm font-medium">{message}</p>
    </div>
  );
};
