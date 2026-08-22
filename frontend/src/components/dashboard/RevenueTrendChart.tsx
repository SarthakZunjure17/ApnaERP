import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { RevenueDataPoint } from '../../types/dashboard';

interface RevenueTrendChartProps {
  data: RevenueDataPoint[];
}

export const RevenueTrendChart: React.FC<RevenueTrendChartProps> = ({ data }) => {
  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs">
      {/* Header & Legend */}
      <div className="flex items-center justify-between mb-3.5">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white tracking-tight">
          Revenue Trend
        </h3>
        <div className="flex items-center gap-3.5 text-xs">
          <div className="flex items-center gap-1.5 font-medium text-slate-700 dark:text-slate-200 text-[11px]">
            <span className="w-2 h-2 rounded-full bg-slate-900 dark:bg-white shrink-0" />
            <span>Actual</span>
          </div>
          <div className="flex items-center gap-1.5 font-medium text-slate-400 dark:text-slate-500 text-[11px]">
            <span className="w-2 h-2 rounded-full bg-slate-300 dark:bg-slate-600 shrink-0" />
            <span>Forecast</span>
          </div>
        </div>
      </div>

      {/* Chart Area */}
      <div className="h-56 sm:h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -24, bottom: 0 }}>
            <defs>
              <linearGradient id="revenueActualGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis
              dataKey="month"
              tickLine={false}
              axisLine={{ stroke: '#e2e8f0' }}
              tick={{ fontSize: 11, fill: '#94a3b8' }}
              dy={6}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11, fill: '#94a3b8' }}
              tickFormatter={(val) => `$${val}M`}
            />
            <Tooltip
              formatter={(value: any, name: string) => [
                `$${value}M`,
                name === 'actual' ? 'Actual Revenue' : 'Forecast Projection',
              ]}
              contentStyle={{
                backgroundColor: '#ffffff',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                fontSize: '11px',
                boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)',
              }}
            />
            <Area
              type="monotone"
              dataKey="actual"
              stroke="#0f172a"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#revenueActualGradient)"
              dot={{ r: 3, fill: '#0f172a', strokeWidth: 2, stroke: '#ffffff' }}
              activeDot={{ r: 5, fill: '#2563eb', strokeWidth: 2, stroke: '#ffffff' }}
            />
            <Area
              type="monotone"
              dataKey="forecast"
              stroke="#94a3b8"
              strokeWidth={1.5}
              strokeDasharray="3 3"
              fillOpacity={0}
              fill="none"
              dot={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
