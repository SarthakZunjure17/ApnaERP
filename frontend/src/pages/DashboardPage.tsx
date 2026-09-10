import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  DollarSign,
  TrendingUp,
  Package,
  CreditCard,
  Users,
  ShoppingCart,
  CheckCircle2,
  RefreshCw,
  AlertCircle,
  BarChart3,
  FileText,
  Building,
  Target,
  ArrowUpRight,
  Boxes,
} from 'lucide-react';
import { dashboardService } from '../services/dashboardService';
import { ExecutiveDashboardResponse } from '../types/dashboard';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { useToast } from '../context/ToastContext';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  Legend,
} from 'recharts';

export const DashboardPage: React.FC = () => {
  const [data, setData] = useState<ExecutiveDashboardResponse | null>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const { success } = useToast();

  const fetchDashboardData = async (isRefresh = false) => {
    if (isRefresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const [dashResult, logsResult] = await Promise.all([
        dashboardService.getExecutiveDashboard(),
        dashboardService.getRecentAuditLogs(5),
      ]);
      setData(dashResult);
      setAuditLogs(logsResult);
      if (isRefresh) {
        success('Refreshed', 'Executive metrics updated with live backend data.');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load executive dashboard data.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  if (isLoading && !data) {
    return <LoadingState message="Loading Executive Dashboard..." height="h-96" />;
  }

  if (error && !data) {
    return <ErrorState message={error} onRetry={() => fetchDashboardData()} />;
  }

  if (!data) return null;

  // Compute dynamic chart datasets based on real metrics
  const domainComparisonData = [
    {
      name: 'Sales',
      count: data.sales.total_orders_count,
      value: Number(data.sales.total_sales_revenue),
    },
    {
      name: 'Procurement',
      count: data.procurement.total_pos_count,
      value: Number(data.procurement.total_spend),
    },
    {
      name: 'Inventory',
      count: data.inventory.total_products_count,
      value: Number(data.inventory.total_inventory_valuation),
    },
    {
      name: 'Payroll',
      count: data.payroll.total_payroll_runs_count,
      value: Number(data.payroll.total_payroll_cost),
    },
  ];

  const formatCurrency = (val: number) => {
    if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(2)}M`;
    if (val >= 1_000) return `$${(val / 1_000).toFixed(1)}k`;
    return `$${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <div className="space-y-5 animate-fade-in pb-10">
      {/* Top Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              Executive Dashboard
            </h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border border-emerald-200/60 dark:border-emerald-800">
              Live Data
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Consolidated operational overview as of {data.as_of_date || 'Today'}.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <button
            onClick={() => fetchDashboardData(true)}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-brand-600' : ''}`} />
            Refresh
          </button>
          <Link
            to="/reports"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors"
          >
            <BarChart3 className="w-3.5 h-3.5" />
            Reporting Hub
          </Link>
        </div>
      </div>

      {/* Primary KPI Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Revenue */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-semibold uppercase tracking-wider text-[10px]">Total Sales Revenue</span>
            <div className="w-7 h-7 rounded-lg bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400 flex items-center justify-center">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <h3 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white">
              {formatCurrency(Number(data.sales.total_sales_revenue))}
            </h3>
            <span className="text-[11px] font-medium text-slate-500">
              {data.sales.total_orders_count} Orders
            </span>
          </div>
          <div className="mt-2 text-[11px] text-slate-400 flex items-center gap-1">
            <span>Avg order: {formatCurrency(Number(data.sales.average_order_value))}</span>
          </div>
        </div>

        {/* Procurement Spend */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-semibold uppercase tracking-wider text-[10px]">Procurement Spend</span>
            <div className="w-7 h-7 rounded-lg bg-amber-50 dark:bg-amber-950 text-amber-600 dark:text-amber-400 flex items-center justify-center">
              <ShoppingCart className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <h3 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white">
              {formatCurrency(Number(data.procurement.total_spend))}
            </h3>
            <span className="text-[11px] font-medium text-slate-500">
              {data.procurement.total_pos_count} POs
            </span>
          </div>
          <div className="mt-2 text-[11px] text-slate-400 flex items-center gap-1">
            <span>Pending POs: {data.procurement.pending_pos_count}</span>
          </div>
        </div>

        {/* Inventory Valuation */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-semibold uppercase tracking-wider text-[10px]">Stock Valuation</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-50 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
              <Package className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <h3 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white">
              {formatCurrency(Number(data.inventory.total_inventory_valuation))}
            </h3>
            <span className="text-[11px] font-medium text-slate-500">
              {data.inventory.total_products_count} SKUs
            </span>
          </div>
          <div className="mt-2 text-[11px] text-slate-400 flex items-center gap-1">
            <span>Low Stock Items: {data.inventory.low_stock_items_count}</span>
          </div>
        </div>

        {/* Total Workforce */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-semibold uppercase tracking-wider text-[10px]">Workforce Headcount</span>
            <div className="w-7 h-7 rounded-lg bg-purple-50 dark:bg-purple-950 text-purple-600 dark:text-purple-400 flex items-center justify-center">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <h3 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white">
              {data.hr.total_employees}
            </h3>
            <span className="text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
              {data.hr.active_employees} Active
            </span>
          </div>
          <div className="mt-2 text-[11px] text-slate-400 flex items-center gap-1">
            <span>Across {data.hr.total_departments} Departments</span>
          </div>
        </div>
      </div>

      {/* Row 2: Charts & Domain Aggregations */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Domain Value Breakdown Chart (Col 8) */}
        <div className="lg:col-span-8 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl p-5 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Cross-Domain Valuation Breakdown
              </h3>
              <p className="text-[11px] text-slate-400">
                Comparing operational figures across Sales, Procurement, Stock, and Payroll.
              </p>
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={domainComparisonData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={(v) => `$${v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v}`} tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(val: any) => [`$${Number(val).toLocaleString()}`, 'Valuation']}
                  contentStyle={{ borderRadius: '8px', fontSize: '12px' }}
                />
                <Bar dataKey="value" fill="#2563eb" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* CRM & Finance Quick Snapshot (Col 4) */}
        <div className="lg:col-span-4 space-y-4">
          {/* CRM Pipeline */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl p-4 shadow-xs">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                <Target className="w-3.5 h-3.5 text-purple-600" />
                CRM Pipeline
              </span>
              <Link to="/crm/opportunities" className="text-[11px] font-semibold text-brand-600 hover:underline">
                View &rarr;
              </Link>
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">Pipeline Valuation</span>
                <span className="font-bold text-slate-900 dark:text-white">
                  {formatCurrency(Number(data.crm.pipeline_value))}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">Weighted Forecast</span>
                <span className="font-bold text-emerald-600 dark:text-emerald-400">
                  {formatCurrency(Number(data.crm.weighted_forecast_value))}
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Active Opportunities</span>
                <span className="font-bold text-slate-900 dark:text-white">
                  {data.crm.active_opportunities} ({data.crm.open_leads} Open Leads)
                </span>
              </div>
            </div>
          </div>

          {/* Finance & General Ledger */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl p-4 shadow-xs">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                <Building className="w-3.5 h-3.5 text-brand-600" />
                Finance & Accounting
              </span>
              <Link to="/finance/journals" className="text-[11px] font-semibold text-brand-600 hover:underline">
                Journals &rarr;
              </Link>
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">Net Operating Income</span>
                <span className="font-bold text-slate-900 dark:text-white">
                  {formatCurrency(Number(data.finance.net_operating_income))}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-500">Total Expenses</span>
                <span className="font-bold text-slate-900 dark:text-white">
                  {formatCurrency(Number(data.finance.total_expenses))}
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Posted Journals</span>
                <span className="font-bold text-slate-900 dark:text-white">
                  {data.finance.posted_journals_count}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Row 3: Quick Navigation Modules */}
      <div>
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
          ERP Operational Domains
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
          <Link
            to="/workforce/employees"
            className="p-3 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl hover:border-brand-500 transition-colors shadow-2xs group"
          >
            <Users className="w-5 h-5 text-blue-600 mb-1.5 group-hover:scale-110 transition-transform" />
            <span className="text-xs font-bold text-slate-800 dark:text-slate-200 block">Workforce</span>
            <span className="text-[10px] text-slate-400">Employees & Shifts</span>
          </Link>

          <Link
            to="/workforce/payroll"
            className="p-3 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl hover:border-brand-500 transition-colors shadow-2xs group"
          >
            <CreditCard className="w-5 h-5 text-emerald-600 mb-1.5 group-hover:scale-110 transition-transform" />
            <span className="text-xs font-bold text-slate-800 dark:text-slate-200 block">Payroll</span>
            <span className="text-[10px] text-slate-400">Runs & Payslips</span>
          </Link>

          <Link
            to="/inventory/products"
            className="p-3 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl hover:border-brand-500 transition-colors shadow-2xs group"
          >
            <Package className="w-5 h-5 text-indigo-600 mb-1.5 group-hover:scale-110 transition-transform" />
            <span className="text-xs font-bold text-slate-800 dark:text-slate-200 block">Inventory</span>
            <span className="text-[10px] text-slate-400">Products & Stock</span>
          </Link>

          <Link
            to="/procurement/orders"
            className="p-3 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl hover:border-brand-500 transition-colors shadow-2xs group"
          >
            <ShoppingCart className="w-5 h-5 text-amber-600 mb-1.5 group-hover:scale-110 transition-transform" />
            <span className="text-xs font-bold text-slate-800 dark:text-slate-200 block">Procurement</span>
            <span className="text-[10px] text-slate-400">POs & Suppliers</span>
          </Link>

          <Link
            to="/sales/orders"
            className="p-3 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl hover:border-brand-500 transition-colors shadow-2xs group"
          >
            <FileText className="w-5 h-5 text-sky-600 mb-1.5 group-hover:scale-110 transition-transform" />
            <span className="text-xs font-bold text-slate-800 dark:text-slate-200 block">Sales & CRM</span>
            <span className="text-[10px] text-slate-400">Orders & Leads</span>
          </Link>

          <Link
            to="/finance/accounts"
            className="p-3 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl hover:border-brand-500 transition-colors shadow-2xs group"
          >
            <Building className="w-5 h-5 text-rose-600 mb-1.5 group-hover:scale-110 transition-transform" />
            <span className="text-xs font-bold text-slate-800 dark:text-slate-200 block">Finance</span>
            <span className="text-[10px] text-slate-400">Ledger & Journals</span>
          </Link>
        </div>
      </div>
    </div>
  );
};
