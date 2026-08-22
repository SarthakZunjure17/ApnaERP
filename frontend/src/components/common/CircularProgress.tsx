import React from 'react';

interface CircularProgressProps {
  percentage: number;
  label?: string;
  size?: number;
  strokeWidth?: number;
  color?: string;
  trackColor?: string;
  className?: string;
}

export const CircularProgress: React.FC<CircularProgressProps> = ({
  percentage,
  label = 'PRESENT',
  size = 110,
  strokeWidth = 9,
  color = '#2563eb', // brand blue
  trackColor = '#e2e8f0', // slate-200
  className = '',
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className={`relative inline-flex items-center justify-center ${className}`}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Track circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={trackColor}
          strokeWidth={strokeWidth}
          fill="transparent"
          className="dark:stroke-slate-800"
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          fill="transparent"
          className="transition-all duration-700 ease-out"
        />
      </svg>

      {/* Center text content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="text-xl font-bold tracking-tight text-slate-900 dark:text-white leading-none">
          {percentage}
          <span className="text-xs font-normal text-slate-400 dark:text-slate-500">%</span>
        </span>
        {label && (
          <span className="text-[9px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 mt-1">
            {label}
          </span>
        )}
      </div>
    </div>
  );
};
