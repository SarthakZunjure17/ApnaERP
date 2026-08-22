import React from 'react';

interface AvatarProps {
  name: string;
  src?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showStatus?: boolean;
  status?: 'online' | 'offline' | 'busy';
  className?: string;
}

export const Avatar: React.FC<AvatarProps> = ({
  name,
  src,
  size = 'md',
  showStatus = false,
  status = 'online',
  className = '',
}) => {
  const getInitials = (n: string) => {
    if (!n) return 'U';
    const parts = n.trim().split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return n.substring(0, 2).toUpperCase();
  };

  const sizeStyles = {
    sm: 'w-7 h-7 text-xs',
    md: 'w-9 h-9 text-sm',
    lg: 'w-11 h-11 text-base',
    xl: 'w-16 h-16 text-lg font-bold',
  };

  const statusDotSizes = {
    sm: 'w-2 h-2',
    md: 'w-2.5 h-2.5',
    lg: 'w-3 h-3',
    xl: 'w-3.5 h-3.5',
  };

  const statusColors = {
    online: 'bg-emerald-500 ring-white dark:ring-slate-900',
    offline: 'bg-slate-400 ring-white dark:ring-slate-900',
    busy: 'bg-rose-500 ring-white dark:ring-slate-900',
  };

  return (
    <div className={`relative inline-flex shrink-0 ${className}`}>
      {src ? (
        <img
          src={src}
          alt={name}
          className={`${sizeStyles[size]} rounded-full object-cover border border-slate-200 dark:border-slate-700`}
        />
      ) : (
        <div
          className={`${sizeStyles[size]} rounded-full bg-brand-600 text-white flex items-center justify-center font-semibold select-none`}
        >
          {getInitials(name)}
        </div>
      )}
      {showStatus && (
        <span
          className={`absolute bottom-0 right-0 rounded-full ring-2 ${statusDotSizes[size]} ${statusColors[status]}`}
        />
      )}
    </div>
  );
};
