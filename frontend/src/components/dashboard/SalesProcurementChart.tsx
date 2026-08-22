import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { SalesProcurementDataPoint } from '../../types/dashboard';

interface SalesProcurementChartProps {
  data: SalesProcurementDataPoint[];
}

export const SalesProcurementChart: React.FC<SalesProcurementChartProps> = ({ data }) => {
  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs">
      {/* Header & Legend */}
      <div className="flex items-center justify-between mb-3.5">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white tracking-tight">
          Sales vs Procurement
        </h3>
        <div className="flex items-center gap-3.5 text-xs">
          <div className="flex items-center gap-1.5 font-medium text-slate-700 dark:text-slate-200 text-[11px]">
            <span className="w-2 h-2 rounded-xs bg-[#0f172a] dark:bg-white shrink-0" />
            <span>Sales</span>
          </div>
          <div className="flex items-center gap-1.5 font-medium text-slate-400 dark:text-slate-500 text-[11px]">
            <span className="w-2 h-2 rounded-xs bg-[#64748b] shrink-0" />
            <span>Procurement</span>
          </div>
        </div>
      </div>

      {/* Bar Chart Area */}
      <div className="h-56 sm:h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -24, bottom: 0 }} barGap={4}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis
              dataKey="period"
              tickLine={false}
              axisLine={{ stroke: '#e2e8f0' }}
              tick={{ fontSize: 11, fill: '#94a3b8' }}
              dy={6}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11, fill: '#94a3b8' }}
              tickFormatter={(val) => `$${val}K`}
            />
            <Tooltip
              formatter={(value: any, name: string) => [
                `$${value}K`,
                name === 'sales' ? 'Total Sales' : 'Procurement Spend',
              ]}
              contentStyle={{
                backgroundColor: '#ffffff',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                fontSize: '11px',
                boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)',
              }}
            />
            <Bar
              dataKey="sales"
              fill="#0f172a"
              radius={[3, 3, 0, 0]}
              maxBarSize={18}
            />
            <Bar
              dataKey="procurement"
              fill="#64748b"
              radius={[3, 3, 0, 0]}
              maxBarSize={18}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
